#!/usr/bin/env python3
"""只验证 Graph Spec 的结构；不证明领域语义、锚点真实性或执行事实。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from common import MODES, NODE_KINDS, RELATIONS, STATES, load_json


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_root_goal(spec: dict[str, Any], errors: list[str]) -> None:
    root_goal = spec.get("root_goal")
    require(isinstance(root_goal, dict), "root_goal 必须是对象。", errors)
    if isinstance(root_goal, dict):
        for field in ("statement", "human_owner", "observable_success"):
            require(is_nonempty_string(root_goal.get(field)), f"root_goal.{field} 必须是非空字符串。", errors)


def validate_nodes(spec: dict[str, Any], errors: list[str]) -> tuple[set[str], dict[str, str]]:
    nodes = spec.get("nodes")
    require(isinstance(nodes, list) and bool(nodes), "nodes 必须是非空数组。", errors)
    ids: set[str] = set()
    kinds: dict[str, str] = {}
    if not isinstance(nodes, list):
        return ids, kinds
    for index, item in enumerate(nodes):
        prefix = f"nodes[{index}]"
        require(isinstance(item, dict), f"{prefix} 必须是对象。", errors)
        if not isinstance(item, dict):
            continue
        node_id = item.get("id")
        require(is_nonempty_string(node_id), f"{prefix}.id 必须是非空字符串。", errors)
        if is_nonempty_string(node_id):
            require(node_id not in ids, f"节点 ID 重复：{node_id}。", errors)
            ids.add(node_id)
            if is_nonempty_string(item.get("kind")):
                kinds[node_id] = item["kind"]
        require(item.get("kind") in NODE_KINDS, f"{prefix}.kind 必须是允许的节点类型。", errors)
        require(is_nonempty_string(item.get("responsibility")), f"{prefix}.responsibility 必须是非空字符串。", errors)
        require(is_nonempty_string(item.get("owner")), f"{prefix}.owner 必须是非空字符串。", errors)
        contract = item.get("contract")
        require(isinstance(contract, dict), f"{prefix}.contract 必须是对象。", errors)
        if isinstance(contract, dict):
            for field in ("inputs", "outputs"):
                value = contract.get(field)
                require(isinstance(value, list) and bool(value) and all(is_nonempty_string(v) for v in value), f"{prefix}.contract.{field} 必须是非空字符串数组。", errors)
    return ids, kinds


def validate_edges(spec: dict[str, Any], ids: set[str], errors: list[str]) -> list[dict[str, Any]]:
    edges = spec.get("edges")
    require(isinstance(edges, list), "edges 必须是数组。", errors)
    if not isinstance(edges, list):
        return []
    valid_edges: list[dict[str, Any]] = []
    for index, edge in enumerate(edges):
        prefix = f"edges[{index}]"
        require(isinstance(edge, dict), f"{prefix} 必须是对象。", errors)
        if not isinstance(edge, dict):
            continue
        require(edge.get("from") in ids, f"{prefix}.from 必须引用已知节点。", errors)
        require(edge.get("to") in ids, f"{prefix}.to 必须引用已知节点。", errors)
        require(edge.get("relation") in RELATIONS, f"{prefix}.relation 必须是允许的真实关系。", errors)
        require(is_nonempty_string(edge.get("artifact")), f"{prefix}.artifact 必须说明传递的产物或证据。", errors)
        valid_edges.append(edge)
    return valid_edges


def validate_graph_controls(spec: dict[str, Any], kinds: dict[str, str], edges: list[dict[str, Any]], errors: list[str]) -> None:
    mode = spec.get("mode")
    nodes = spec.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []
    kind_values = set(kinds.values())
    require("human_gate" in kind_values, "必须存在 human_gate。", errors)
    require("stop_handoff" in kind_values, "必须存在 stop_handoff。", errors)
    anchors = spec.get("anchors")
    if mode in {"graph", "graph_plus_loop"}:
        require("verification_loop" in kind_values, "Graph 必须存在独立 verification_loop。", errors)
        require("anchor" in kind_values, "Graph 必须存在 anchor 节点。", errors)
        verifiers = [item for item in nodes if isinstance(item, dict) and item.get("kind") == "verification_loop"]
        require(any(item.get("context_scope") == "fresh-independent" for item in verifiers), "Graph 验证者必须使用 fresh-independent 上下文。", errors)
        anchor_node_ids = {node_id for node_id, kind in kinds.items() if kind == "anchor"}
        require(isinstance(anchors, list) and bool(anchors), "Graph 必须至少有一个现实锚点。", errors)
        if isinstance(anchors, list):
            complete_anchor = any(
                isinstance(anchor, dict)
                and anchor.get("node_id") in anchor_node_ids
                and anchor.get("frozen") is True
                and is_nonempty_string(anchor.get("source"))
                and is_nonempty_string(anchor.get("evidence_form"))
                and is_nonempty_string(anchor.get("owner"))
                and is_nonempty_string(anchor.get("freshness_rule"))
                for anchor in anchors
            )
            require(complete_anchor, "Graph 必须有对应 anchor 节点、来源、证据形式、owner、freshness_rule 完整且 frozen 的现实锚点。", errors)
        require(any(edge.get("from") in anchor_node_ids and edge.get("relation") == "anchors" for edge in edges), "Graph 必须有从 anchor 节点发出的 anchors 边。", errors)
    permissions = spec.get("permissions")
    require(isinstance(permissions, dict) and is_nonempty_string(permissions.get("human_owner")), "permissions.human_owner 必须由人类指定。", errors)
    if isinstance(permissions, dict):
        allowed = permissions.get("allowed_actions")
        forbidden = permissions.get("forbidden_actions")
        require(isinstance(allowed, list) and all(is_nonempty_string(item) for item in allowed), "permissions.allowed_actions 必须是字符串数组。", errors)
        require(isinstance(forbidden, list) and all(is_nonempty_string(item) for item in forbidden), "permissions.forbidden_actions 必须是字符串数组。", errors)
        if isinstance(allowed, list) and isinstance(forbidden, list):
            require(not set(allowed).intersection(forbidden), "allowed_actions 与 forbidden_actions 不得冲突。", errors)
    frozen_rules = spec.get("frozen_rules")
    require(isinstance(frozen_rules, list) and bool(frozen_rules) and all(is_nonempty_string(item) for item in frozen_rules), "frozen_rules 必须是非空字符串数组。", errors)
    budget = spec.get("budget")
    require(isinstance(budget, dict), "budget 必须是对象。", errors)
    if isinstance(budget, dict):
        for field in ("max_agents", "max_concurrency", "max_cost_units"):
            require(is_integer(budget.get(field)) and budget[field] > 0, f"budget.{field} 必须是正整数。", errors)
        require(is_integer(budget.get("max_retries")) and budget["max_retries"] >= 0, "budget.max_retries 必须是非负整数。", errors)
        if is_integer(budget.get("max_agents")) and is_integer(budget.get("max_concurrency")):
            require(budget["max_concurrency"] <= budget["max_agents"], "max_concurrency 不得超过 max_agents。", errors)
    approval = spec.get("approval")
    require(isinstance(approval, dict) and approval.get("status") in {"pending", "approved", "rejected"}, "approval.status 必须是 pending、approved 或 rejected。", errors)
    if isinstance(approval, dict) and approval.get("status") == "approved":
        require(is_nonempty_string(approval.get("approved_by")), "批准状态必须记录 approved_by。", errors)
    if isinstance(approval, dict) and approval.get("status") == "rejected":
        require(spec.get("state") == "blocked", "审批被拒绝时 state 必须为 blocked。", errors)
    if spec.get("state") in {"ready", "executing"}:
        require(isinstance(approval, dict) and approval.get("status") == "approved" and is_nonempty_string(approval.get("approved_by")), "ready/executing 必须先取得人类批准。", errors)
    require(isinstance(spec.get("failure_policy"), dict) and bool(spec.get("failure_policy")), "必须定义 failure_policy。", errors)
    handoff = spec.get("stop_handoff")
    require(isinstance(handoff, dict) and is_nonempty_string(handoff.get("owner")) and isinstance(handoff.get("conditions"), list) and bool(handoff.get("conditions")) and all(is_nonempty_string(item) for item in handoff.get("conditions", [])) and is_nonempty_string(handoff.get("artifact")), "必须定义完整的 stop_handoff。", errors)
    execution_contract = spec.get("execution_contract")
    require(isinstance(execution_contract, dict) and isinstance(execution_contract.get("external_execution"), bool), "execution_contract.external_execution 必须是布尔值。", errors)
    if spec.get("state") == "executing":
        require(isinstance(execution_contract, dict) and execution_contract.get("external_execution") is True, "executing 必须显式允许 external_execution。", errors)
    if spec.get("state") == "completed":
        evidence = spec.get("reality_evidence")
        require(isinstance(evidence, list) and bool(evidence), "completed 必须有现实证据。", errors)


def validate(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(spec.get("schema_version") == "1.0", "schema_version 必须为 1.0。", errors)
    require(is_nonempty_string(spec.get("title")), "title 必须是非空字符串。", errors)
    require(spec.get("mode") in MODES, "mode 必须是支持的分类枚举。", errors)
    require(spec.get("state") in STATES, "state 必须是支持的状态枚举。", errors)
    validate_root_goal(spec, errors)
    ids, kinds = validate_nodes(spec, errors)
    edges = validate_edges(spec, ids, errors)
    validate_graph_controls(spec, kinds, edges, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 Graph Spec 的结构")
    parser.add_argument("graph_spec", type=Path)
    args = parser.parse_args()
    try:
        spec = load_json(args.graph_spec)
    except (OSError, ValueError) as error:
        print(f"无法读取 Graph Spec：{error}", file=sys.stderr)
        return 2
    errors = validate(spec)
    if errors:
        print("Graph Spec 结构校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Graph Spec 结构校验通过（不证明语义真实性、锚点独立性或外部执行）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
