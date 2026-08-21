import importlib.util
import os
import sys
import unittest

# Load module directly
file_path = os.path.join(
    os.path.dirname(__file__),
    "../../camel/agents/production_debt.py",
)
spec = importlib.util.spec_from_file_location("camel_production_debt", file_path)
production_debt_mod = importlib.util.module_from_spec(spec)
sys.modules["camel_production_debt"] = production_debt_mod
spec.loader.exec_module(production_debt_mod)

ProductionDebtSwarmGate = production_debt_mod.ProductionDebtSwarmGate
TechnicalDueDiligenceLedger = production_debt_mod.TechnicalDueDiligenceLedger
GENESIS_HASH = production_debt_mod.GENESIS_HASH


class TestProductionDebtSwarmGate(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = ProductionDebtSwarmGate(
            never_equate_intent_to_approval=True,
            max_acceptable_cdi=12.0,
        )

    def test_clean_swarm_turn_passes_readiness(self) -> None:
        report = self.gate.evaluate_turn(
            swarm_id="swarm_enterprise_analyst_01",
            turn_index=1,
            context_tokens=1000,
            generated_tokens=120,
            turn_latency_seconds=0.95,
            conversational_deadlocks=0,
            un_gated_mutations=0,
        )
        self.assertTrue(report.is_production_ready)
        self.assertLessEqual(report.cdi_score, 12.0)
        self.assertEqual(len(report.critical_smells), 0)
        self.assertTrue(bool(report.receipt_hash))

    def test_degraded_swarm_fails_debt(self) -> None:
        report = self.gate.evaluate_turn(
            swarm_id="swarm_deadlock_loop",
            turn_index=15,
            context_tokens=1000,
            generated_tokens=2500,  # High token sprawl (3.5x)
            turn_latency_seconds=8.5,  # High latency
            conversational_deadlocks=4,  # 4 deadlock cycles
            un_gated_mutations=2,  # 2 un-gated mutations
        )
        self.assertFalse(report.is_production_ready)
        self.assertGreater(report.cdi_score, 50.0)
        self.assertIn("HIGH_DIALOGUE_TOKEN_SPRAWL_3.50X", report.critical_smells)
        self.assertIn("HIGH_TURN_LATENCY_8.50S", report.critical_smells)
        self.assertIn("DETECTED_4_CONVERSATIONAL_DEADLOCKS", report.critical_smells)
        self.assertIn("DETECTED_2_UNGATED_SWARM_MUTATIONS", report.critical_smells)

    def test_cryptographic_ledger_integrity(self) -> None:
        self.gate.evaluate_turn("swarm-1")
        self.gate.evaluate_turn("swarm-2")
        self.gate.evaluate_turn("swarm-3")

        entries = self.gate.ledger.get_ledger_entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["prev_hash"], GENESIS_HASH)
        self.assertEqual(entries[1]["prev_hash"], entries[0]["curr_hash"])
        self.assertEqual(entries[2]["prev_hash"], entries[1]["curr_hash"])
        self.assertTrue(self.gate.ledger.verify_ledger_integrity())


if __name__ == "__main__":
    unittest.main()
