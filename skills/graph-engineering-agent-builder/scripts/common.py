"""Graph Engineering Agent Builder 的共享确定性规则。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODES = {
    "direct",
    "loop",
    "linear_workflow",
    "graph",
    "graph_plus_loop",
    "blocked",
}
STATES = {
    "designed",
    "awaiting_approval",
    "ready",
    "executing",
    "blocked",
    "failed",
    "completed",
    "budget_exhausted",
}
NODE_KINDS = {
    "execution",
    "execution_loop",
    "verification_loop",
    "counter_metric_loop",
    "audit_loop",
    "arbitration",
    "governance_loop",
    "anchor",
    "human_gate",
    "stop_handoff",
    "reducer",
    "synthesis",
}
RELATIONS = {
    "feeds",
    "observes",
    "verifies",
    "constrains",
    "vetoes",
    "escalates",
    "arbitrates",
    "revises",
    "anchors",
    "hands_off",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是对象。")
    return data


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify(brief: dict[str, Any]) -> str:
    """只根据显式信号做保守分类，不从自然语言猜测权限或风险。"""
    root_goal = brief.get("root_goal", {})
    signals = brief.get("signals", {})
    if not isinstance(root_goal, dict) or not all(
        root_goal.get(key) for key in ("statement", "human_owner", "observable_success")
    ):
        return "blocked"
    if not isinstance(signals, dict) or not signals.get("task_clear", False):
        return "blocked"
    if signals.get("interacting_loops", False):
        return "graph_plus_loop" if signals.get("requires_iteration", False) else "graph"
    if signals.get("independent_responsibilities", False) and signals.get(
        "requires_independent_verification", False
    ):
        return "graph"
    if signals.get("requires_iteration", False):
        return "loop"
    if signals.get("sequential_dependencies", False):
        return "linear_workflow"
    return "direct"
