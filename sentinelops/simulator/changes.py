"""Deployments and configuration changes.

Causal and red-herring changes come from the same draw: the fault picks its
trigger uniformly from changes that already exist. Author pool, version format,
summaries, keys and timing are therefore identically distributed. The only
difference is that a config trigger's new value is set to a harmful one, which
is legitimate diagnostic signal.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from sentinelops.models import Service
from sentinelops.simulator.topology import DB_SERVICES, SERVICES

AUTHORS = ("aisha.k", "ben.t", "chen.w", "dina.r", "eli.m", "release-bot")

DEPLOY_SUMMARIES = (
    "Bump dependencies",
    "Refactor request handlers",
    "Add structured logging fields",
    "Improve input validation",
    "Update pricing rules",
    "Minor performance tweaks",
    "Fix pagination edge case",
    "Update translations",
)

TIMEOUT_KEY = "http_client.timeout_ms"
POOL_KEY = "db.pool_max"
CACHE_KEY = "cache.ttl_seconds"
RATE_LIMIT_KEY = "rate_limit.rps"

CONFIG_DEFAULTS: dict[str, int] = {TIMEOUT_KEY: 3000, POOL_KEY: 40, CACHE_KEY: 300, RATE_LIMIT_KEY: 500}

# Only services with a database connection pool have a pool setting.
CONFIG_KEYS: dict[Service, tuple[str, ...]] = {
    service: (
        (TIMEOUT_KEY, POOL_KEY, CACHE_KEY, RATE_LIMIT_KEY)
        if service in DB_SERVICES
        else (TIMEOUT_KEY, CACHE_KEY, RATE_LIMIT_KEY)
    )
    for service in SERVICES
}

BENIGN_FACTORS = (0.5, 0.75, 1.25, 1.5, 2.0)
HARMFUL_VALUES: dict[str, tuple[int, ...]] = {
    TIMEOUT_KEY: (100, 150, 200, 250),
    POOL_KEY: (2, 3, 4),
    CACHE_KEY: (0,),
    RATE_LIMIT_KEY: (20, 30, 40),
}

# Minutes after window start in which any change can happen.
CHANGE_WINDOW_MIN = (10.0, 75.0)


@dataclass
class DraftDeployment:
    minute: float
    service: Service
    author: str
    summary: str
    minor_bump: bool
    version: str = ""
    previous_version: str = ""


@dataclass
class DraftConfigChange:
    minute: float
    service: Service
    key: str
    old_value: int
    new_value: int
    author: str


def _format_version(version: tuple[int, int, int]) -> str:
    return "v{}.{}.{}".format(*version)


def draw_deployments(rng: random.Random) -> list[DraftDeployment]:
    current = {s: (rng.randint(1, 3), rng.randint(0, 20), rng.randint(0, 9)) for s in SERVICES}
    drafts = [
        DraftDeployment(
            minute=rng.uniform(*CHANGE_WINDOW_MIN),
            service=rng.choice(SERVICES),
            author=rng.choice(AUTHORS),
            summary=rng.choice(DEPLOY_SUMMARIES),
            minor_bump=rng.random() < 0.3,
        )
        for _ in range(rng.randint(1, 3))
    ]
    # Chain versions in time order so repeated deploys of one service are consistent.
    for draft in sorted(drafts, key=lambda d: d.minute):
        major, minor, patch = current[draft.service]
        new = (major, minor + 1, 0) if draft.minor_bump else (major, minor, patch + 1)
        draft.previous_version = _format_version(current[draft.service])
        draft.version = _format_version(new)
        current[draft.service] = new
    return drafts


def draw_config_changes(rng: random.Random) -> list[DraftConfigChange]:
    # Distinct (service, key) pairs so old values never contradict an earlier change.
    pairs = [(service, key) for service in SERVICES for key in CONFIG_KEYS[service]]
    drafts = []
    for service, key in rng.sample(pairs, rng.randint(1, 3)):
        old = CONFIG_DEFAULTS[key]
        drafts.append(
            DraftConfigChange(
                minute=rng.uniform(*CHANGE_WINDOW_MIN),
                service=service,
                key=key,
                old_value=old,
                new_value=max(1, round(old * rng.choice(BENIGN_FACTORS))),
                author=rng.choice(AUTHORS),
            )
        )
    return drafts


def make_harmful(change: DraftConfigChange, rng: random.Random) -> None:
    change.new_value = rng.choice(HARMFUL_VALUES[change.key])
