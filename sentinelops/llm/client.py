"""Backend-neutral chat contract for tool-using models.

Every client returns either an ``LLMResponse`` or an ``LLMError``; it never raises
for timeouts, connection failures, HTTP errors or malformed responses. The tool
loop can then handle model failures the same way it handles tool failures
(``ToolResult.ok=False``), without try/except around each call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]
LLMErrorCode = Literal["timeout", "connection", "http_status", "bad_response"]


@dataclass(frozen=True)
class ToolCallRequest:
    """One tool call as the model emitted it. ``raw_arguments`` is unparsed JSON text (untrusted)."""

    id: str
    name: str
    raw_arguments: str


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCallRequest, ...] = ()  # assistant messages only
    tool_name: str | None = None  # tool messages only
    tool_call_id: str | None = None  # tool messages only


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema, $ref-free


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: tuple[ToolCallRequest, ...] = ()
    usage: Usage = field(default_factory=Usage)
    latency_s: float = 0.0
    thinking_chars: int = 0  # length of any separate reasoning text the backend returned
    load_s: float | None = None  # time the backend spent loading the model for this call, if it reports it


@dataclass(frozen=True)
class LLMError:
    code: LLMErrorCode
    message: str
    latency_s: float = 0.0


class LLMClient(Protocol):
    """A chat backend. ``describe()`` returns non-secret configuration for traces."""

    def chat(self, messages: list[ChatMessage], tools: list[ToolSpec]) -> LLMResponse | LLMError: ...

    def describe(self) -> dict[str, Any]: ...
