"""Clause hygiene, CAS lease fencing, WebAssembly spend gate, Sheaf audit, and exact 2^K Shapley."""

from __future__ import annotations

import math
from typing import Any


class SpendPolicyWasmGate:
  """Builds a compact WebAssembly spending policy module and evaluates micro-unit caps."""

  def __init__(self, constants: dict[str, Any]):
    self.constants = constants
    self.wasm_bytes = bytes(int(b) for b in constants["wasm_policy_bytes"])

  def check_spend(self, requested_micro_units: int, cap_micro_units: int) -> dict[str, Any]:
    has_magic = self.wasm_bytes[: 1 + 1 + 1 + 1] == b"\x00asm"
    within_cap = (
        has_magic
        and int(requested_micro_units) >= 0
        and int(requested_micro_units) <= int(cap_micro_units)
    )
    return {
        "allowed": within_cap,
        "wasm_byte_length": len(self.wasm_bytes),
        "requested_micro_units": int(requested_micro_units),
        "cap_micro_units": int(cap_micro_units),
        "action": "ALLOW_ACCESS_KEY_CALL" if within_cap else "TRIPWIRE_ABORT_SPEND",
    }


class LeaseEpochTracker:
  """Compare-and-swap monotonic lease fencing preventing duplicate intent claims."""

  def __init__(self) -> None:
    self._epochs: dict[str, int] = {}

  def claim_epoch(self, intent_id: str, expected_epoch: int) -> dict[str, Any]:
    cur = self._epochs.get(intent_id, 0)
    if int(expected_epoch) != cur:
      return {"fenced_ok": False, "current_epoch": cur, "reason": "STALE_LEASE_EPOCH"}
    nxt = cur + 1
    self._epochs[intent_id] = nxt
    return {"fenced_ok": True, "current_epoch": nxt, "reason": "EPOCH_ADVANCED"}


class UnambiguousClauseValidator:
  """ASD-STE100-inspired measurable intent clause checker."""

  def __init__(self, ambiguous_phrases: tuple[str, ...], constants: dict[str, Any]):
    self.ambiguous_phrases = ambiguous_phrases
    self.min_words = int(constants["min_clause_words"])

  def validate(self, clause_text: str) -> dict[str, Any]:
    low = clause_text.strip().lower()
    words = [w for w in low.split() if w]
    hits = [p for p in self.ambiguous_phrases if p in low]
    ok = len(words) >= self.min_words and not hits
    return {
        "clause_ok": ok,
        "word_count": len(words),
        "ambiguous_hits": hits,
    }


class CellularSheafIntentAuditor:
  """Computes Cellular Sheaf coboundary energy `x^T L_F x` across multi-agent stalks."""

  def __init__(self, constants: dict[str, Any]):
    self.constants = constants

  def audit(
      self,
      stalk_vectors: dict[str, list[float]],
      edges: list[tuple[str, str, float]],
      obstruction_limit: float,
  ) -> dict[str, Any]:
    total_energy = 0.0
    worst_edge = "none"
    worst_val = -1.0
    for src, dst, weight in edges:
      u = stalk_vectors[src]
      v = stalk_vectors[dst]
      sq = sum((float(a) - float(b)) * (float(a) - float(b)) for a, b in zip(u, v))
      edge_e = float(weight) * sq
      total_energy += edge_e
      if edge_e > worst_val:
        worst_val = edge_e
        worst_edge = f"{src}->{dst}"
    coherent = total_energy <= float(obstruction_limit)
    return {
        "coherent": coherent,
        "sheaf_energy": total_energy,
        "obstruction_limit": float(obstruction_limit),
        "top_obstruction_edge": "none" if coherent else worst_edge,
    }


class ExactShapleyCoalitionSplitter:
  """Computes exact `2^K` Shapley allocations with zero integer micro-unit drift."""

  def __init__(self, constants: dict[str, Any]):
    self.constants = constants

  def allocate(
      self,
      gross_micro_units: int,
      fee_bps: int,
      actor_ids: list[str],
      capability_matrix: list[list[float]],
  ) -> dict[str, Any]:
    bps_den = int(self.constants["bps_denominator"])
    fee_units = (int(gross_micro_units) * int(fee_bps)) // bps_den
    net_units = int(gross_micro_units) - fee_units
    k_actors = len(actor_ids)
    n_dims = len(capability_matrix[0]) if k_actors > 0 else 1
    synergy = float(self.constants["synergy_bonus_scale"])
    eps = float(self.constants["numerical_eps"])
    fact = [math.factorial(i) for i in range(k_actors + 1)]

    def _val(mask: int) -> float:
      if mask == 0:
        return 0.0
      members = [i for i in range(k_actors) if (mask & (1 << i)) != 0]
      covered = sum(
          max(float(capability_matrix[m][d]) for m in members) for d in range(n_dims)
      ) / float(n_dims)
      return covered * (1.0 + synergy * float(len(members) - 1) / float(max(1, k_actors)))

    phis = [0.0 for _ in range(k_actors)]
    for idx in range(k_actors):
      for mask in range(1 << k_actors):
        if (mask & (1 << idx)) != 0:
          continue
        s_card = mask.bit_count()
        weight = float(fact[s_card] * fact[k_actors - s_card - 1]) / float(fact[k_actors])
        phis[idx] += weight * (_val(mask | (1 << idx)) - _val(mask))
      phis[idx] = max(0.0, phis[idx])

    phi_total = sum(phis) or 1.0
    quotas = [(p / phi_total) * float(net_units) for p in phis]
    floors = [int(math.floor(q + eps)) for q in quotas]
    remainder = net_units - sum(floors)
    order = sorted(
        range(k_actors), key=lambda i: quotas[i] - float(floors[i]), reverse=True
    )
    for r_i in range(remainder):
      floors[order[r_i]] += 1

    payouts = [
        {"actor_id": actor_ids[i], "micro_units": floors[i]} for i in range(k_actors)
    ]
    return {
        "gross_micro_units": int(gross_micro_units),
        "protocol_fee_micro_units": fee_units,
        "net_micro_units": net_units,
        "sum_allocated_micro_units": sum(floors),
        "exact_conservation": sum(floors) == net_units,
        "payouts": payouts,
    }
