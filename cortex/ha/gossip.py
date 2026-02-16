"""
CORTEX v4.0 — Gossip Protocol.

Anti-entropy protocol for syncing state between nodes.
"""

import asyncio
import logging
import random
from typing import List, Optional

import aiosqlite

from cortex.ha.crdt import VectorClock

logger = logging.getLogger(__name__)


class GossipProtocol:
    """
    Anti-entropy gossip protocol.
    Syncs Merkle roots and CRDT states between peers.
    """

    def __init__(
        self,
        node_id: str,
        conn: aiosqlite.Connection,
        peers: List[str],
        interval: float = 30.0
    ):
        self.node_id = node_id
        self.conn = conn
        self.peers = peers
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start gossip loop."""
        self._running = True
        self._task = asyncio.create_task(self._gossip_loop())
        logger.info("GossipProtocol started")

    async def stop(self):
        """Stop gossip loop."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("GossipProtocol stopped")

    async def _gossip_loop(self):
        """Background loop to pick a peer and sync."""
        while self._running:
            try:
                if self.peers:
                    peer = random.choice(self.peers)
                    await self._perform_gossip(peer)
            except Exception as e:
                logger.error("Gossip error: %s", e)
            
            await asyncio.sleep(self.interval)

    async def _perform_gossip(self, peer: str):
        """
        Perform gossip exchange with a peer.
        
        1. Exchange Vector Clocks (to determine what's new)
        2. Compare Merkle Roots (to find data inconsistencies)
        3. Push/Pull missing data
        """
        # logger.debug(f"Gossiping with {peer}...")
        
        # Stub: HTTP/RPC call to peer
        # peer_clock = await client.get_vector_clock(peer)
        # my_clock = ...
        # compare ...
        pass
