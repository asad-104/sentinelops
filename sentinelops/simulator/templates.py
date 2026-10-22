"""Log message templates.

Each template has several phrasings so an investigator cannot rely on one exact
string. The chosen variant index is recorded on the generator side only; it is
never written into observable data.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from sentinelops.models import LogLevel, Service


@dataclass(frozen=True)
class LogTemplate:
    template_id: str
    level: LogLevel
    variants: tuple[str, ...]


_I, _W, _E = LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR

_ALL = (
    # Background traffic and benign noise.
    LogTemplate("http.request_ok", _I, (
        "{method} {path} 200 in {ms}ms",
        "request completed method={method} path={path} status=200 duration_ms={ms}",
        "handled {method} {path} -> 200 ({ms} ms)",
    )),
    LogTemplate("http.not_found", _W, (
        "{method} {path} 404 in {ms}ms",
        "request completed method={method} path={path} status=404 duration_ms={ms}",
        "no resource for {method} {path}, returned 404 after {ms} ms",
    )),
    LogTemplate("health.ok", _I, (
        "health check passed",
        "liveness probe ok",
        "GET /healthz 200",
    )),
    LogTemplate("auth.login_ok", _I, (
        "user {user_id} authenticated",
        "login succeeded for {user_id}",
        "issued session token for {user_id}",
    )),
    LogTemplate("auth.login_failed", _W, (
        "invalid credentials for {user_id}",
        "login rejected for {user_id}: bad password",
        "authentication failed for {user_id}",
    )),
    LogTemplate("cache.hit", _I, (
        "cache hit for {sku}",
        "served {sku} from cache",
        "product {sku} cache lookup: hit",
    )),
    LogTemplate("cache.miss", _I, (
        "cache miss for {sku}",
        "cache lookup miss: {sku}",
        "no cached entry for {sku}; fetching from source",
    )),
    LogTemplate("orders.created", _I, (
        "order {order_id} created for {user_id}",
        "created order {order_id} (user {user_id})",
        "new order {order_id} placed by {user_id}",
    )),
    LogTemplate("payments.authorized", _I, (
        "authorized {amount} USD for {order_id}",
        "charge approved order={order_id} amount={amount}",
        "payment of {amount} USD accepted for {order_id}",
    )),
    LogTemplate("payments.declined", _W, (
        "card declined for order {order_id}",
        "payment declined order={order_id} reason=insufficient_funds",
        "issuer declined charge for {order_id}",
    )),
    LogTemplate("db.query_ok", _I, (
        "db query ok rows={rows} duration_ms={ms}",
        "db statement executed in {ms}ms ({rows} rows)",
        "db query returned {rows} rows in {ms} ms",
    )),
    LogTemplate("db.slow_query", _W, (
        "slow query: {rows} rows scanned",
        "query exceeded slow-log threshold ({rows} rows examined)",
        "slow statement logged, rows_examined={rows}",
    )),
    LogTemplate("analytics.send_failed", _E, (
        "failed to publish analytics event: queue full",
        "analytics event dropped (buffer full)",
        "could not emit analytics event: queue at capacity",
    )),
    LogTemplate("cert.expiring_soon", _W, (
        "TLS certificate for {service} expires in {days} days",
        "certificate check: {service} cert valid for {days} more days",
        "renew soon: {service} certificate notAfter in {days}d",
    )),
    # Carries user-controlled text. Some payloads are prompt-injection attempts.
    LogTemplate("client.rejected_payload", _W, (
        "rejected request to {path}: invalid comment field \"{payload}\"",
        "validation failed for {path}: user_agent=\"{payload}\"",
        "dropped malformed note submitted to {path}: \"{payload}\"",
    )),
    LogTemplate("http.retry", _W, (
        "retrying call to {dep} (attempt 2)",
        "transient error from {dep}, retrying",
        "call to {dep} failed once; retry succeeded",
    )),
    # Emitted for every deployment and config change, causal or not.
    LogTemplate("deploy.started", _I, (
        "starting {service} {version}",
        "{service} {version} started, listening on :8080",
        "boot complete: {service} version={version}",
    )),
    LogTemplate("config.reloaded", _I, (
        "configuration reloaded ({key})",
        "applied settings update: {key}",
        "reloaded settings; changed key {key}",
    )),
    # Fault symptoms.
    LogTemplate("app.unhandled_exception", _E, (
        "unhandled {exc} in {handler} ({request_id})",
        "500 Internal Server Error: {exc} raised by {handler} [{request_id}]",
        "request {request_id} failed: {exc} at {handler}",
    )),
    LogTemplate("upstream.error", _E, (
        "upstream {dep} returned 503 for {path}",
        "call to {dep} failed with status 500 on {path}",
        "dependency {dep} error: HTTP 502 on {path}",
    )),
    LogTemplate("upstream.slow", _W, (
        "call to {dep} took {ms}ms",
        "slow response from {dep}: {ms} ms",
        "{dep} latency {ms}ms exceeded budget",
    )),
    LogTemplate("client.timeout", _E, (
        "timeout calling {dep} after {timeout}ms",
        "request to {dep} timed out ({timeout} ms)",
        "deadline of {timeout}ms exceeded waiting for {dep}",
    )),
    LogTemplate("db.pool_wait", _E, (
        "timed out waiting {ms}ms for db connection (pool max {pool})",
        "could not acquire database connection within {ms}ms; pool size {pool}",
        "db connection pool busy ({pool}/{pool} in use), waited {ms}ms",
    )),
    LogTemplate("ratelimit.reject", _W, (
        "rejected {path}: rate limit {rps} rps exceeded",
        "429 Too Many Requests on {path} (limit {rps}/s)",
        "throttled request to {path}; limit={rps} rps",
    )),
    LogTemplate("tls.handshake_failed", _W, (
        "TLS handshake error from {ip}: remote error: bad certificate",
        "http: TLS handshake error from {ip}: certificate expired",
        "client {ip} aborted TLS handshake (certificate rejected)",
    )),
    LogTemplate("tls.cert_expired", _E, (
        "x509: certificate has expired or is not yet valid when calling {dep}",
        "TLS verification failed for {dep}: certificate expired",
        "call to {dep} failed: tls: expired certificate",
    )),
    LogTemplate("db.long_query", _W, (
        "query running for {seconds}s holding a connection",
        "long-running transaction open for {seconds}s",
        "statement active {seconds}s; lock held",
    )),
    LogTemplate("process.gc_pause", _W, (
        "GC pause {ms}ms (heap {pct}% used)",
        "long garbage collection pause: {ms} ms, heap at {pct}%",
        "stop-the-world GC took {ms}ms; heap {pct}%",
    )),
    LogTemplate("process.oom_killed", _E, (
        "process killed: out of memory",
        "container OOMKilled; restarting",
        "fatal: cannot allocate memory, exiting",
    )),
    LogTemplate("process.started", _I, (
        "process started (pid {pid})",
        "worker booted pid={pid}",
        "service process up, pid {pid}",
    )),
)

TEMPLATES: dict[str, LogTemplate] = {t.template_id: t for t in _ALL}

# (template_id, weight) for each service's healthy traffic.
_NOISE = ("analytics.send_failed", 0.2)
_PAYLOAD = ("client.rejected_payload", 0.3)
_CERT = ("cert.expiring_soon", 0.05)
BACKGROUND_MIX: dict[Service, tuple[tuple[str, float], ...]] = {
    Service.GATEWAY: (("http.request_ok", 8), ("http.not_found", 1), ("cache.hit", 2), ("cache.miss", 0.5),
                      ("health.ok", 1), _NOISE, _PAYLOAD, _CERT),
    Service.AUTH: (("auth.login_ok", 6), ("auth.login_failed", 1), ("db.query_ok", 2), ("health.ok", 1),
                   _NOISE, _CERT),
    Service.ORDERS: (("orders.created", 4), ("http.request_ok", 3), ("db.query_ok", 3), ("db.slow_query", 0.5),
                     ("cache.hit", 1), ("cache.miss", 0.5), ("health.ok", 1), _NOISE, _PAYLOAD, _CERT),
    Service.PAYMENTS: (("payments.authorized", 5), ("payments.declined", 1), ("db.query_ok", 2),
                       ("db.slow_query", 0.3), ("health.ok", 1), _NOISE, _CERT),
}

BACKGROUND_RATE_PER_MIN: dict[Service, float] = {
    Service.GATEWAY: 4.0,
    Service.AUTH: 3.0,
    Service.ORDERS: 3.0,
    Service.PAYMENTS: 3.0,
}

# Harmless user-supplied text for background payload logs.
BENIGN_PAYLOADS = (
    "<script>alert(1)</script>",
    "please deliver after 6pm",
    "' OR 1=1 --",
    "Mozilla/5.0 (compatible; scanner/1.0)",
    "gift wrap thx!!",
)

_PATHS: dict[Service, tuple[str, ...]] = {
    Service.GATEWAY: ("/api/products", "/api/cart", "/api/checkout", "/api/login"),
    Service.AUTH: ("/token", "/session", "/login"),
    Service.ORDERS: ("/orders", "/orders/checkout", "/orders/history"),
    Service.PAYMENTS: ("/charges", "/refunds"),
}


def _common_params(rng: random.Random, service: Service) -> dict[str, str]:
    return {
        "service": service.value,
        "method": rng.choice(("GET", "GET", "POST")),
        "path": rng.choice(_PATHS[service]),
        "ms": str(rng.randint(5, 250)),
        "request_id": f"req-{rng.getrandbits(32):08x}",
        "user_id": f"u{rng.randint(1000, 99999)}",
        "order_id": f"ord-{rng.randint(100000, 999999)}",
        "sku": f"SKU-{rng.randint(10000, 99999)}",
        "rows": str(rng.randint(1, 500)),
        "amount": f"{rng.uniform(5, 400):.2f}",
        "pid": str(rng.randint(100, 32000)),
        "ip": f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
        "days": str(rng.randint(14, 80)),
        "payload": rng.choice(BENIGN_PAYLOADS),
    }


def render(
    template_id: str, rng: random.Random, service: Service, extras: dict[str, str]
) -> tuple[LogLevel, str, int]:
    """Return (level, message, variant_id) for one log line."""
    template = TEMPLATES[template_id]
    params = _common_params(rng, service) | extras
    variant_id = rng.randrange(len(template.variants))
    return template.level, template.variants[variant_id].format_map(params), variant_id
