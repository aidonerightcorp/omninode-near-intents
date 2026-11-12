#!/usr/bin/env python3
"""Deterministic CLI runner (`do X -> see Y`) for interactive and automated repo evaluation."""

from __future__ import annotations

import argparse
import json
import pathlib

from src.grid_ledger_core import NodeGrid
from src.near_intent_quorum_adapter import OmniNodeNearSettlementCoordinator


def build_scenarios() -> dict[str, dict[str, object]]:
  return {
      "settle": {
          "intent_id": "near-intent-001",
          "expected_epoch": 0,
          "clause_text": "Deliver schema migration module passing 12 unit checks under 50 ms p95 latency",
          "gross_micro_units": 2500000,
          "maker_account": "maker-agent.testnet",
          "checker_account": "checker-guard.testnet",
          "coalition_accounts": [
              "planner-node.testnet",
              "maker-agent.testnet",
              "checker-guard.testnet",
          ],
          "capability_matrix": [
              [0.9, 0.2, 0.3],
              [0.3, 0.95, 0.4],
              [0.2, 0.3, 0.92],
          ],
          "stalk_vectors": {
              "planner": [0.82, 0.44, 0.91],
              "maker": [0.81, 0.45, 0.90],
              "checker": [0.82, 0.44, 0.90],
          },
          "sheaf_edges": [("planner", "maker", 1.0), ("maker", "checker", 1.0)],
      },
      "ambiguous": {
          "intent_id": "near-intent-002",
          "expected_epoch": 0,
          "clause_text": "Optimize indexer throughput asap on a best effort basis",
          "gross_micro_units": 1000000,
          "maker_account": "maker-agent.testnet",
          "checker_account": "checker-guard.testnet",
          "coalition_accounts": ["maker-agent.testnet", "checker-guard.testnet"],
          "capability_matrix": [[0.8, 0.4], [0.4, 0.8]],
          "stalk_vectors": {"maker": [1.0, 1.0], "checker": [1.0, 1.0]},
          "sheaf_edges": [("maker", "checker", 1.0)],
      },
      "tamper": {
          "intent_id": "near-intent-003",
          "expected_epoch": 0,
          "clause_text": "Produce signed price-feed aggregation report across 3 oracle relays within 5 bps",
          "gross_micro_units": 3000000,
          "maker_account": "maker-agent.testnet",
          "checker_account": "checker-guard.testnet",
          "coalition_accounts": ["maker-agent.testnet", "checker-guard.testnet"],
          "capability_matrix": [[0.9, 0.3], [0.3, 0.9]],
          "stalk_vectors": {
              "planner": [0.75, 0.80, 0.70],
              "relay": [0.74, 0.79, 0.71],
              "checker": [0.10, 0.15, 0.95],
          },
          "sheaf_edges": [("planner", "relay", 1.0), ("relay", "checker", 1.0)],
      },
      "runaway": {
          "intent_id": "near-intent-004",
          "expected_epoch": 0,
          "clause_text": "Execute batch cross-chain rebalance across 4 liquidity pools under 20 bps slippage",
          "gross_micro_units": 95000000,
          "maker_account": "maker-agent.testnet",
          "checker_account": "checker-guard.testnet",
          "coalition_accounts": ["maker-agent.testnet", "checker-guard.testnet"],
          "capability_matrix": [[0.8, 0.5], [0.5, 0.8]],
          "stalk_vectors": {"maker": [1.0, 1.0], "checker": [1.0, 1.0]},
          "sheaf_edges": [("maker", "checker", 1.0)],
      },
  }


def main() -> None:
  parser = argparse.ArgumentParser(description="OmniNode NEAR Intents & Swarm Escrow CLI")
  parser.add_argument(
      "--scenario",
      choices=["settle", "ambiguous", "tamper", "runaway", "all"],
      default="all",
  )
  parser.add_argument(
      "--live-readonly-check",
      action="store_true",
      help="Fetch live zero-spend cross-chain asset metadata from 1Click API and live NEAR Mainnet/Testnet RPC status.",
  )
  parser.add_argument(
      "--save-probe",
      default="",
      help="Optional relative or absolute file path to write the JSON output.",
  )
  args = parser.parse_args()

  root = pathlib.Path(__file__).resolve().parent
  grid = NodeGrid.from_json(root / "config" / "intent_quorum_grid.json")
  coord = OmniNodeNearSettlementCoordinator(grid)

  if args.live_readonly_check:
    out: object = coord.readonly_probe.run_live_readonly_check()
  else:
    scenarios = build_scenarios()
    if args.scenario == "all":
      out = {name: coord.execute_intent_envelope(env) for name, env in scenarios.items()}
    else:
      out = coord.execute_intent_envelope(scenarios[args.scenario])

  rendered = json.dumps(out, indent=2)
  if args.save_probe:
    target = pathlib.Path(args.save_probe)
    if not target.is_absolute():
      target = root / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered + "\n", encoding="utf-8")
  print(rendered)


if __name__ == "__main__":
  main()
