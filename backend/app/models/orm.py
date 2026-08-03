import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Float, Integer,
    ForeignKey, DateTime, ARRAY, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db import Base
import enum


# ─── Enums ──────────────────────────────────────────────────────────────────

class WorkspacePlan(str, enum.Enum):
    free = "free"
    pro = "pro"
    team = "team"


class MemberRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class EvalRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JudgeVerdict(str, enum.Enum):
    pass_ = "pass"
    fail = "fail"
    unclear = "unclear"


# ─── Workspace ───────────────────────────────────────────────────────────────

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="free")
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    members = relationship("WorkspaceMember", back_populates="workspace")
    model_endpoints = relationship("ModelEndpoint", back_populates="workspace")
    datasets = relationship("Dataset", back_populates="workspace")
    eval_runs = relationship("EvalRun", back_populates="workspace")


# ─── User ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    hashed_password = Column(String(255), nullable=True)  # NULL for OAuth users
    created_at = Column(DateTime, default=datetime.utcnow)

    workspaces = relationship("WorkspaceMember", back_populates="user")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspaces")


# ─── Model Endpoint ───────────────────────────────────────────────────────────

class ModelEndpoint(Base):
    __tablename__ = "model_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)  # openai | anthropic | custom
    base_url = Column(Text, nullable=False)
    model_name = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="model_endpoints")
    eval_runs = relationship("EvalRun", back_populates="model_endpoint")


# ─── Dataset ─────────────────────────────────────────────────────────────────

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(100), nullable=False)  # qa | jailbreak | factual | custom
    row_count = Column(Integer, default=0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="datasets")
    rows = relationship("DatasetRow", back_populates="dataset", cascade="all, delete-orphan")


class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"))
    input_prompt = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    tags = Column(ARRAY(String), default=[])
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="rows")


# ─── Eval Run ────────────────────────────────────────────────────────────────

class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    model_endpoint_id = Column(UUID(as_uuid=True), ForeignKey("model_endpoints.id"))
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="queued")
    eval_types = Column(ARRAY(String), nullable=False)
    probe_ids = Column(ARRAY(String), nullable=True)
    concurrency = Column(Integer, default=5)
    baseline_id = Column(UUID(as_uuid=True), ForeignKey("baselines.id"), nullable=True)

    total_rows = Column(Integer, default=0)
    completed_rows = Column(Integer, default=0)

    # Aggregate scores
    hallucination_score = Column(Float, nullable=True)
    jailbreak_resistance_score = Column(Float, nullable=True)
    factual_accuracy_score = Column(Float, nullable=True)
    regression_pass_rate = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="eval_runs")
    dataset = relationship("Dataset")
    model_endpoint = relationship("ModelEndpoint", back_populates="eval_runs")
    results = relationship("EvalResult", back_populates="eval_run", cascade="all, delete-orphan")


# ─── Eval Result ─────────────────────────────────────────────────────────────

class EvalResult(Base):
    __tablename__ = "eval_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eval_run_id = Column(UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"))
    dataset_row_id = Column(UUID(as_uuid=True), ForeignKey("dataset_rows.id"), nullable=True)

    actual_output = Column(Text, nullable=False)

    # Hallucination
    hallucination_detected = Column(Boolean, nullable=True)
    hallucination_confidence = Column(Float, nullable=True)
    hallucination_reason = Column(Text, nullable=True)

    # Jailbreak
    jailbreak_succeeded = Column(Boolean, nullable=True)
    jailbreak_category = Column(String(100), nullable=True)
    jailbreak_probe_id = Column(String(50), nullable=True)
    language = Column(String(20), nullable=True, default="en")

    # Factual
    factual_score = Column(Float, nullable=True)

    # Semantic similarity
    similarity_score = Column(Float, nullable=True)
    output_embedding = Column(Vector(1536), nullable=True)

    # LLM judge
    judge_verdict = Column(String(50), nullable=True)
    judge_reasoning = Column(Text, nullable=True)

    latency_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    eval_run = relationship("EvalRun", back_populates="results")
    dataset_row = relationship("DatasetRow")


# ─── Baseline ────────────────────────────────────────────────────────────────

class Baseline(Base):
    __tablename__ = "baselines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))
    model_endpoint_id = Column(UUID(as_uuid=True), ForeignKey("model_endpoints.id"))
    eval_run_id = Column(UUID(as_uuid=True), ForeignKey("eval_runs.id"))
    name = Column(String(255), nullable=False)
    pinned_at = Column(DateTime, default=datetime.utcnow)


# ─── Alert Rule ──────────────────────────────────────────────────────────────

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    metric = Column(String(100), nullable=False)
    operator = Column(String(10), nullable=False)  # lt | gt | lte | gte
    threshold = Column(Float, nullable=False)
    notify_email = Column(ARRAY(String), default=[])
    notify_slack_webhook = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
