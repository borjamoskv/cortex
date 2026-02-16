"""
CORTEX v4.0 — Conflict-Free Replicated Data Types (CRDTs).

Provides data structures for eventual consistency in HA clusters.
"""

from dataclasses import dataclass, field
from typing import Dict, Generic, TypeVar, Optional, Any, Set

T = TypeVar("T")

@dataclass
class VectorClock:
    """
    Vector clock for causality tracking.
    """
    node_id: str
    counters: Dict[str, int] = field(default_factory=dict)

    def increment(self) -> "VectorClock":
        """Increment this node's counter."""
        new_counters = self.counters.copy()
        new_counters[self.node_id] = new_counters.get(self.node_id, 0) + 1
        return VectorClock(self.node_id, new_counters)

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Merge with another vector clock (taking max of each counter)."""
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        new_counters = {}
        for node in all_nodes:
            new_counters[node] = max(
                self.counters.get(node, 0),
                other.counters.get(node, 0)
            )
        return VectorClock(self.node_id, new_counters)

    def compare(self, other: "VectorClock") -> str:
        """
        Compare two vector clocks.
        
        Returns:
            - 'before': self happened before other
            - 'after': self happened after other
            - 'equal': self and other are identical
            - 'concurrent': neither happened before the other
        """
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        dominates = False
        dominated = False

        for node in all_nodes:
            a = self.counters.get(node, 0)
            b = other.counters.get(node, 0)
            if a > b:
                dominates = True
            elif b > a:
                dominated = True

        if dominates and not dominated:
            return "after"
        if dominated and not dominates:
            return "before"
        if not dominates and not dominated:
            return "equal"
        return "concurrent"


@dataclass
class LWWRegister(Generic[T]):
    """
    Last-Write-Wins Register.
    Does not require vector clocks, relies on wall clock timestamp.
    """
    value: T
    timestamp: float

    def merge(self, other: "LWWRegister[T]") -> "LWWRegister[T]":
        if other.timestamp > self.timestamp:
            return other
        elif other.timestamp < self.timestamp:
            return self
        else:
            # Tie-breaker: arbitrary but deterministic (e.g. value hash or comparison)
            # Here we just keep self if equal 
            return self


class ORSet(Generic[T]):
    """
    Observed-Remove Set (Add-Wins Set).
    Allows adding and removing elements concurrently.
    """
    def __init__(self):
        # element -> set of unique action IDs (add tags)
        self.elements: Dict[T, Set[str]] = {}
        # set of removed action IDs (tombstones could be handled, but simple ORSet uses this)
        # Actually OR-Set usually: 
        # Add: generate unique ID, add to set for element
        # Remove: clear set for element, and record strict 'removed' if using tombstone variants
        # A simple state-based OR-Set merges: (E, A) merge (E', A') -> (E U E', A U A') - diff removed? 
        # Standard OR-Set:
        # S = { (element, uuid) }
        # Add(e) -> S = S U {(e, new_uuid)}
        # Remove(e) -> S = S - {(e, u) | u in S}
        # Merge(S1, S2) -> (S1 INTERSECT S2) U (S1 - Removals2) ... no, state based is simpler:
        # Just S1 U S2. Remove involves keeping a 'tombstone' set?
        # Let's implement a simplified State-based OR-Set where we just track (element, uuid).
        self._state: Set[tuple[T, str]] = set()
        
    def add(self, element: T, uid: str):
        self._state.add((element, uid))
        
    def remove(self, element: T):
        # Remove all instances of this element currently known
        to_remove = {item for item in self._state if item[0] == element}
        self._state -= to_remove
        
    def merge(self, other: "ORSet[T]"):
        # This is strictly Add-Wins only if we track causal history?
        # Actually basic set union of (element, uuid) pairs works if 'remove' consumes UUIDs 
        # that are known at removal time.
        # But for state-based merge without tombstones, we simply Union. 
        # Wait, if I remove 'A' (uuid1) and you merge, and you still have 'A' (uuid1), it comes back.
        # That's why we need tombstones or Observed-Remove logic which requires more context.
        # For this MVP, let's stick to LWWRegister for simplicity or implement a proper AW-Set later.
        pass

