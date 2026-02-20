"""
CORTEX v4.0 — API Models.
Centralized Pydantic models for request/response validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class StoreRequest(BaseModel):
    project: str = Field(..., max_length=100, description="Project/namespace for the fact")
    content: str = Field(..., max_length=50000, description="The fact content")
    fact_type: str = Field(
        "knowledge", max_length=20, description="Type: knowledge, decision, mistake, bridge, ghost"
    )
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    source: str | None = Field(None, max_length=200, description="Source of the fact (e.g. agent name)")
    meta: dict | None = Field(None, description="Optional JSON metadata")

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
    as_of: str | None = Field(None, description="Temporal filter (ISO 8601)")
    fact_type: str | None = Field(None, description="Filter by fact type")
    tags: list[str] | None = Field(None, description="Filter by tags")
    graph_depth: int = Field(0, ge=0, le=5, description="Enable Graph-RAG (0=off, >0=depth of context traversal)")
    include_graph: bool = Field(False, description="Include the localized context subgraph in response")

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
    valid_from: str | None = None
    valid_until: str | None = None
    tx_id: int | None = None
    hash: str | None = None
    context: dict | None = Field(None, description="Graph-RAG context (subgraph or related entities)")


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
    confidence: str | None = None
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
    reason: str | None = Field(None, max_length=500)
    signature: str | None = Field(None, description="Optional cryptographic signature")


class FactResponse(BaseModel):
    id: int
    project: str
    content: str
    fact_type: str
    tags: list[str]
    created_at: str
    updated_at: str
    valid_from: str | None = None
    valid_until: str | None = None
    metadata: dict | None = None
    confidence: str = "stated"
    consensus_score: float = 1.0
    tx_id: int | None = None
    hash: str | None = None


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
    category: str | None = Field(None, max_length=50)
    branch: str | None = Field(None, max_length=255)
    language: str | None = Field(None, max_length=50)
    meta: dict | None = None


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
    result_id: int | None = None
    status: str
    stdout: str | None = None
    stderr: str | None = None


class LedgerReportResponse(BaseModel):
    valid: bool
    violations: list[dict[str, Any]]
    tx_checked: int = 0
    roots_checked: int = 0
    votes_checked: int = 0
    vote_checkpoints_checked: int = 0


class CheckpointResponse(BaseModel):
    checkpoint_id: int | None
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
    findings: list[str] = Field(default_factory=list)


class MejoraloScanResponse(BaseModel):
    project: str
    score: int
    stack: str
    dimensions: list[DimensionResultModel]
    dead_code: bool
    total_files: int = 0
    total_loc: int = 0
    fact_id: int | None = None


class MejoraloSessionRequest(BaseModel):
    project: str = Field(..., max_length=100)
    score_before: int = Field(..., ge=0, le=100)
    score_after: int = Field(..., ge=0, le=100)
    actions: list[str] = Field(default_factory=list)


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
    seals: list[ShipSealModel]
    passed: int
    total: int = 7


# ─── SovereignGate Models ────────────────────────────────────────────


class GateApprovalRequest(BaseModel):
    signature: str = Field(..., description="HMAC-SHA256 signature of the challenge")
    operator_id: str | None = Field(None, description="Operator identifier")


class GateActionResponse(BaseModel):
    action_id: str
    level: str
    description: str
    command: list[str] | None = None
    project: str | None = None
    status: str
    created_at: str
    approved_at: str | None = None
    operator_id: str | None = None


class GateStatusResponse(BaseModel):
    policy: str
    timeout_seconds: int
    pending: int = 0
    approved: int = 0
    denied: int = 0
    expired: int = 0
    executed: int = 0
    total_audit_entries: int = 0


# ─── Context Engine Models ───────────────────────────────────────────


class ContextSignalModel(BaseModel):
    source: str
    signal_type: str
    content: str
    project: str | None = None
    timestamp: str
    weight: float


class ProjectScoreModel(BaseModel):
    project: str
    score: float


class ContextSnapshotResponse(BaseModel):
    active_project: str | None = None
    confidence: str
    signals_used: int
    summary: str
    top_signals: list[ContextSignalModel] = Field(default_factory=list)
    projects_ranked: list[ProjectScoreModel] = Field(default_factory=list)
