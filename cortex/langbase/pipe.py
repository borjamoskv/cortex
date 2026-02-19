# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v4.2 — Langbase Pipe with CORTEX Context.

Run Langbase Pipes (AI agents) enriched with CORTEX memory.
The pipe receives relevant facts as context for grounded answers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine
    from cortex.langbase.client import LangbaseClient

logger = logging.getLogger("cortex.langbase.pipe")

# Template for injecting CORTEX facts into the pipe's context
CORTEX_CONTEXT_TEMPLATE = """## CORTEX Memory Context

The following facts are retrieved from CORTEX sovereign memory.
Use them to ground your response. Cite [Fact #ID] when referencing.

{facts}

## User Query

{query}"""


def _format_facts(facts: list) -> str:
    """Format CORTEX search results into a readable context block."""
    if not facts:
        return "(No relevant facts found in CORTEX memory.)"

    lines = []
    for i, fact in enumerate(facts, 1):
        fact_id = getattr(fact, "fact_id", "?")
        project = getattr(fact, "project", "?")
        score = getattr(fact, "score", 0.0)
        content = getattr(fact, "content", str(fact))
        fact_type = getattr(fact, "fact_type", "knowledge")

        lines.append(
            f"[Fact #{fact_id}] (project: {project}, type: {fact_type}, "
            f"relevance: {score:.3f})\n{content}"
        )

    return "\n\n".join(lines)


async def run_with_cortex_context(
    client: LangbaseClient,
    engine: AsyncCortexEngine,
    pipe_name: str,
    query: str,
    *,
    project: str | None = None,
    top_k: int = 10,
    thread_id: str | None = None,
    variables: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run a Langbase Pipe with CORTEX memory as context.

    Flow:
        1. Search CORTEX for relevant facts
        2. Format facts as context
        3. Send enriched query to Langbase Pipe
        4. Return pipe response + source facts

    Args:
        client: Langbase API client
        engine: CORTEX async engine
        pipe_name: Name of the Langbase Pipe to run
        query: User's question / prompt
        project: Filter CORTEX search by project (optional)
        top_k: Number of facts to retrieve for context
        thread_id: Langbase thread ID for conversation continuity
        variables: Optional pipe variables

    Returns:
        Dict with 'completion', 'sources', and 'facts_used'
    """
    # 1. Search CORTEX memory
    search_results = await engine.search(
        query=query,
        top_k=top_k,
        project=project,
    )
    logger.info(
        "CORTEX search for pipe '%s': %d facts found",
        pipe_name, len(search_results),
    )

    # 2. Build enriched message
    facts_text = _format_facts(search_results)
    enriched_content = CORTEX_CONTEXT_TEMPLATE.format(
        facts=facts_text,
        query=query,
    )

    messages = [{"role": "user", "content": enriched_content}]

    # 3. Run the Langbase Pipe
    pipe_result = await client.run_pipe(
        name=pipe_name,
        messages=messages,
        thread_id=thread_id,
        variables=variables,
    )

    # 4. Build response with provenance
    sources = [
        {
            "fact_id": getattr(r, "fact_id", None),
            "project": getattr(r, "project", None),
            "score": getattr(r, "score", 0.0),
            "content": getattr(r, "content", "")[:200],  # Truncate
        }
        for r in search_results
    ]

    return {
        "completion": pipe_result.get("completion", pipe_result),
        "pipe_name": pipe_name,
        "sources": sources,
        "facts_used": len(search_results),
        "thread_id": pipe_result.get("threadId"),
    }


async def create_cortex_pipe(
    client: LangbaseClient,
    name: str,
    *,
    description: str = "CORTEX-powered AI agent",
    model: str = "openai:gpt-4o-mini",
    memory_names: list[str] | None = None,
) -> dict:
    """Create a Langbase Pipe pre-configured for CORTEX integration.

    Args:
        client: Langbase API client
        name: Pipe name
        description: Human-readable description
        model: LLM model to use
        memory_names: Optional Langbase memories to attach

    Returns:
        Created pipe details
    """
    system_prompt = (
        "You are an AI agent powered by CORTEX sovereign memory. "
        "When facts from CORTEX are provided in the context, use them "
        "to ground your answers. Cite [Fact #ID] for traceability. "
        "Be concise, precise, and sovereign."
    )

    memory = None
    if memory_names:
        memory = [{"name": m} for m in memory_names]

    result = await client.create_pipe(
        name=name,
        description=description,
        model=model,
        system_prompt=system_prompt,
        memory=memory,
    )

    logger.info("Created CORTEX-powered pipe: %s", name)
    return result
