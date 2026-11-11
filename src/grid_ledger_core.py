"""Configuration Settings Grid, lifecycle ledger, and dynamic boundary expansion."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import pathlib
from typing import Any

LIFECYCLE_ORDER: tuple[str, ...] = (
    "represented",
    "applicable",
    "proposed",
    "dispatched",
    "evaluated",
    "attested",
    "promoted",
)


@dataclass(frozen=True)
class ParameterAxis:
  name: str
  kind: str
  default: Any
  low: int | None = None
  high: int | None = None
  choices: tuple[Any, ...] = ()

  def clamp(self, raw: Any) -> Any:
    if self.kind == "boolean":
      return bool(raw)
    if self.kind == "choice":
      return raw if raw in self.choices else self.default
    val = int(round(float(raw)))
    assert self.low is not None and self.high is not None
    return max(int(self.low), min(int(self.high), val))


@dataclass
class GridLedger:
  records: dict[str, str] = field(default_factory=dict)

  def register(self, cell_id: str) -> None:
    self.records.setdefault(cell_id, LIFECYCLE_ORDER[0])

  def advance(self, cell_id: str, target_stage: str) -> str:
    self.register(cell_id)
    cur_i = LIFECYCLE_ORDER.index(self.records[cell_id])
    tgt_i = LIFECYCLE_ORDER.index(target_stage)
    if tgt_i > cur_i + 1:
      raise ValueError(f"Non-monotonic transition {self.records[cell_id]} -> {target_stage}")
    self.records[cell_id] = target_stage
    return target_stage

  def promote_after_check(self, cell_id: str) -> str:
    for stg in LIFECYCLE_ORDER[1:]:
      cur_i = LIFECYCLE_ORDER.index(self.records.get(cell_id, LIFECYCLE_ORDER[0]))
      if LIFECYCLE_ORDER.index(stg) == cur_i + 1:
        self.advance(cell_id, stg)
    return self.records[cell_id]


class NodeGrid:
  def __init__(self, spec: dict[str, Any]):
    self.raw = spec
    self.generation = int(spec["generation"])
    self.constants: dict[str, Any] = dict(spec["operational_constants"])
    self.ambiguous_phrases: tuple[str, ...] = tuple(spec["ambiguous_phrases"])
    self.near_endpoints: dict[str, str] = dict(spec["near_endpoints"])
    self.axes: dict[str, ParameterAxis] = {}
    for p in spec["parameters"]:
      self.axes[p["name"]] = ParameterAxis(
          name=p["name"],
          kind=p["kind"],
          default=p["default"],
          low=p.get("low"),
          high=p.get("high"),
          choices=tuple(p.get("choices", [])),
      )
    self.constraints: list[dict[str, Any]] = list(spec.get("constraints", []))
    self.cells: dict[str, dict[str, Any]] = dict(spec["regime_cells"])
    self.ledger = GridLedger()
    for cid in self.cells:
      self.ledger.register(cid)

  @classmethod
  def from_json(cls, path: pathlib.Path) -> "NodeGrid":
    return cls(json.loads(path.read_text(encoding="utf-8")))

  def resolve_cell(self, regime: str = "default_swarm_settlement") -> dict[str, Any]:
    raw_cell = dict(self.cells[regime])
    cid = str(raw_cell.pop("cell_id"))
    clamped = {k: self.axes[k].clamp(v) for k, v in raw_cell.items() if k in self.axes}
    for rule in self.constraints:
      if int(clamped.get(rule["when_param"], 0)) >= int(rule["min_trigger"]):
        if clamped.get(rule["require_param"]) != rule["require_equals"]:
          raise ValueError(f"Constraint failed: {rule['id']}")
    return {"cell_id": cid, "values": clamped}

  def auto_expand_if_saturated(self, axis_name: str, observed_val: int) -> bool:
    ax = self.axes[axis_name]
    if ax.kind != "integer_range" or ax.high is None or ax.low is None:
      return False
    ratio = float(self.constants["saturation_ratio"])
    if float(observed_val) < float(ax.high) * ratio:
      return False
    num = int(self.constants["expansion_num"])
    den = int(self.constants["expansion_den"])
    new_high = max(ax.high + 1, (ax.high * num) // den)
    self.axes[axis_name] = ParameterAxis(
        name=ax.name, kind=ax.kind, default=ax.default, low=ax.low, high=new_high
    )
    self.generation += 1
    return True
