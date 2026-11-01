from typing import Any, Literal

from pydantic import BaseModel, Field

Tier = Literal["T0", "T1", "T2", "T3"]
Origin = Literal["user", "command_output", "web", "code"]


class Answer(BaseModel):
    choice: str
    confidence: float = Field(ge=0, le=1)
    source: Literal["laya", "keyword"]


class ToolCall(BaseModel):
    task_id: str
    step: int
    call_id: str
    tool: str
    args: dict[str, Any]
    request_en: str
    last_origin_flagged: bool = False


class RiskDecision(BaseModel):
    tier: Answer
    verify: Answer
    latency_ms: int


class PolicyVerdict(BaseModel):
    verdict: Literal["allow", "confirm", "deny"]
    policy: str
    reason: str
    hard: bool = True
    corrective_context: str | None = None


class GateToken(BaseModel):
    call_id: str
    verdict: PolicyVerdict
    confirmed: bool = False


class ToolResult(BaseModel):
    ok: bool
    summary: str
    data: dict | None = None
    origin: Origin = "command_output"


class Event(BaseModel):
    ts: str
    task_id: str
    stage: str
    payload: dict = Field(default_factory=dict)
