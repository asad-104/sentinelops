"""Tool specs for the model, generated from the ToolSet's own input models.

Generating the schemas (rather than writing them by hand) means what the model
is told and what ``ToolSet.call`` validates cannot drift apart. ``$ref``s are
inlined and titles dropped, because small models handle flat schemas better.
``submit_report`` takes the part of ``InvestigationReport`` the model writes;
the loop adds scenario ID, investigator, measured counts and the stop reason.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sentinelops.llm.client import ToolSpec
from sentinelops.llm.prompt import TOOL_DESCRIPTIONS
from sentinelops.models import Service
from sentinelops.report import Hypothesis
from sentinelops.tools import TOOL_INPUT_MODELS

SUBMIT_REPORT = "submit_report"


class ReportDraft(BaseModel):
    """What the model submits. Unknown fields are rejected, like every tool input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str = Field(max_length=4000)
    affected_services: tuple[Service, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = Field(min_length=1, max_length=5)
    missing_evidence: tuple[str, ...] = ()
    uncertainty: str = ""
    next_checks: tuple[str, ...] = ()
    recommended_remediation: tuple[str, ...] = ()


def inline_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve local ``#/$defs/...`` references and drop ``$defs`` and ``title`` keys."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                target = resolve(defs[node["$ref"].removeprefix("#/$defs/")])
                return {**target, **{k: resolve(v) for k, v in node.items() if k != "$ref"}}
            return {k: resolve(v) for k, v in node.items() if k not in ("$defs", "title")}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def tool_specs() -> list[ToolSpec]:
    """Specs for every read-only tool, then ``submit_report``, in a fixed order."""
    specs = [ToolSpec(name, TOOL_DESCRIPTIONS[name], inline_schema(model.model_json_schema()))
             for name, model in TOOL_INPUT_MODELS.items()]
    specs.append(ToolSpec(SUBMIT_REPORT, TOOL_DESCRIPTIONS[SUBMIT_REPORT],
                          inline_schema(ReportDraft.model_json_schema())))
    return specs
