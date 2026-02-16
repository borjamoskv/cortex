"""
CORTEX v4.0 — High Availability Layer.

Provides Raft consensus, CRDTs, and Gossip protocols for multi-node clusters.
"""

from .raft import NodeRole, RaftNode
from .crdt import VectorClock, LWWRegister
from .gossip import GossipProtocol
