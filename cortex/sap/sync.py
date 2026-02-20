"""CORTEX v4 — SAP Bidirectional Sync Engine.

Pulls SAP entities into CORTEX facts and pushes modified facts back to SAP.
Supports configurable conflict resolution strategies.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from cortex.sap.client import SAPClient
from cortex.sap.mapper import SAPMapper

logger = logging.getLogger("cortex.sap.sync")


@dataclass
class SAPSyncResult:
    """Result of a SAP sync operation."""

    pulled: int = 0
    pushed: int = 0
    skipped: int = 0
    conflicts: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "completed"


class SAPSync:
    """Bidirectional sync engine between SAP OData and CORTEX.

    Usage:
        client = SAPClient(config)
        await client.connect()
        sync = SAPSync(client, engine)
        result = await sync.pull("A_BusinessPartner", "sap-partners")
    """

    def __init__(self, client: SAPClient, engine: Any) -> None:
        """Initialize sync with SAP client and CORTEX engine.

        Args:
            client: Connected SAPClient instance.
            engine: CortexEngine or AsyncCortexEngine instance.
        """
        self.client = client
        self.engine = engine
        self.mapper = SAPMapper()

    async def pull(
        self,
        entity_set: str,
        project: str,
        *,
        filters: str | None = None,
        top: int = 100,
    ) -> SAPSyncResult:
        """Pull entities from SAP into CORTEX.

        Fetches entities from the SAP entity set and stores them as CORTEX
        facts. Uses diff to avoid re-storing unchanged entities.

        Args:
            entity_set: SAP entity set name.
            project: CORTEX project to store facts in.
            filters: OData $filter expression.
            top: Maximum entities to pull.

        Returns:
            SAPSyncResult with pull counts.
        """
        result = SAPSyncResult()

        try:
            # Fetch from SAP
            entities = await self.client.read_entity_set(
                entity_set, filters=filters, top=top
            )
            logger.info("Fetched %d entities from SAP/%s", len(entities), entity_set)

            # Get existing CORTEX facts for this entity set
            existing_facts = await self._get_sap_facts(project)

            # Compute diff
            diff = self.mapper.diff_entities(
                existing_facts,
                entities,
                entity_set,
                self.client.config.base_url_normalized,
            )

            # Store new entities
            for entity in diff.new:
                try:
                    fact_data = self.mapper.sap_to_fact(
                        entity, entity_set, self.client.config.base_url_normalized
                    )
                    # Override project with user-specified project
                    fact_data["project"] = project
                    await self._store_fact(fact_data)
                    result.pulled += 1
                except (OSError, ValueError, KeyError) as e:
                    result.errors.append(f"Failed to store entity: {e}")

            # Update modified entities
            for entity in diff.modified:
                try:
                    fact_data = self.mapper.sap_to_fact(
                        entity, entity_set, self.client.config.base_url_normalized
                    )
                    fact_data["project"] = project
                    await self._store_fact(fact_data)
                    result.pulled += 1
                except (OSError, ValueError, KeyError) as e:
                    result.errors.append(f"Failed to update entity: {e}")

            result.skipped = diff.unchanged

        except (OSError, ValueError, KeyError) as e:
            result.errors.append(f"Pull failed: {e}")
            result.status = "error"

        return result

    async def push(
        self,
        project: str,
        entity_set: str,
    ) -> SAPSyncResult:
        """Push modified CORTEX facts back to SAP.

        Finds facts tagged as SAP entities that have been modified in CORTEX
        and writes them back to the SAP system.

        Args:
            project: CORTEX project containing SAP facts.
            entity_set: Target SAP entity set.

        Returns:
            SAPSyncResult with push counts.
        """
        result = SAPSyncResult()

        try:
            facts = await self._get_sap_facts(project)
            sap_facts = [
                f for f in facts
                if self._fact_matches_entity_set(f, entity_set)
            ]

            for fact in sap_facts:
                try:
                    entity_data = self.mapper.fact_to_sap(fact)
                    sap_key = self.mapper.extract_sap_key(fact)

                    if sap_key:
                        # Extract just the key portion from the URI
                        key_part = self._extract_key_from_uri(sap_key, entity_set)
                        if key_part:
                            await self.client.update_entity(entity_set, key_part, entity_data)
                            result.pushed += 1
                        else:
                            result.errors.append(f"Cannot extract key from URI: {sap_key}")
                    else:
                        await self.client.create_entity(entity_set, entity_data)
                        result.pushed += 1

                except (OSError, ValueError, KeyError) as e:
                    result.errors.append(f"Push failed for fact #{fact.get('id', '?')}: {e}")

        except (OSError, ValueError, KeyError) as e:
            result.errors.append(f"Push failed: {e}")
            result.status = "error"

        return result

    async def full_sync(
        self,
        entity_set: str,
        project: str,
        *,
        conflict_strategy: str = "sap_wins",
        filters: str | None = None,
        top: int = 100,
    ) -> SAPSyncResult:
        """Full bidirectional sync.

        1. Pull from SAP → CORTEX
        2. Push from CORTEX → SAP (if strategy allows)

        Args:
            entity_set: SAP entity set name.
            project: CORTEX project.
            conflict_strategy: 'sap_wins' | 'cortex_wins' | 'manual'.
            filters: OData $filter expression.
            top: Maximum entities.

        Returns:
            Combined SAPSyncResult.
        """
        combined = SAPSyncResult()

        # Step 1: Pull (SAP → CORTEX)
        pull_result = await self.pull(entity_set, project, filters=filters, top=top)
        combined.pulled = pull_result.pulled
        combined.skipped = pull_result.skipped
        combined.errors.extend(pull_result.errors)

        # Step 2: Push (CORTEX → SAP) — only if cortex_wins
        if conflict_strategy == "cortex_wins":
            push_result = await self.push(project, entity_set)
            combined.pushed = push_result.pushed
            combined.errors.extend(push_result.errors)
        elif conflict_strategy == "manual":
            combined.conflicts = pull_result.pulled  # Flag as needing review

        if combined.errors:
            combined.status = "completed_with_errors"

        return combined

    # ─── Internal Helpers ────────────────────────────────────────────

    async def _get_sap_facts(self, project: str) -> list[dict[str, Any]]:
        """Retrieve existing SAP facts from CORTEX."""
        try:
            # Try async engine first
            if hasattr(self.engine, "recall") and asyncio.iscoroutinefunction(
                getattr(self.engine, "recall", None)
            ):
                facts = await self.engine.recall(project=project)
            else:
                facts = self.engine.recall_sync(project=project)

            return [f for f in facts if f.get("fact_type") == "sap_entity"]
        except (OSError, ValueError, KeyError):
            logger.warning("Failed to recall SAP facts for project %s", project)
            return []

    async def _store_fact(self, fact_data: dict[str, Any]) -> int:
        """Store a fact using the available engine interface."""
        if hasattr(self.engine, "store") and asyncio.iscoroutinefunction(
            getattr(self.engine, "store", None)
        ):
            return await self.engine.store(
                project=fact_data["project"],
                content=fact_data["content"],
                fact_type=fact_data["fact_type"],
                tags=fact_data.get("tags", []),
                source=fact_data.get("source"),
                meta=fact_data.get("meta"),
            )
        else:
            return self.engine.store_sync(
                project=fact_data["project"],
                content=fact_data["content"],
                fact_type=fact_data["fact_type"],
                tags=fact_data.get("tags", []),
            )

    @staticmethod
    def _fact_matches_entity_set(fact: dict[str, Any], entity_set: str) -> bool:
        """Check if a fact belongs to a specific SAP entity set."""
        meta = fact.get("meta") or fact.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                return False
        return meta.get("entity_set") == entity_set

    @staticmethod
    def _extract_key_from_uri(uri: str, entity_set: str) -> str:
        """Extract key portion from SAP URI.

        Example:
            URI: "BusinessPartnerSet('1000001')"
            Returns: "'1000001'"
        """
        # Find the key between parentheses after entity set name
        marker = f"{entity_set}("
        idx = uri.find(marker)
        if idx < 0:
            # Try without the full URI path
            for segment in uri.split("/"):
                if "(" in segment:
                    start = segment.index("(")
                    return segment[start + 1 : -1] if segment.endswith(")") else ""
            return ""

        start = idx + len(marker)
        end = uri.find(")", start)
        if end < 0:
            return ""
        return uri[start:end]


# Needed for async detection in _get_sap_facts / _store_fact
import asyncio  # noqa: E402
