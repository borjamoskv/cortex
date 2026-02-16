"""
CORTEX v4.0 — Raft Consensus Implementation.

Handles leader election and log replication state.
"""

import asyncio
import logging
import random
import time
from enum import Enum
from typing import Optional, List, Callable, Awaitable

import aiosqlite

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"


class RaftNode:
    """
    Raft Consensus Node.

    Manages node state, election timeouts, and role transitions.
    Does not fully implement the log replication state machine (yet),
    focuses on Leader Election for the HA cluster.
    """

    HEARTBEAT_INTERVAL = 1.0  # seconds
    ELECTION_TIMEOUT_MIN = 3.0
    ELECTION_TIMEOUT_MAX = 6.0

    def __init__(
        self,
        node_id: str,
        conn: aiosqlite.Connection,
        peers: List[str],
        state_callback: Optional[Callable[[NodeRole], Awaitable[None]]] = None,
    ):
        self.node_id = node_id
        self.conn = conn
        self.peers = peers
        self.state_callback = state_callback

        self.role = NodeRole.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.leader_id: Optional[str] = None

        self.last_heartbeat = time.monotonic()
        self._running = False
        self._election_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the Raft node lifecycle."""
        self._running = True
        self._election_task = asyncio.create_task(self._election_loop())
        logger.info(f"RaftNode {self.node_id} started as FOLLOWER")

    async def stop(self):
        """Stop the Raft node."""
        self._running = False
        if self._election_task:
            self._election_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info(f"RaftNode {self.node_id} stopped")

    async def _election_loop(self):
        """Monitor heartbeat and trigger elections."""
        while self._running:
            timeout = random.uniform(self.ELECTION_TIMEOUT_MIN, self.ELECTION_TIMEOUT_MAX)
            await asyncio.sleep(0.1)  # check interval

            if self.role == NodeRole.LEADER:
                continue

            elapsed = time.monotonic() - self.last_heartbeat
            if elapsed > timeout:
                logger.warning(
                    f"Election timeout ({elapsed:.2f}s)! Starting election for term {self.current_term + 1}"
                )
                await self._start_election()

    async def _start_election(self):
        """Become Candidate and request votes."""
        self.role = NodeRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_heartbeat = time.monotonic()

        votes_received = 1  # Vote for self

        # In a real implementation, we would send RequestVote RPCs to peers here.
        # For now, we simulate a single-node cluster wins immediately if no peers,
        # or just log the attempt for multi-node checks.

        if not self.peers:
            logger.info("No peers. Self-electing as LEADER.")
            await self._become_leader()
            return

        # Stub: Request votes from peers (via HTTP/RPC)
        # ...

        # If majority received:
        # await self._become_leader()

    async def _become_leader(self):
        """Transition to Leader role."""
        if self.role == NodeRole.LEADER:
            return

        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        logger.info(f"Node {self.node_id} is now LEADER (Term {self.current_term})")

        if self.state_callback:
            await self.state_callback(self.role)

        # Start heartbeat loop
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Send heartbeats to followers."""
        while self._running and self.role == NodeRole.LEADER:
            # Stub: Send AppendEntries RPC (Heartbeat) to peers
            # logger.debug("Sending heartbeats...")

            # Update last_seen in DB for self
            await self._update_last_seen()

            await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    async def _update_last_seen(self):
        """Update last_seen_at in cluster_nodes table."""
        try:
            await self.conn.execute(
                "UPDATE cluster_nodes SET last_seen_at = datetime('now'), raft_role = ? WHERE node_id = ?",
                (self.role.value, self.node_id),
            )
            await self.conn.commit()
        except Exception as e:
            logger.error("Failed to update last_seen: %s", e)

    async def receive_heartbeat(self, leader_id: str, term: int):
        """Called when a heartbeat is received from the leader."""
        if term >= self.current_term:
            self.current_term = term
            self.leader_id = leader_id
            self.role = NodeRole.FOLLOWER
            self.last_heartbeat = time.monotonic()
            # logger.debug(f"Received heartbeat from {leader_id}")
