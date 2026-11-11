"""Automated Conformance & Functional Suite for OmniNode NEAR Intents & Swarm Quorum."""

from __future__ import annotations

import ast
import json
import os
import pathlib
import subprocess
import sys
import unittest

from src.grid_ledger_core import NodeGrid
from src.near_intent_quorum_adapter import OmniNodeNearSettlementCoordinator

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRID_PATH = ROOT / "config" / "intent_quorum_grid.json"
ALLOWED_SCALARS = {0, 1, -1, 0.0, 1.0, -1.0}
FORBIDDEN_VERTICAL_WORDS = (
    "realestate", "real_estate", "mortgage", "healthcare",
    "hospitality", "ecommerce", "parcel", "pokemon", "football",
)


class NearIntentQuorumSuite(unittest.TestCase):

  def setUp(self) -> None:
    self.grid = NodeGrid.from_json(GRID_PATH)
    self.coord = OmniNodeNearSettlementCoordinator(self.grid)

  def test_01_zero_hardcoded_values_ast_gate(self) -> None:
    violations: list[str] = []
    for py_path in sorted((ROOT / "src").glob("*.py")):
      tree = ast.parse(py_path.read_text(encoding="utf-8"))
      for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
            and node.value not in ALLOWED_SCALARS
        ):
          violations.append(f"{py_path.name}:{node.lineno}:{node.value!r}")
    self.assertEqual(violations, [])

  def test_02_domain_agnostic_naming_gate(self) -> None:
    for p in ROOT.rglob("*"):
      if ".git" in p.parts or "__pycache__" in p.parts or ".pytest_cache" in p.parts:
        continue
      low = p.name.lower()
      for word in FORBIDDEN_VERTICAL_WORDS:
        self.assertNotIn(word, low)

  def test_03_zero_local_home_paths_gate(self) -> None:
    for p in ROOT.rglob("*"):
      if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts:
        if p.name == "test_near_intent_quorum.py":
          continue
        txt = p.read_text(encoding="utf-8", errors="ignore").lower()
        self.assertNotIn("/" + "home/", txt, f"Path leak in {p}")

  def test_04_grid_ledger_and_boundary_auto_expansion(self) -> None:
    cell = self.grid.resolve_cell()
    self.assertEqual(cell["cell_id"], "cell_near_swarm_g1")
    with self.assertRaises(ValueError):
      self.grid.ledger.advance("cell_near_swarm_g1", "promoted")
    expanded = self.grid.auto_expand_if_saturated("max_call_spend_micro_units", 48000000)
    self.assertTrue(expanded)
    self.assertGreater(self.grid.axes["max_call_spend_micro_units"].high, 50000000)

  def test_05_asd_ste100_rejects_vague_intent_pre_lock(self) -> None:
    res = self.coord.execute_intent_envelope({
        "intent_id": "i-vague",
        "expected_epoch": 0,
        "clause_text": "Ship cross-chain bridge adapter asap with best effort",
        "gross_micro_units": 500000,
        "maker_account": "maker.testnet",
        "checker_account": "checker.testnet",
        "coalition_accounts": ["maker.testnet", "checker.testnet"],
        "capability_matrix": [[0.8, 0.2], [0.2, 0.8]],
        "stalk_vectors": {"a": [1.0], "b": [1.0]},
        "sheaf_edges": [("a", "b", 1.0)],
    })
    self.assertEqual(res["status"], "REJECTED_PRE_LOCK_AMBIGUOUS_CLAUSE")

  def test_06_cas_lease_epoch_blocks_replay(self) -> None:
    env = {
        "intent_id": "i-replay",
        "expected_epoch": 0,
        "clause_text": "Deliver deterministic state proof passing 10 unit checks",
        "gross_micro_units": 1000000,
        "maker_account": "maker.testnet",
        "checker_account": "checker.testnet",
        "coalition_accounts": ["maker.testnet", "checker.testnet"],
        "capability_matrix": [[0.8, 0.2], [0.2, 0.8]],
        "stalk_vectors": {"a": [1.0], "b": [1.0]},
        "sheaf_edges": [("a", "b", 1.0)],
    }
    first = self.coord.execute_intent_envelope(env)
    self.assertEqual(first["status"], "SETTLED_VIA_NEAR_INTENTS_AND_SHAPLEY")
    replay = self.coord.execute_intent_envelope(env)
    self.assertEqual(replay["status"], "REJECTED_STALE_LEASE_EPOCH")

  def test_07_wasm_spend_guardrail_blocks_overspend(self) -> None:
    res = self.coord.execute_intent_envelope({
        "intent_id": "i-overspend",
        "expected_epoch": 0,
        "clause_text": "Rebalance liquidity across 4 pools within 15 bps tolerance",
        "gross_micro_units": 99000000,
        "maker_account": "maker.testnet",
        "checker_account": "checker.testnet",
        "coalition_accounts": ["maker.testnet", "checker.testnet"],
        "capability_matrix": [[0.8, 0.2], [0.2, 0.8]],
        "stalk_vectors": {"a": [1.0], "b": [1.0]},
        "sheaf_edges": [("a", "b", 1.0)],
    })
    self.assertEqual(res["status"], "ABORTED_BY_WASM_SPEND_GUARDRAIL")
    self.assertEqual(res["spend_check"]["wasm_byte_length"], 50)

  def test_08_disjoint_maker_checker_blocks_self_approval(self) -> None:
    res = self.coord.execute_intent_envelope({
        "intent_id": "i-self",
        "expected_epoch": 0,
        "clause_text": "Execute state transition check across 5 validator shards",
        "gross_micro_units": 1000000,
        "maker_account": "same-agent.testnet",
        "checker_account": "same-agent.testnet",
        "coalition_accounts": ["same-agent.testnet"],
        "capability_matrix": [[1.0]],
        "stalk_vectors": {"a": [1.0], "b": [1.0]},
        "sheaf_edges": [("a", "b", 1.0)],
    })
    self.assertEqual(res["status"], "REJECTED_BY_QUORUM_POLICY")

  def test_09_cellular_sheaf_pinpoints_tampered_edge(self) -> None:
    res = self.coord.execute_intent_envelope({
        "intent_id": "i-sheaf",
        "expected_epoch": 0,
        "clause_text": "Aggregate oracle median across 3 independent price feeds",
        "gross_micro_units": 1500000,
        "maker_account": "maker.testnet",
        "checker_account": "checker.testnet",
        "coalition_accounts": ["maker.testnet", "checker.testnet"],
        "capability_matrix": [[0.9, 0.2], [0.2, 0.9]],
        "stalk_vectors": {"s0": [0.9, 0.9], "s1": [0.89, 0.91], "s2": [0.1, 0.1]},
        "sheaf_edges": [("s0", "s1", 1.0), ("s1", "s2", 1.0)],
    })
    self.assertEqual(res["status"], "HELD_ON_SHEAF_OBSTRUCTION")
    self.assertEqual(res["sheaf_check"]["top_obstruction_edge"], "s1->s2")

  def test_10_exact_shapley_conservation_and_dry_quotes(self) -> None:
    res = self.coord.execute_intent_envelope({
        "intent_id": "i-shapley",
        "expected_epoch": 0,
        "clause_text": "Complete 3-stage indexing and audit pipeline under 40 ms p95",
        "gross_micro_units": 3333333,
        "maker_account": "maker.testnet",
        "checker_account": "checker.testnet",
        "coalition_accounts": ["planner.testnet", "maker.testnet", "checker.testnet"],
        "capability_matrix": [[0.9, 0.1, 0.2], [0.2, 0.95, 0.3], [0.1, 0.2, 0.9]],
        "stalk_vectors": {"p": [0.5, 0.5], "m": [0.5, 0.5], "c": [0.5, 0.5]},
        "sheaf_edges": [("p", "m", 1.0), ("m", "c", 1.0)],
    })
    self.assertEqual(res["status"], "SETTLED_VIA_NEAR_INTENTS_AND_SHAPLEY")
    sh = res["shapley_settlement"]
    self.assertTrue(sh["exact_conservation"])
    self.assertEqual(sh["net_micro_units"], sh["sum_allocated_micro_units"])
    self.assertEqual(len(res["near_intents_dry_quotes"]), 3)
    self.assertTrue(all(q["quote"]["dry"] is True for q in res["near_intents_dry_quotes"]))

  def test_11_cli_do_x_see_y_reproducibility(self) -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "--scenario", "all"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(proc.stdout)
    self.assertEqual(doc["settle"]["status"], "SETTLED_VIA_NEAR_INTENTS_AND_SHAPLEY")
    self.assertEqual(doc["ambiguous"]["status"], "REJECTED_PRE_LOCK_AMBIGUOUS_CLAUSE")
    self.assertEqual(doc["tamper"]["status"], "HELD_ON_SHEAF_OBSTRUCTION")
    self.assertEqual(doc["runaway"]["status"], "ABORTED_BY_WASM_SPEND_GUARDRAIL")

  def test_12_studio_html_paper_and_ink_light_mode(self) -> None:
    html = (ROOT / "web" / "omninode-near-studio.html").read_text(encoding="utf-8")
    self.assertIn("color-scheme: only light", html)
    self.assertIn("#f5f2ea", html.lower())
    self.assertIn("WebAssembly.instantiate", html)


if __name__ == "__main__":
  unittest.main()
