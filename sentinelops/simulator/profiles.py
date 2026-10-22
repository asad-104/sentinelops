"""Dataset splits and difficulty tiers.

The held-out split differs from dev in two ways at once: it may use a fourth
log phrasing that dev never contains, and its trigger-to-onset lag range is
wider. A drop in held-out accuracy therefore cannot be attributed to either
difference alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Split(StrEnum):
    DEV = "dev"
    HELDOUT = "heldout"


class Tier(StrEnum):
    STANDARD = "standard"
    AMBIGUOUS = "ambiguous"
    MISSING_EVIDENCE = "missing_evidence"


@dataclass(frozen=True)
class SplitProfile:
    split: Split
    variants: tuple[int, ...]
    trigger_lag_min: tuple[float, float]  # minutes from causal change to onset


DEV_PROFILE = SplitProfile(Split.DEV, variants=(0, 1, 2), trigger_lag_min=(1.0, 6.0))
HELDOUT_PROFILE = SplitProfile(Split.HELDOUT, variants=(0, 1, 2, 3), trigger_lag_min=(1.0, 12.0))
PROFILES: dict[Split, SplitProfile] = {Split.DEV: DEV_PROFILE, Split.HELDOUT: HELDOUT_PROFILE}

# Ambiguous tier (v4): realistic secondary symptoms that resemble another fault, plus one red
# herring just before onset. True symptoms keep their normal rate (v3 thinned them to 40%).
DECOY_LEAD_MIN = (1.0, 6.0)

# Missing-evidence tier (v4): the root service loses logs OR metrics from just before onset to
# the window end (v3 restored them 20 minutes after onset). Never both.
GAP_BEFORE_ONSET_MIN = 5.0
