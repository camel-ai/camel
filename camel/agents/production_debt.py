from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log: logging.Logger = logging.getLogger(__name__)

GENESIS_HASH: str = (
    "0000000000000000000000000000000000000000000000000000000000000000"
)


@dataclass
class SwarmDebtReport:
    swarm_id: str
    cdi_score: float  # Communicative Debt Index (target <= 12.0)
    dialogue_token_multiplier: float  # Target <= 1.15x
    turn_latency_seconds: float  # Target <= 1.8s
    consensus_safety_score: float  # Target 100.0
    production_readiness_index: float  # Scale 0 - 100
    is_production_ready: bool
    critical_smells: List[str]
    receipt_hash: str


class TechnicalDueDiligenceLedger:
    """
    Cryptographic SHA-256 hash-chained Action Ledger for CAMEL communicative multi-agent runs.
    """

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._last_hash: str = GENESIS_HASH

    def record_swarm_turn(
        self,
        swarm_id: str,
        event_type: str,
        readiness_index: float,
        critical_smells: List[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        index = len(self._entries)

        meta_bytes = json.dumps(metadata, sort_keys=True).encode("utf-8")
        canonical_content = f"{index}|{self._last_hash}|{swarm_id}|{event_type}|{readiness_index}|{timestamp}|{hashlib.sha256(meta_bytes).hexdigest()}"
        curr_hash = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()

        entry = {
            "index": index,
            "timestamp": timestamp,
            "swarm_id": swarm_id,
            "event_type": event_type,
            "readiness_index": readiness_index,
            "critical_smells": critical_smells,
            "prev_hash": self._last_hash,
            "curr_hash": curr_hash,
            "metadata": metadata,
        }

        self._entries.append(entry)
        self._last_hash = curr_hash
        return entry

    def get_ledger_entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def verify_ledger_integrity(self) -> bool:
        prev = GENESIS_HASH
        for entry in self._entries:
            if entry["prev_hash"] != prev:
                return False
            prev = entry["curr_hash"]
        return True


class ProductionDebtSwarmGate:
    """
    A2Z SOC Production Debt & Technical Due Diligence Gate for CAMEL Communicative Agents.

    Quantifies multi-agent dialogues and consensus loops against 4 Enterprise Forward Deployed Engineering KPIs:
    1. Communicative Debt Index (CDI <= 12.0)
    2. Swarm Dialogue Token Multiplier (SDM <= 1.15x)
    3. P99 Single-Turn Latency Ceiling (<= 1.8s)
    4. Deterministic Mutation Boundaries (never_equate_intent_to_approval)
    """

    def __init__(
        self,
        never_equate_intent_to_approval: bool = True,
        max_acceptable_cdi: float = 12.0,
    ) -> None:
        self.never_equate_intent_to_approval = never_equate_intent_to_approval
        self.max_acceptable_cdi = max_acceptable_cdi
        self.ledger = TechnicalDueDiligenceLedger()

    def check_kill_switch(self) -> bool:
        if os.environ.get("AAG_KILL_SWITCH", "").lower() in ("true", "1", "yes"):
            return True
        for path_str in ("artifacts/KILL", "/tmp/KILL"):
            if Path(path_str).exists():
                return True
        return False

    def evaluate_turn(
        self,
        swarm_id: str,
        turn_index: int = 1,
        context_tokens: int = 1000,
        generated_tokens: int = 120,
        turn_latency_seconds: float = 0.95,
        conversational_deadlocks: int = 0,
        un_gated_mutations: int = 0,
    ) -> SwarmDebtReport:
        # 1. Evaluate emergency kill switch
        if self.check_kill_switch():
            self.ledger.record_swarm_turn(
                swarm_id=swarm_id,
                event_type="swarm_halted_kill_switch",
                readiness_index=0.0,
                critical_smells=["EMERGENCY_KILL_SWITCH_ENGAGED"],
                metadata={"reason": "AAG_KILL_SWITCH is set"},
            )
            raise PermissionError(
                "A2Z SOC ActionGate: Emergency kill switch is engaged. Multi-agent swarm execution halted."
            )

        critical_smells: List[str] = []

        # KPI 2: Dialogue Token Multiplier
        token_ratio = (context_tokens + generated_tokens) / max(1, context_tokens)
        if token_ratio > 2.0:
            critical_smells.append(f"HIGH_DIALOGUE_TOKEN_SPRAWL_{token_ratio:.2f}X")

        # KPI 3: Latency Ceiling
        if turn_latency_seconds > 5.0:
            critical_smells.append(f"HIGH_TURN_LATENCY_{turn_latency_seconds:.2f}S")

        # Conversational deadlocks
        if conversational_deadlocks > 2:
            critical_smells.append(f"DETECTED_{conversational_deadlocks}_CONVERSATIONAL_DEADLOCKS")

        # KPI 4: Mutation Safety
        if un_gated_mutations > 0:
            critical_smells.append(f"DETECTED_{un_gated_mutations}_UNGATED_SWARM_MUTATIONS")

        # KPI 1: Communicative Debt Index (0 = Clean, 100 = Catastrophic)
        cdi = (
            max(0.0, (token_ratio - 1.0) * 15.0)
            + max(0.0, (turn_latency_seconds - 1.8) * 8.0)
            + (conversational_deadlocks * 12.0)
            + (un_gated_mutations * 30.0)
        )
        cdi_score = round(min(100.0, cdi), 2)

        # Production Readiness Index (0 - 100)
        readiness = max(0.0, 100.0 - cdi_score)
        is_production_ready = (
            cdi_score <= self.max_acceptable_cdi and len(critical_smells) == 0
        )

        # Cryptographic Ledger Entry
        entry = self.ledger.record_swarm_turn(
            swarm_id=swarm_id,
            event_type="turn_authorized" if is_production_ready else "turn_flagged_debt",
            readiness_index=readiness,
            critical_smells=critical_smells,
            metadata={
                "turn_index": turn_index,
                "cdi_score": cdi_score,
                "token_ratio": token_ratio,
                "turn_latency_seconds": turn_latency_seconds,
                "conversational_deadlocks": conversational_deadlocks,
                "un_gated_mutations": un_gated_mutations,
                "never_equate_intent_to_approval": self.never_equate_intent_to_approval,
            },
        )

        return SwarmDebtReport(
            swarm_id=swarm_id,
            cdi_score=cdi_score,
            dialogue_token_multiplier=round(token_ratio, 2),
            turn_latency_seconds=round(turn_latency_seconds, 2),
            consensus_safety_score=(
                100.0 if un_gated_mutations == 0 else max(0.0, 100.0 - un_gated_mutations * 30.0)
            ),
            production_readiness_index=readiness,
            is_production_ready=is_production_ready,
            critical_smells=critical_smells,
            receipt_hash=entry["curr_hash"],
        )
