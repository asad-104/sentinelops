"""Tool specs are generated from the ToolSet's input models and stay in sync with validation."""

from __future__ import annotations

import json

import pytest

from sentinelops.llm.prompt import SYSTEM_PROMPT, TOOL_DESCRIPTIONS, prompt_sha256
from sentinelops.llm.schemas import SUBMIT_REPORT, ReportDraft, inline_schema, tool_specs
from sentinelops.report import InvestigationReport
from sentinelops.tools import TOOL_INPUT_MODELS, ToolSet

# Frozen in stage A (docs/PROGRESS.md). Changing the prompt or a tool description changes this hash;
# any change must be logged in PROGRESS.md as a prompt revision before the pilot is rerun.
FROZEN_PROMPT_SHA256 = "0f97fb44c2549794f7ba1be577d8d01392422e30b8752f4fd2ba640a88c2d2ea"

SAMPLE_ARGS = {
    "get_alert": {}, "get_window": {},
    "search_logs": {"service": "orders", "min_level": "ERROR", "contains": "timeout", "limit": 5,
                    "start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
    "get_metrics": {"service": "auth", "metric": "error_rate", "limit": 10},
    "list_deployments": {"service": "payments"}, "list_config_changes": {"limit": 3},
    "get_dependencies": {"service": "orders"}, "get_timeline": {"limit": 10},
    "get_record": {"source_id": "LOG-00001"},
}


def test_every_tool_and_submit_report_has_a_flat_spec() -> None:
    specs = {s.name: s for s in tool_specs()}
    assert list(specs) == [*TOOL_INPUT_MODELS, SUBMIT_REPORT]
    text = json.dumps([s.parameters for s in specs.values()])
    assert "$ref" not in text and "$defs" not in text
    assert all(s.description == TOOL_DESCRIPTIONS[s.name] for s in specs.values())


def test_toolset_registry_uses_the_shared_input_models(toolset: ToolSet) -> None:
    assert toolset.tool_input_models == TOOL_INPUT_MODELS


@pytest.mark.parametrize("name", list(TOOL_INPUT_MODELS))
def test_spec_fields_match_the_validating_model(name: str) -> None:
    spec = next(s for s in tool_specs() if s.name == name)
    model = TOOL_INPUT_MODELS[name]
    assert set(spec.parameters.get("properties", {})) == set(model.model_fields)
    assert set(spec.parameters.get("required", [])) == {f for f, info in model.model_fields.items()
                                                       if info.is_required()}
    model.model_validate(SAMPLE_ARGS[name])
    assert set(SAMPLE_ARGS[name]) <= set(spec.parameters.get("properties", {}))


def test_enums_are_inlined_for_the_model() -> None:
    metrics = next(s for s in tool_specs() if s.name == "get_metrics").parameters["properties"]
    assert "api-gateway" in metrics["service"]["enum"] and "error_rate" in metrics["metric"]["enum"]


def test_inline_schema_resolves_nested_references() -> None:
    schema = {"$defs": {"A": {"type": "object", "properties": {"b": {"$ref": "#/$defs/B"}}, "title": "A"},
                        "B": {"type": "string", "enum": ["x"]}},
              "properties": {"a": {"$ref": "#/$defs/A"}}, "title": "Top"}
    assert inline_schema(schema) == {"properties": {"a": {"type": "object", "properties": {
        "b": {"type": "string", "enum": ["x"]}}}}}


def test_submit_report_draft_completes_to_a_valid_report() -> None:
    draft = ReportDraft.model_validate({
        "summary": "s", "hypotheses": [{"rank": 1, "service": "orders", "fault_type": "memory_leak",
                                        "confidence": "medium", "supporting_evidence": ["LOG-00001"],
                                        "rationale": "r"}]})
    report = InvestigationReport(scenario_id="sc-0123456789", investigator="llm_tool_loop", tool_calls=3,
                                 duration_s=1.0, stop_reason="sufficient_evidence", **draft.model_dump())
    assert report.top.fault_type.value == "memory_leak" and report.executed_actions == ()
    spec = next(s for s in tool_specs() if s.name == SUBMIT_REPORT).parameters
    assert "executed_actions" not in spec["properties"]  # the model cannot even claim an action


def test_prompt_is_frozen() -> None:
    assert prompt_sha256() == FROZEN_PROMPT_SHA256, "prompt changed: log a revision in PROGRESS.md first"
    assert "untrusted" in SYSTEM_PROMPT
