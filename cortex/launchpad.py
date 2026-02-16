"""
CORTEX v4.0 — Launchpad Orchestration.

Bridge between the Python ledger and the Node.js Swarm engine.
"""

from __future__ import annotations

import json
import logging
import subprocess
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex.engine import CortexEngine, Fact

logger = logging.getLogger("cortex.launchpad")

# Default path to the swarm engine relative to home
DEFAULT_SWARM_PATH = "~/game/.agent/skills/autonomous-browser-swarm/scripts/swarm-v6-engine.js"

class MissionOrchestrator:
    """Manages Swarm mission lifecycles."""

    def __init__(self, engine: CortexEngine, swarm_path: Optional[str] = None):
        self.engine = engine
        self.swarm_path = Path(swarm_path or DEFAULT_SWARM_PATH).expanduser()

    def launch(
        self, 
        project: str, 
        goal: str, 
        formation: str = "IRON_DOME",
        agents: int = 10,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record intent and launch a swarm mission via subprocess."""
        
        # 1. Record the intent in the ledger
        intent_fact = {
            "project": project,
            "content": f"MISSION_INTENT: {goal} (Formation: {formation}, Agents: {agents})",
            "fact_type": "intent",
            "tags": ["swarm", "mission", "launch"],
            "confidence": "intended",
            "source": "cortex-launchpad"
        }
        
        fact_id = self.engine.store(**intent_fact)
        logger.info(f"Recorded mission intent #{fact_id} for project {project}")

        # 2. Build the command
        # Assumes node is in PATH
        cmd = [
            "node", 
            str(self.swarm_path),
            "--mission", goal,
            "--project", project,
            "--formation", formation,
            "--agents", str(agents)
        ]
        
        if context:
            cmd.extend(["--context", context])

        # 3. Execute (Async-ish for now, but blocking in CLI)
        try:
            logger.info(f"Executing swarm mission: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            output = result.stdout
            error = result.stderr
            status = "success" if result.returncode == 0 else "failed"

            # 4. Record the result
            result_fact = {
                "project": project,
                "content": f"MISSION_RESULT: {status}\nOutput: {output[:500]}...",
                "fact_type": "report",
                "tags": ["swarm", "result", status],
                "confidence": "verified" if status == "success" else "disputed",
                "source": "swarm-engine",
                "meta": {
                    "return_code": result.returncode,
                    "stderr": error[-1000:],
                    "intent_id": fact_id
                }
            }
            
            result_id = self.engine.store(**result_fact)
            
            return {
                "intent_id": fact_id,
                "result_id": result_id,
                "status": status,
                "stdout": output,
                "stderr": error
            }

        except Exception as e:
            logger.error(f"Failed to launch mission: {e}")
            return {
                "intent_id": fact_id,
                "status": "error",
                "error": str(e)
            }

    def list_missions(self, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent mission attempts from the ledger."""
        # Query facts of type 'intent' or 'report' with 'swarm' tag
        # For simplicity, we use the engine's recall/search or raw SQL
        conn = self.engine._get_conn()
        query = "SELECT id, project, content, created_at, fact_type FROM facts WHERE (fact_type = 'intent' OR fact_type = 'report') AND tags LIKE '%swarm%'"
        params = []
        if project:
            query += " AND project = ?"
            params.append(project)
        
        query += " ORDER BY created_at DESC LIMIT 20"
        
        rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": row[0],
                "project": row[1],
                "content": row[2],
                "created_at": row[3],
                "fact_type": row[4]
            } 
            for row in rows
        ]
