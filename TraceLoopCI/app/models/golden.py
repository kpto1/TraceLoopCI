from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, JSON, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


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
    dataset_id = Column(Integer, ForeignKey("golden_datasets.id", ondelete="CASCADE"), nullable=False)
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
