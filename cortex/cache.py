"""
CORTEX v4.0 — Tiered Caching Strategy.

Multi-level cache with L1 (Memory) and PubSub invalidation.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from enum import Enum
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar('T')

logger = logging.getLogger(__name__)


class CacheEvent(Enum):
    INVALIDATE = "invalidate"
    WARM = "warm"
    CLEAR = "clear"


class TieredCache(Generic[T]):
    """
    Multi-tier cache with pub/sub invalidation.
    
    Tiers:
    - L1: In-memory LRU (per-process)
    - L2/L3: (Future) Redis or Persistent Store
    """

    def __init__(
        self,
        name: str,
        l1_size: int = 1000,
        ttl_seconds: float = 300.0
    ):
        self.name = name
        self.l1: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self.l1_size = l1_size
        self.ttl = ttl_seconds
        self._subscribers: List[asyncio.Queue] = []

    async def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        # L1 check
        if key in self.l1:
            expiry, value = self.l1[key]
            if time.monotonic() > expiry:
                del self.l1[key]
                return None
            
            # Move to end (LRU)
            self.l1.move_to_end(key)
            return value
        
        return None

    async def set(self, key: str, value: T, ttl: Optional[float] = None):
        """Set value in cache."""
        expiry = time.monotonic() + (ttl or self.ttl)
        
        # L1 insert
        self.l1[key] = (expiry, value)
        self.l1.move_to_end(key)
        
        # Evict oldest if over capacity
        while len(self.l1) > self.l1_size:
            self.l1.popitem(last=False)
        
        # Notify subscribers
        await self._notify(CacheEvent.WARM, key)

    async def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern (simple substring match for now)."""
        # Remove from L1
        keys_to_remove = [k for k in self.l1.keys() if pattern in k]
        for k in keys_to_remove:
            del self.l1[k]
        
        await self._notify(CacheEvent.INVALIDATE, pattern)

    async def clear(self):
        """Clear all cache entries."""
        self.l1.clear()
        await self._notify(CacheEvent.CLEAR, "all")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to cache events."""
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    async def _notify(self, event: CacheEvent, key: str):
        """Notify all subscribers."""
        for queue in self._subscribers:
            try:
                queue.put_nowait((event, key))
            except asyncio.QueueFull:
                pass
