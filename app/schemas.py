from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def get(self, key, default=None):
        return getattr(self, key, default)


class SpanInput(Payload):
    span_type: str = Field(default="unknown", max_length=32)
    name: str | None = Field(default=None, max_length=128)
    parent_span_id: str | None = None
    input_data: Any = None
    output_data: Any = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    status: str = "success"
    error_message: str | None = None
    metadata_extra: dict = Field(default_factory=dict)


class TraceInput(Payload):
    trace_id: str | None = Field(default=None, min_length=1, max_length=24)
    user_input: str = Field(default="", validation_alias=AliasChoices("user_input", "input"))
    model_output: str | None = Field(
        default=None, validation_alias=AliasChoices("model_output", "output")
    )
    model: str = Field(default="unknown", max_length=64)
    project_id: str = Field(default="default", max_length=64)
    system_prompt: str | None = None
    provider: str | None = Field(default=None, max_length=32)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    tokens_prompt: int = Field(default=0, ge=0)
    tokens_completion: int = Field(default=0, ge=0)
    tokens_total: int = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    ttft_ms: int | None = Field(default=None, ge=0)
    status: str = "success"
    error_message: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata_extra: dict = Field(default_factory=dict)
    spans: list[SpanInput] = Field(default_factory=list, max_length=1000)


class DatasetInput(Payload):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    project_id: str = Field(default="default", max_length=64)


class CaseInput(Payload):
    input_text: str = ""
    expected_keywords: list[str] = Field(default_factory=list)
    forbidden_keywords: list[str] = Field(default_factory=list)
    expected_json_schema: dict | bool | None = None
    must_cite_docs: list[str] = Field(default_factory=list)
    source_trace_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    messages: list[dict] | None = None
    system_prompt: str | None = None


class EvalInput(Payload):
    dataset_id: int | None = Field(default=None, gt=0)
    model: str = Field(default="deepseek-chat", max_length=64)
    is_baseline: bool = False
    baseline_run_id: int | None = Field(default=None, gt=0)
    require_real_judge: bool = True
    revision: str = Field(default="", max_length=128)
    min_score: int = Field(default=80, ge=0, le=100)
    max_drop: int = Field(default=0, ge=0, le=100)
