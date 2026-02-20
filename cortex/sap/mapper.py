"""CORTEX v4 — SAP Entity Mapper.

Transforms SAP OData entities into CORTEX facts and back.
Handles diffing for bidirectional sync.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.sap.mapper")

# SAP OData metadata keys to strip from entity payloads
_SAP_META_KEYS = frozenset({"__metadata", "__deferred", "__count", "results"})


@dataclass
class SyncDiff:
    """Result of diffing CORTEX facts against SAP entities."""

    new: list[dict[str, Any]] = field(default_factory=list)
    modified: list[dict[str, Any]] = field(default_factory=list)
    deleted: list[dict[str, Any]] = field(default_factory=list)
    unchanged: int = 0


class SAPMapper:
    """Bidirectional mapper between SAP entities and CORTEX facts."""

    @staticmethod
    def sap_to_fact(
        entity: dict[str, Any],
        entity_set: str,
        sap_base_url: str,
    ) -> dict[str, Any]:
        """Convert a SAP OData entity to a CORTEX fact dict.

        Args:
            entity: Raw SAP entity dict.
            entity_set: SAP entity set name.
            sap_base_url: SAP service base URL.

        Returns:
            Dict ready for CortexEngine.store().
        """
        # Strip OData metadata from the entity
        clean = {k: v for k, v in entity.items() if k not in _SAP_META_KEYS}

        # Extract SAP key from __metadata if available
        sap_key = ""
        metadata = entity.get("__metadata", {})
        if isinstance(metadata, dict):
            sap_key = metadata.get("uri", "")

        # Build a human-readable content summary
        content = json.dumps(clean, ensure_ascii=False, default=str)

        return {
            "project": f"sap-{entity_set.lower()}",
            "content": content,
            "fact_type": "sap_entity",
            "tags": [entity_set, "sap", "odata"],
            "source": "sap-connector",
            "meta": {
                "sap_key": sap_key,
                "entity_set": entity_set,
                "sap_base_url": sap_base_url,
                "sap_entity": clean,
            },
        }

    @staticmethod
    def fact_to_sap(fact: dict[str, Any]) -> dict[str, Any]:
        """Reconstruct a SAP entity from a CORTEX fact.

        Args:
            fact: CORTEX fact dict (must have meta.sap_entity).

        Returns:
            SAP entity dict ready for OData write-back.

        Raises:
            ValueError: If fact doesn't contain SAP entity data.
        """
        meta = fact.get("meta") or fact.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}

        sap_entity = meta.get("sap_entity")
        if sap_entity:
            return sap_entity

        # Fallback: try to parse content as JSON
        content = fact.get("content", "")
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Fact #{fact.get('id', '?')} has no SAP entity data") from e

    @staticmethod
    def extract_sap_key(fact: dict[str, Any]) -> str:
        """Extract the SAP key from a fact's metadata."""
        meta = fact.get("meta") or fact.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                return ""
        return meta.get("sap_key", "")

    @staticmethod
    def diff_entities(
        cortex_facts: list[dict[str, Any]],
        sap_entities: list[dict[str, Any]],
        entity_set: str,
        sap_base_url: str,
    ) -> SyncDiff:
        """Compute the diff between CORTEX facts and SAP entities.

        Args:
            cortex_facts: Existing CORTEX facts with SAP metadata.
            sap_entities: Current SAP entities.
            entity_set: SAP entity set name.
            sap_base_url: SAP service base URL.

        Returns:
            SyncDiff with new, modified, deleted, and unchanged counts.
        """
        diff = SyncDiff()

        # Index existing CORTEX facts by SAP key
        cortex_by_key: dict[str, dict] = {}
        for fact in cortex_facts:
            key = SAPMapper.extract_sap_key(fact)
            if key:
                cortex_by_key[key] = fact

        # Index SAP entities by their metadata URI
        for entity in sap_entities:
            metadata = entity.get("__metadata", {})
            sap_key = metadata.get("uri", "") if isinstance(metadata, dict) else ""

            if sap_key in cortex_by_key:
                # Exists in both — check for modification
                existing = cortex_by_key.pop(sap_key)
                existing_meta = existing.get("meta") or existing.get("metadata") or {}
                if isinstance(existing_meta, str):
                    try:
                        existing_meta = json.loads(existing_meta)
                    except json.JSONDecodeError:
                        existing_meta = {}

                existing_entity = existing_meta.get("sap_entity", {})
                clean = {k: v for k, v in entity.items() if k not in _SAP_META_KEYS}

                if _entities_differ(existing_entity, clean):
                    diff.modified.append(entity)
                else:
                    diff.unchanged += 1
            else:
                # New in SAP
                diff.new.append(entity)

        # Remaining in cortex_by_key = deleted from SAP
        diff.deleted = list(cortex_by_key.values())

        return diff


def _entities_differ(a: dict, b: dict) -> bool:
    """Compare two entity dicts, ignoring order and metadata fields."""
    # Normalize both by stripping metadata
    clean_a = {k: v for k, v in a.items() if k not in _SAP_META_KEYS}
    clean_b = {k: v for k, v in b.items() if k not in _SAP_META_KEYS}

    try:
        return json.dumps(clean_a, sort_keys=True, default=str) != json.dumps(
            clean_b, sort_keys=True, default=str
        )
    except (TypeError, ValueError):
        return clean_a != clean_b
