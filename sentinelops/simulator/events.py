"""Generator-side log events, before rendering and ID assignment."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from sentinelops.models import Service

Origin = Literal["background", "change", "distractor", "fault"]
ParamsFn = Callable[[random.Random, int], dict[str, str]]


@dataclass
class LogEvent:
    minute: float
    service: Service
    template_id: str
    origin: Origin
    params: dict[str, str] = field(default_factory=dict)


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def stream(
    rng: random.Random,
    service: Service,
    template_id: str,
    rates: Sequence[float],
    origin: Origin,
    *,
    not_before: float = 0.0,
    params: ParamsFn | None = None,
) -> list[LogEvent]:
    """Poisson log events with a per-minute rate; ``params(rng, minute)`` fills placeholders."""
    events = []
    for minute, rate in enumerate(rates):
        for _ in range(poisson(rng, rate)):
            t = minute + rng.random()
            if t >= not_before:
                events.append(LogEvent(t, service, template_id, origin, params(rng, minute) if params else {}))
    return events
