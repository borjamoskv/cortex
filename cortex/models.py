"""
CORTEX v4.0 — API Models.
Centralized Pydantic models for request/response validation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class StoreRequest(BaseModel):
    project: str = Field(..., max_length=100, description="Project/namespace for the fact")
    content: str = Field(..., max_length=50000, description="The fact content")
    fact_type: str = Field(
        "knowledge", max_length=20, description="Type: knowledge, decision, mistake, bridge, ghost"
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    metadata: dict | None = Field(None, description="Optional JSON metadata")

    @field_validator("project", "content")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Must not be empty or whitespace only")
        return v


class StoreResponse(BaseModel):
    fact_id: int
    project: str
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=1024, description="Natural language search query")
    k: int = Field(5, ge=1, le=50, description="Number of results")
    project: str | None = Field(None, max_length=100, description="Filter by project")
    as_of: Optional[str] = Field(None, description="Temporal filter (ISO 8601)")
    fact_type: Optional[str] = Field(None, description="Filter by fact type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")

    @field_validator("query")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Must not be empty or whitespace only")
        return v


class SearchResult(BaseModel):
    fact_id: int
    project: str
    content: str
    fact_type: str
    score: float
    tags: list[str]
    consensus_score: float = 1.0
    created_at: str
    updated_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    tx_id: Optional[int] = None
    hash: Optional[str] = None


class VoteRequest(BaseModel):
    value: int = Field(..., description="1 to verify, -1 to dispute, 0 to remove")

    @field_validator("value")
    @classmethod
    def valid_vote(cls, v: int) -> int:
        if v not in (1, -1, 0):
            raise ValueError("Vote must be 1, -1, or 0")
        return v


class VoteResponse(BaseModel):
    fact_id: int
    agent: str
    vote: int
    new_consensus_score: float
    confidence: Optional[str] = None
    status: str = "recorded"


class AgentRegisterRequest(BaseModel):
    name: str = Field(..., max_length=100)
    agent_type: str = Field("ai", description="ai, human, oracle, system")
    public_key: str = Field("", description="Optional Ed25519 public key")


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    agent_type: str
    reputation_score: float
    created_at: str


class VoteV2Request(BaseModel):
    agent_id: str = Field(..., description="UUID of the registered agent")
    vote: int = Field(..., description="1 to verify, -1 to dispute, 0 to remove")
    reason: Optional[str] = Field(None, max_length=500)
    signature: Optional[str] = Field(None, description="Optional cryptographic signature")


class FactResponse(BaseModel):
    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    created_at: str
    updated_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    metadata: dict | None = None
    confidence: str = "stated"
    consensus_score: float = 1.0
    tx_id: Optional[int] = None
    hash: Optional[str] = None


class StatusResponse(BaseModel):
    version: str
    total_facts: int
    active_facts: int
    deprecated: int
    projects: int
    embeddings: int
    transactions: int
    db_size_mb: float


class HeartbeatRequest(BaseModel):
    project: str = Field(..., max_length=100)
    entity: str = Field("", max_length=1024)
    category: Optional[str] = Field(None, max_length=50)
    branch: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    meta: Optional[dict] = None


class TimeSummaryResponse(BaseModel):
    total_seconds: int
    total_hours: float
    by_category: dict[str, int]
    by_project: dict[str, int]
    entries: int
    heartbeats: int
    top_entities: list[list]  # [[entity, count], ...]


# ─── Mission Models ──────────────────────────────────────────────────


class MissionLaunchRequest(BaseModel):
    project: str = Field(..., max_length=100)
    goal: str = Field(..., max_length=2000)
    formation: str = "IRON_DOME"
    agents: int = Field(10, ge=1, le=50)


class MissionResponse(BaseModel):
    intent_id: int
    result_id: Optional[int] = None
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class LedgerReportResponse(BaseModel):
    valid: bool
    violations: List[Dict[str, Any]]
    tx_checked: int = 0
    roots_checked: int = 0
    votes_checked: int = 0
    vote_checkpoints_checked: int = 0


class CheckpointResponse(BaseModel):
    checkpoint_id: Optional[int]
    message: str
    status: str = "success"


# ─── MEJORAlo Models ────────────────────────────────────────────────


class MejoraloScanRequest(BaseModel):
    project: str = Field(..., max_length=100)
    path: str = Field(..., description="Ruta al directorio del proyecto")
    deep: bool = Field(False, description="Activa dimensión Psi + análisis profundo")


class DimensionResultModel(BaseModel):
    name: str
    score: int = Field(..., ge=0, le=100)
    weight: str
    findings: List[str] = Field(default_factory=list)


class MejoraloScanResponse(BaseModel):
    project: str
    score: int
    stack: str
    dimensions: List[DimensionResultModel]
    dead_code: bool
    total_files: int = 0
    total_loc: int = 0
    fact_id: Optional[int] = None


class MejoraloSessionRequest(BaseModel):
    project: str = Field(..., max_length=100)
    score_before: int = Field(..., ge=0, le=100)
    score_after: int = Field(..., ge=0, le=100)
    actions: List[str] = Field(default_factory=list)


class MejoraloSessionResponse(BaseModel):
    fact_id: int
    project: str
    delta: int
    status: str = "recorded"


class MejoraloShipRequest(BaseModel):
    project: str = Field(..., max_length=100)
    path: str = Field(..., description="Ruta al directorio del proyecto")


class ShipSealModel(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class MejoraloShipResponse(BaseModel):
    project: str
    ready: bool
    seals: List[ShipSealModel]
    passed: int
    total: int = 7


# ─── SovereignGate Models ────────────────────────────────────────────


class GateApprovalRequest(BaseModel):
    signature: str = Field(..., description="HMAC-SHA256 signature of the challenge")
    operator_id: Optional[str] = Field(None, description="Operator identifier")


class GateActionResponse(BaseModel):
    action_id: str
    level: str
    description: str
    command: Optional[List[str]] = None
    project: Optional[str] = None
    status: str
    created_at: str
    approved_at: Optional[str] = None
    operator_id: Optional[str] = None


class GateStatusResponse(BaseModel):
    policy: str
    timeout_seconds: int
    pending: int = 0
    approved: int = 0
    denied: int = 0
    expired: int = 0
    executed: int = 0
    total_audit_entries: int = 0
