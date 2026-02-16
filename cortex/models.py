"""
CORTEX v4.0 — API Models.
Centralized Pydantic models for request/response validation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class StoreRequest(BaseModel):
    project: str = Field(..., max_length=100, description="Project/namespace for the fact")
    content: str = Field(..., max_length=50000, description="The fact content")
    fact_type: str = Field("knowledge", max_length=20, description="Type: knowledge, decision, mistake, bridge, ghost")
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    metadata: dict | None = Field(None, description="Optional JSON metadata")

    @field_validator("project", "content")
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
    
    @field_validator("query")
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
    valid_from: str
    valid_until: str | None
    metadata: dict | None
    confidence: str = "stated"
    consensus_score: float = 1.0


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
