import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


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

    __table_args__ = (
        Index("ix_traces_project_created", "project_id", "created_at"),
    )


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
