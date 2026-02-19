"""
Interactive CLI approval logic for SovereignGate.
"""
import logging
import time
from typing import TYPE_CHECKING
from cortex.sovereign_gate import ActionStatus, GateNotApproved, GatePolicy

if TYPE_CHECKING:
    from cortex.sovereign_gate import SovereignGate

logger = logging.getLogger("cortex.gate.interact")


def approve_interactive(gate: "SovereignGate", action_id: str) -> bool:
    """
    Interactive CLI approval — prompts the operator directly.

    In AUDIT_ONLY mode, auto-approves with a log entry.
    In DISABLED mode, does nothing.
    """
    # Use private methods or access public API of gate
    # Since we moved this out, we need to access gate._get_action or add a public method
    # Let's assume we can access it via public API or we might need to adjust SovereignGate to expose it
    # But wait, SovereignGate._get_action is internal. 
    # Better to add a public method to get action by ID without side effects or use the private one if we are in the same package (python doesn't enforce private)
    # Actually, let's look at how it was used. It was a method on SovereignGate.
    
    # We will access the action via a new public getter or just use the private one for now as we are refactoring.
    try:
        action = gate._get_action(action_id)
    except Exception as e:
        logger.error(f"Failed to retrieve action {action_id}: {e}")
        return False

    if gate.policy == GatePolicy.DISABLED:
        action.status = ActionStatus.APPROVED
        return True

    if gate.policy == GatePolicy.AUDIT_ONLY:
        logger.info(
            "🔍 AUDIT: Action %s would require approval — %s",
            action_id,
            action.description,
        )
        action.status = ActionStatus.APPROVED
        action.approved_at = time.time()
        action.operator_id = "auto-audit"
        gate._log_audit("AUTO_APPROVED_AUDIT", action)
        return True

    # ENFORCE mode — actual interactive prompt
    print(f"\n{'=' * 60}")
    print("⚡ SOVEREIGN GATE — L3 ACTION APPROVAL REQUIRED")
    print(f"{'=' * 60}")
    print(f"  Action:  {action.description}")
    print(f"  Level:   {action.level.value}")
    print(f"  Project: {action.project or 'N/A'}")
    if action.command:
        cmd_str = " ".join(action.command)
        if len(cmd_str) > 100:
            cmd_str = cmd_str[:100] + "..."
        print(f"  Command: {cmd_str}")
    print(f"  ID:      {action_id}")
    print(f"{'=' * 60}")

    try:
        response = input("  ¿Aprobar ejecución? [s/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        response = "n"

    if response in ("s", "y", "si", "yes"):
        action.status = ActionStatus.APPROVED
        action.approved_at = time.time()
        action.operator_id = "interactive"
        gate._log_audit("ACTION_APPROVED_INTERACTIVE", action)
        logger.info("✅ Gate: Action %s approved interactively", action_id)
        return True
    else:
        action.status = ActionStatus.DENIED
        gate._log_audit("ACTION_DENIED", action)
        logger.warning("❌ Gate: Action %s denied by operator", action_id)
        raise GateNotApproved(f"Action {action_id} denied by operator")
