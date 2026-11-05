import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uid():
    return uuid.uuid4().hex[:24]


def _now():
    return datetime.now(timezone.utc)


class Trace(Base):
    __tablename__ = "traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(24), default=_uid, unique=True, nullable=False, index=True)
    project_id = Column(String(64), default="default", nullable=False, index=True)

    user_input = Column(Text, nullable=False)
    system_prompt = Column(Text)
    model = Column(String(64), nullable=False, index=True)
    provider = Column(String(32), index=True)
    temperature = Column(Float)
    max_tokens = Column(Integer)

    model_output = Column(Text)
    tokens_prompt = Column(Integer, default=0)
    tokens_completion = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)

    cost = Column(Float, default=0.0)
    latency_ms = Column(Integer)
    ttft_ms = Column(Integer)

    status = Column(String(16), default="success", index=True)
    error_message = Column(Text)
    tags = Column(JSON, default=list)
    metadata_extra = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now, index=True)

    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_traces_project_created", "project_id", "created_at"),)


class Span(Base):
    __tablename__ = "spans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    span_id = Column(String(24), default=_uid, unique=True, nullable=False, index=True)
    trace_id_fk = Column(Integer, ForeignKey("traces.id", ondelete="CASCADE"), nullable=False)
    parent_span_id = Column(String(24), nullable=True, index=True)

    span_type = Column(String(32), nullable=False, index=True)
    name = Column(String(128))

    input_data = Column(JSON)
    output_data = Column(JSON)

    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)

    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    status = Column(String(16), default="success")
    error_message = Column(Text)
    metadata_extra = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    trace = relationship("Trace", back_populates="spans")


class GoldenDataset(Base):
    __tablename__ = "golden_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    project_id = Column(String(64), default="default", index=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    cases = relationship("GoldenCase", back_populates="dataset", cascade="all, delete-orphan")


class GoldenCase(Base):
    __tablename__ = "golden_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        Integer, ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False
    )
    source_trace_id = Column(String(24), index=True)

    input_text = Column(Text, nullable=False)
    expected_keywords = Column(JSON, default=list)
    forbidden_keywords = Column(JSON, default=list)
    expected_json_schema = Column(JSON)
    must_cite_docs = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("GoldenDataset", back_populates="cases")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("golden_datasets.id"), nullable=False)
    model = Column(String(64), nullable=False)
    is_baseline = Column(Integer, default=0)  # 0=false, 1=true
    status = Column(String(16), default="running")  # running | completed | failed

    total_cases = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    overall_score = Column(Integer, default=0)  # 0-100

    cost_total = Column(Integer, default=0)
    latency_p95_ms = Column(Integer)
    cost_change_pct = Column(Integer)
    latency_change_ms = Column(Integer)

    per_case_results = Column(JSON, default=list)
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    dataset = relationship("GoldenDataset")
