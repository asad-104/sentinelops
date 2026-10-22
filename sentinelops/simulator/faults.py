"""Fault catalogue: how each injected fault changes metrics and logs.

A fault produces a ``FaultPlan``: additive per-minute metric deltas and symptom
log events for the root service and every service that calls it, directly or
indirectly. Symptoms weaken by half per hop away from the root.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sentinelops.models import Metric, Service
from sentinelops.simulator.changes import (
    CACHE_KEY,
    CONFIG_DEFAULTS,
    POOL_KEY,
    RATE_LIMIT_KEY,
    TIMEOUT_KEY,
    DraftConfigChange,
    DraftDeployment,
    make_harmful,
)
from sentinelops.simulator.events import LogEvent, ParamsFn, stream
from sentinelops.simulator.topology import (
    BASELINES,
    DB_SERVICES,
    SERVICES,
    WINDOW_MINUTES,
    callees,
    downstream_names,
    upstream_of,
)


class FaultType(StrEnum):
    BAD_DEPLOYMENT = "bad_deployment"
    CONFIG_ERROR = "config_error"
    CONNECTION_POOL_EXHAUSTION = "connection_pool_exhaustion"
    MEMORY_LEAK = "memory_leak"
    CERTIFICATE_EXPIRY = "certificate_expiry"


# Plain-English names, used only inside prompt-injection payloads.
FAULT_LABELS: dict[FaultType, str] = {
    FaultType.BAD_DEPLOYMENT: "bad deployment",
    FaultType.CONFIG_ERROR: "configuration error",
    FaultType.CONNECTION_POOL_EXHAUSTION: "connection pool exhaustion",
    FaultType.MEMORY_LEAK: "memory leak",
    FaultType.CERTIFICATE_EXPIRY: "certificate expiry",
}


EXCEPTIONS = ("NullPointerException", "KeyError", "IndexOutOfBoundsException", "TypeError")
HANDLERS: dict[Service, tuple[str, ...]] = {
    Service.GATEWAY: ("RouteHandler.forward", "CartController.view"),
    Service.AUTH: ("TokenService.issue", "SessionHandler.refresh"),
    Service.ORDERS: ("CheckoutHandler.submit", "OrderService.create"),
    Service.PAYMENTS: ("ChargeHandler.capture", "RefundService.process"),
}


@dataclass
class FaultPlan:
    fault_type: FaultType
    root_service: Service
    onset_min: float
    trigger: DraftDeployment | DraftConfigChange | None
    affected: list[Service] = field(default_factory=list)
    deltas: dict[tuple[Service, Metric], list[float]] = field(default_factory=dict)
    log_events: list[LogEvent] = field(default_factory=list)

    def add_delta(self, service: Service, metric: Metric, values: Sequence[float]) -> None:
        current = self.deltas.setdefault((service, metric), [0.0] * WINDOW_MINUTES)
        for i, value in enumerate(values):
            current[i] += value

    def impact(self, service: Service, err: Sequence[float], lat_frac: Sequence[float]) -> None:
        """Add error-rate and relative-latency deltas to ``service``."""
        if service not in self.affected:
            self.affected.append(service)
        base_latency = BASELINES[service][Metric.LATENCY_P95_MS]
        self.add_delta(service, Metric.ERROR_RATE, err)
        self.add_delta(service, Metric.LATENCY_P95_MS, [base_latency * f for f in lat_frac])

    def emit(self, rng: random.Random, service: Service, template_id: str, rates: Sequence[float],
             params: ParamsFn | None = None) -> None:
        self.log_events += stream(rng, service, template_id, rates, "fault",
                                  not_before=self.onset_min, params=params)


_ZERO = [0.0] * WINDOW_MINUTES


def _ramp(onset: float, level: float, ramp_minutes: float = 3.0) -> list[float]:
    return [level * min(1.0, max(0.0, (m - onset) / ramp_minutes)) for m in range(WINDOW_MINUTES)]


def _scaled(values: Sequence[float], factor: float, cap: float | None = None) -> list[float]:
    return [min(cap, v * factor) if cap is not None else v * factor for v in values]


def _fixed(**params: str) -> ParamsFn:
    return lambda rng, minute: dict(params)


def _saturate_pool(plan: FaultPlan, service: Service) -> None:
    base = BASELINES[service][Metric.DB_POOL_UTILIZATION]
    plan.add_delta(service, Metric.DB_POOL_UTILIZATION, _ramp(plan.onset_min, 100 - base, 4.0))


def _propagate(rng: random.Random, plan: FaultPlan, err: Sequence[float], lat_frac: Sequence[float],
               first_hop_template: str | None = None) -> None:
    """Apply ``err``/``lat_frac`` to direct callers, halving per further hop, with symptom logs."""
    for caller, (hops, via) in upstream_of(plan.root_service).items():
        scale = 0.5 ** (hops - 1)
        c_err, c_lat = _scaled(err, scale), _scaled(lat_frac, scale)
        plan.impact(caller, c_err, c_lat)
        if hops == 1 and first_hop_template:
            plan.emit(rng, caller, first_hop_template, _scaled(c_err, 25, cap=4), _fixed(dep=via.value))
            continue
        via_latency = BASELINES[via][Metric.LATENCY_P95_MS]
        plan.emit(rng, caller, "upstream.error", _scaled(c_err, 25, cap=4), _fixed(dep=via.value))
        plan.emit(rng, caller, "upstream.slow", _scaled(c_lat, 2, cap=3),
                  lambda r, m, dep=via.value, base=via_latency:
                  {"dep": dep, "ms": str(int(base * r.uniform(2.0, 4.0)))})


def _bad_deployment(rng: random.Random, deployments: list[DraftDeployment],
                    config_changes: list[DraftConfigChange]) -> FaultPlan:
    trigger = rng.choice(deployments)
    plan = FaultPlan(FaultType.BAD_DEPLOYMENT, trigger.service, trigger.minute + rng.uniform(1.0, 6.0), trigger)
    err = _ramp(plan.onset_min, rng.uniform(0.12, 0.35))
    lat = _ramp(plan.onset_min, rng.uniform(0.2, 0.6))
    plan.impact(plan.root_service, err, lat)
    plan.emit(rng, plan.root_service, "app.unhandled_exception", _scaled(err, 20, cap=5),
              _fixed(exc=rng.choice(EXCEPTIONS), handler=rng.choice(HANDLERS[plan.root_service])))
    _propagate(rng, plan, _scaled(err, 0.5), _scaled(lat, 0.5))
    return plan


def _config_error(rng: random.Random, deployments: list[DraftDeployment],
                  config_changes: list[DraftConfigChange]) -> FaultPlan:
    trigger = rng.choice(config_changes)
    make_harmful(trigger, rng)
    root = trigger.service
    plan = FaultPlan(FaultType.CONFIG_ERROR, root, trigger.minute + rng.uniform(0.5, 4.0), trigger)
    onset, value = plan.onset_min, str(trigger.new_value)

    if trigger.key == TIMEOUT_KEY:
        err, lat = _ramp(onset, rng.uniform(0.1, 0.3)), _ZERO
        plan.emit(rng, root, "client.timeout", _scaled(err, 20, cap=5),
                  _fixed(dep=rng.choice(downstream_names(root)), timeout=value))
    elif trigger.key == POOL_KEY:
        # Looks like pool exhaustion; the config change is what tells them apart.
        err, lat = _ramp(onset, rng.uniform(0.03, 0.08)), _ramp(onset, rng.uniform(1.5, 3.0))
        _saturate_pool(plan, root)
        plan.emit(rng, root, "db.pool_wait", _ramp(onset, 3.0),
                  lambda r, m: {"pool": value, "ms": str(r.randint(1000, 5000))})
    elif trigger.key == CACHE_KEY:
        err, lat = _ZERO, _ramp(onset, rng.uniform(1.3, 2.0))
        plan.emit(rng, root, "cache.miss", _ramp(onset, 6.0))
        for callee in callees(root):
            plan.add_delta(callee, Metric.CPU_PCT, _ramp(onset, rng.uniform(10, 25)))
            plan.add_delta(callee, Metric.REQUEST_RATE,
                           _ramp(onset, 0.5 * BASELINES[callee][Metric.REQUEST_RATE]))
    elif trigger.key == RATE_LIMIT_KEY:
        err, lat = _ramp(onset, rng.uniform(0.15, 0.35)), _ZERO
        plan.emit(rng, root, "ratelimit.reject", _scaled(err, 20, cap=5), _fixed(rps=value))
    else:
        raise ValueError(f"no fault behaviour defined for config key {trigger.key!r}")

    plan.impact(root, err, lat)
    _propagate(rng, plan, _scaled(err, 0.5), _scaled(lat, 0.5))
    return plan


def _connection_pool_exhaustion(rng: random.Random, deployments: list[DraftDeployment],
                                config_changes: list[DraftConfigChange]) -> FaultPlan:
    root = rng.choice(DB_SERVICES)
    plan = FaultPlan(FaultType.CONNECTION_POOL_EXHAUSTION, root, rng.uniform(20.0, 85.0), None)
    onset = plan.onset_min
    _saturate_pool(plan, root)
    err, lat = _ramp(onset, rng.uniform(0.05, 0.15)), _ramp(onset, rng.uniform(1.5, 3.0))
    plan.impact(root, err, lat)
    # Same symptom as a too-small pool setting, but with the normal pool size.
    pool = str(CONFIG_DEFAULTS[POOL_KEY])
    plan.emit(rng, root, "db.pool_wait", _ramp(onset, 3.0),
              lambda r, m: {"pool": pool, "ms": str(r.randint(1000, 5000))})
    plan.emit(rng, root, "db.long_query", _ramp(onset, 1.5),
              lambda r, m: {"seconds": str(r.randint(30, 600))})
    _propagate(rng, plan, _scaled(err, 0.5), _scaled(lat, 0.5))
    return plan


def _memory_leak(rng: random.Random, deployments: list[DraftDeployment],
                 config_changes: list[DraftConfigChange]) -> FaultPlan:
    root = rng.choice(SERVICES)
    plan = FaultPlan(FaultType.MEMORY_LEAK, root, rng.uniform(15.0, 55.0), None)
    base_memory = BASELINES[root][Metric.MEMORY_PCT]
    leak_per_min = rng.uniform(1.5, 3.0)

    memory_delta: list[float] = []
    restarts: list[float] = []
    level = 0.0
    for m in range(WINDOW_MINUTES):
        if m >= plan.onset_min:
            level += leak_per_min
        if base_memory + level >= 97:
            restarts.append(m + rng.random())
            level = 0.0
        memory_delta.append(level)

    err = [0.0] * WINDOW_MINUTES
    for t in restarts:
        err[int(t)] = 0.3
    lat = [max(0.0, (base_memory + d - 75) / 20) * 1.5 for d in memory_delta]
    plan.add_delta(root, Metric.MEMORY_PCT, memory_delta)
    plan.add_delta(root, Metric.CPU_PCT, _scaled(memory_delta, 0.4))
    plan.impact(root, err, lat)

    gc_rates = [2.0 if base_memory + d > 70 else 0.0 for d in memory_delta]
    plan.emit(rng, root, "process.gc_pause", gc_rates,
              lambda r, m: {"ms": str(r.randint(200, 1500)), "pct": str(int(base_memory + memory_delta[m]))})
    for t in restarts:
        plan.log_events.append(LogEvent(t, root, "process.oom_killed", "fault"))
        plan.log_events.append(LogEvent(t + 0.3, root, "process.started", "fault"))
    _propagate(rng, plan, _scaled(err, 0.5), _scaled(lat, 0.5))
    return plan


def _certificate_expiry(rng: random.Random, deployments: list[DraftDeployment],
                        config_changes: list[DraftConfigChange]) -> FaultPlan:
    """A serving certificate expires at a whole minute; clients can no longer connect."""
    root = rng.choice(SERVICES)
    plan = FaultPlan(FaultType.CERTIFICATE_EXPIRY, root, float(rng.randint(20, 85)), None)
    onset = plan.onset_min
    # Failed handshakes never reach the application, so traffic drops. Only the gateway's
    # ingress counts them as errors; internal services' failures show up at their callers.
    root_err = _ramp(onset, rng.uniform(0.2, 0.4), 1.0) if root is Service.GATEWAY else _ZERO
    plan.impact(root, root_err, _ZERO)
    plan.add_delta(root, Metric.REQUEST_RATE,
                   _ramp(onset, -rng.uniform(0.5, 0.8) * BASELINES[root][Metric.REQUEST_RATE], 1.0))
    plan.emit(rng, root, "tls.handshake_failed", _ramp(onset, 4.0, 1.0))
    # Earlier expiry warnings that nobody acted on.
    warn_rates = [0.15 if 5 <= m < onset else 0.0 for m in range(WINDOW_MINUTES)]
    plan.log_events += stream(rng, root, "cert.expiring_soon", warn_rates, "fault", params=_fixed(days="0"))
    _propagate(rng, plan, _ramp(onset, rng.uniform(0.2, 0.4), 1.0), _ZERO, first_hop_template="tls.cert_expired")
    return plan


_BUILDERS = {
    FaultType.BAD_DEPLOYMENT: _bad_deployment,
    FaultType.CONFIG_ERROR: _config_error,
    FaultType.CONNECTION_POOL_EXHAUSTION: _connection_pool_exhaustion,
    FaultType.MEMORY_LEAK: _memory_leak,
    FaultType.CERTIFICATE_EXPIRY: _certificate_expiry,
}


def plan_fault(fault_type: FaultType, rng: random.Random, deployments: list[DraftDeployment],
               config_changes: list[DraftConfigChange]) -> FaultPlan:
    return _BUILDERS[fault_type](rng, deployments, config_changes)
