from cortex.migrations.mig_base import (
    _migration_001_add_updated_at,
    _migration_002_add_indexes,
    _migration_003_enable_wal,
    _migration_004_vector_index,
    _migration_005_fts5_setup,
)
from cortex.migrations.mig_graph import _migration_006_graph_memory
from cortex.migrations.mig_consensus import (
    _migration_007_consensus_layer,
    _migration_008_consensus_refinement,
    _migration_009_reputation_consensus,
)
from cortex.migrations.mig_ledger import (
    _migration_010_immutable_ledger,
    _migration_011_link_facts_to_tx,
    _migration_012_ghosts_table,
)

MIGRATIONS = [
    (1, "Add updated_at column", _migration_001_add_updated_at),
    (2, "Add performance indexes", _migration_002_add_indexes),
    (3, "Enable WAL mode", _migration_003_enable_wal),
    (4, "Pruned embeddings table (replaces dead IVF)", _migration_004_vector_index),
    (5, "Setup FTS5 search", _migration_005_fts5_setup),
    (6, "Graph Memory tables", _migration_006_graph_memory),
    (7, "Consensus Layer (votes + score)", _migration_007_consensus_layer),
    (8, "Consensus refinement (index)", _migration_008_consensus_refinement),
    (9, "Reputation-Weighted Consensus", _migration_009_reputation_consensus),
    (10, "Immutable Ledger (Merkle)", _migration_010_immutable_ledger),
    (11, "Link facts to transactions", _migration_011_link_facts_to_tx),
    (12, "Add ghosts table", _migration_012_ghosts_table),
]
