from pydantic import BaseModel, EmailStr, UUID4, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: Optional[str]

class UserOut(BaseModel):
    id: UUID4
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    class Config: from_attributes = True


# ─── Workspace ───────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

class WorkspaceOut(BaseModel):
    id: UUID4
    name: str
    slug: str
    plan: str
    created_at: datetime
    class Config: from_attributes = True


# ─── Model Endpoint ───────────────────────────────────────────────────────────

class ModelEndpointCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    name: str
    provider: str  # openai | anthropic | custom
    base_url: str
    model_name: str
    api_key: str   # raw — will be encrypted before storing
    system_prompt: Optional[str] = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=32000)

class ModelEndpointOut(BaseModel):
    id: UUID4
    name: str
    provider: str
    base_url: str
    model_name: str
    api_key_masked: str   # e.g. sk-...****
    system_prompt: Optional[str]
    temperature: float
    max_tokens: int
    created_at: datetime
    class Config: from_attributes = True

class ModelTestRequest(BaseModel):
    prompt: str = "Say hello in one sentence."

class ModelTestResponse(BaseModel):
    success: bool
    output: Optional[str]
    latency_ms: Optional[int]
    error: Optional[str]


# ─── Dataset ─────────────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # qa | jailbreak | factual | custom

class DatasetOut(BaseModel):
    id: UUID4
    name: str
    description: Optional[str]
    type: str
    row_count: int
    created_at: datetime
    class Config: from_attributes = True

class DatasetRowCreate(BaseModel):
    input_prompt: str
    expected_output: Optional[str] = None
    context: Optional[str] = None
    tags: List[str] = []

class DatasetRowOut(BaseModel):
    id: UUID4
    input_prompt: str
    expected_output: Optional[str]
    context: Optional[str]
    tags: List[str]
    created_at: datetime
    class Config: from_attributes = True

class DatasetRowsBulkCreate(BaseModel):
    rows: List[DatasetRowCreate]


# ─── Eval Run ────────────────────────────────────────────────────────────────

class EvalRunCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    dataset_id: Optional[UUID4] = None  # not required for jailbreak-only runs
    model_endpoint_id: UUID4
    eval_types: List[str] = Field(
        default=["factual"],
        description="List of: hallucination, jailbreak, regression, factual"
    )
    probe_ids: Optional[List[str]] = None  # which jailbreak probes to run; all probes if omitted
    baseline_id: Optional[UUID4] = None
    concurrency: int = Field(default=5, ge=1, le=20)

class EvalRunOut(BaseModel):
    id: UUID4
    dataset_id: Optional[UUID4]
    model_endpoint_id: UUID4
    status: str
    eval_types: List[str]
    total_rows: int
    completed_rows: int
    overall_score: Optional[float]
    hallucination_score: Optional[float]
    jailbreak_resistance_score: Optional[float]
    factual_accuracy_score: Optional[float]
    regression_pass_rate: Optional[float]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    class Config: from_attributes = True

class EvalResultOut(BaseModel):
    id: UUID4
    dataset_row_id: Optional[UUID4]
    actual_output: str
    hallucination_detected: Optional[bool]
    hallucination_confidence: Optional[float]
    hallucination_reason: Optional[str]
    jailbreak_succeeded: Optional[bool]
    jailbreak_category: Optional[str]
    jailbreak_probe_id: Optional[str]
    language: Optional[str]
    factual_score: Optional[float]
    similarity_score: Optional[float]
    judge_verdict: Optional[str]
    judge_reasoning: Optional[str]
    latency_ms: Optional[int]
    tokens_used: Optional[int]
    error: Optional[str]
    created_at: datetime
    class Config: from_attributes = True


# ─── Baseline ────────────────────────────────────────────────────────────────

class BaselineCreate(BaseModel):
    eval_run_id: UUID4
    name: str

class BaselineOut(BaseModel):
    id: UUID4
    eval_run_id: UUID4
    name: str
    pinned_at: datetime
    class Config: from_attributes = True


# ─── Alert ───────────────────────────────────────────────────────────────────

class AlertRuleCreate(BaseModel):
    name: str
    metric: str  # overall_score | jailbreak_resistance_score | hallucination_score
    operator: str  # lt | gt | lte | gte
    threshold: float
    notify_email: List[str] = []
    notify_slack_webhook: Optional[str] = None

class AlertRuleOut(BaseModel):
    id: UUID4
    name: str
    metric: str
    operator: str
    threshold: float
    notify_email: List[str]
    notify_slack_webhook: Optional[str]
    enabled: bool
    created_at: datetime
    class Config: from_attributes = True


# ─── Paginated Response ──────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    has_next: bool
