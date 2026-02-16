"""Graph Storage Backends - Base Class."""
from abc import ABC, abstractmethod
from typing import Optional

class GraphBackend(ABC):
    @abstractmethod
    async def upsert_entity(self, name: str, entity_type: str, project: str, timestamp: str) -> int | str:
        pass

    @abstractmethod
    async def upsert_relationship(self, source_id: int | str, target_id: int | str, relation_type: str, fact_id: int, timestamp: str) -> int | str:
        pass

    @abstractmethod
    async def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        pass

    @abstractmethod
    async def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        pass

    @abstractmethod
    async def upsert_ghost(self, reference: str, context: str, project: str, timestamp: str) -> int | str:
        pass

    @abstractmethod
    async def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float, timestamp: str) -> bool:
        pass

    @abstractmethod
    async def delete_fact_elements(self, fact_id: int) -> bool:
        """Delete all relationships and potentially nodes linked to a fact."""
        pass
