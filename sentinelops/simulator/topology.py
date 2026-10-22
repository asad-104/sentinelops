"""The simulated e-commerce system: services, call graph and healthy baselines.

There is no database service. Each service that talks to a database reports the
utilisation of its own connection pool as a metric.
"""

from __future__ import annotations

from sentinelops.models import Metric, Service

WINDOW_MINUTES = 120

# (caller, callee) edges. Order is fixed so generated output is deterministic.
DEPENDENCY_EDGES: tuple[tuple[Service, Service], ...] = (
    (Service.GATEWAY, Service.AUTH),
    (Service.GATEWAY, Service.ORDERS),
    (Service.ORDERS, Service.AUTH),
    (Service.ORDERS, Service.PAYMENTS),
)

# Third-party dependencies outside the simulated system. They appear in timeout logs only.
EXTERNAL_DEPENDENCIES: dict[Service, str] = {
    Service.AUTH: "identity-provider",
    Service.PAYMENTS: "card-processor",
}

SERVICES: tuple[Service, ...] = tuple(Service)
DB_SERVICES: tuple[Service, ...] = (Service.AUTH, Service.ORDERS, Service.PAYMENTS)

_COMMON_METRICS = (
    Metric.LATENCY_P95_MS,
    Metric.ERROR_RATE,
    Metric.CPU_PCT,
    Metric.MEMORY_PCT,
    Metric.REQUEST_RATE,
)

BASELINES: dict[Service, dict[Metric, float]] = {
    Service.GATEWAY: {Metric.LATENCY_P95_MS: 120, Metric.ERROR_RATE: 0.004, Metric.CPU_PCT: 35,
                      Metric.MEMORY_PCT: 40, Metric.REQUEST_RATE: 220},
    Service.AUTH: {Metric.LATENCY_P95_MS: 60, Metric.ERROR_RATE: 0.002, Metric.CPU_PCT: 25,
                   Metric.MEMORY_PCT: 38, Metric.REQUEST_RATE: 90, Metric.DB_POOL_UTILIZATION: 30},
    Service.ORDERS: {Metric.LATENCY_P95_MS: 150, Metric.ERROR_RATE: 0.003, Metric.CPU_PCT: 32,
                     Metric.MEMORY_PCT: 42, Metric.REQUEST_RATE: 40, Metric.DB_POOL_UTILIZATION: 35},
    Service.PAYMENTS: {Metric.LATENCY_P95_MS: 200, Metric.ERROR_RATE: 0.003, Metric.CPU_PCT: 28,
                       Metric.MEMORY_PCT: 40, Metric.REQUEST_RATE: 18, Metric.DB_POOL_UTILIZATION: 25},
}


def metrics_for(service: Service) -> tuple[Metric, ...]:
    if service in DB_SERVICES:
        return _COMMON_METRICS + (Metric.DB_POOL_UTILIZATION,)
    return _COMMON_METRICS


def callers(service: Service) -> tuple[Service, ...]:
    return tuple(caller for caller, callee in DEPENDENCY_EDGES if callee is service)


def callees(service: Service) -> tuple[Service, ...]:
    return tuple(callee for caller, callee in DEPENDENCY_EDGES if caller is service)


def downstream_names(service: Service) -> tuple[str, ...]:
    """Everything ``service`` calls, including external dependencies."""
    names = tuple(c.value for c in callees(service))
    external = EXTERNAL_DEPENDENCIES.get(service)
    return names + (external,) if external else names


def upstream_of(root: Service) -> dict[Service, tuple[int, Service]]:
    """Services that transitively call ``root``, mapped to (hops, next service towards root)."""
    result: dict[Service, tuple[int, Service]] = {}
    frontier = [root]
    hops = 0
    while frontier:
        hops += 1
        next_frontier: list[Service] = []
        for service in frontier:
            for caller in callers(service):
                if caller is not root and caller not in result:
                    result[caller] = (hops, service)
                    next_frontier.append(caller)
        frontier = next_frontier
    return result
