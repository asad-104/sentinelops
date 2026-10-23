"""Tool specs for the M4 agent: the read tools (from the ToolSet's input models) plus the state tools.

All tools are sent on every request, in a fixed order, so the tool block stays stable for the
backend's prefix cache; the loop rejects tools that the current state does not allow.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sentinelops.agent.prompt import TOOL_DESCRIPTIONS
from sentinelops.agent.states import (
    FINISH_GATHERING,
    FINISH_VERIFYING,
    RETURN_TO_GATHER,
    SUBMIT_HYPOTHESES,
    SUBMIT_REPORT,
)
from sentinelops.llm.client import ToolSpec
from sentinelops.llm.schemas import ReportDraft, inline_schema
from sentinelops.report import Hypothesis
from sentinelops.tools import TOOL_INPUT_MODELS


class NoArguments(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HypothesesDraft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hypotheses: tuple[Hypothesis, ...] = Field(min_length=1, max_length=5)


STATE_TOOL_MODELS: dict[str, type[BaseModel]] = {
    FINISH_GATHERING: NoArguments,
    SUBMIT_HYPOTHESES: HypothesesDraft,
    RETURN_TO_GATHER: NoArguments,
    FINISH_VERIFYING: NoArguments,
    SUBMIT_REPORT: ReportDraft,
}


def agent_tool_specs() -> list[ToolSpec]:
    models = {**TOOL_INPUT_MODELS, **STATE_TOOL_MODELS}
    return [ToolSpec(name, TOOL_DESCRIPTIONS[name], inline_schema(model.model_json_schema()))
            for name, model in models.items()]
