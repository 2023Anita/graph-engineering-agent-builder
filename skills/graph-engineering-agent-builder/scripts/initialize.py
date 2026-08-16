#!/usr/bin/env python3
"""从任务简报生成 Graph Engineering Agent Builder 的七个约定文件。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from common import classify, load_json, write_json


def node(
    node_id: str,
    kind: str,
    responsibility: str,
    inputs: list[str],
    outputs: list[str],
    owner: str,
    **extra: Any,
) -> dict[str, Any]:
    result = {
        "id": node_id,
        "kind": kind,
        "responsibility": responsibility,
        "owner": owner,
        "contract": {"inputs": inputs, "outputs": outputs},
    }
    result.update(extra)
    return result


def default_nodes(mode: str, owner: str) -> list[dict[str, Any]]:
    nodes = [
        node("human-approval", "human_gate", "确认根目标、锚点、权限与执行许可", ["graph-spec"], ["approval-record"], owner),
        node("stop-handoff", "stop_handoff", "在停止、失败或预算耗尽时交接", ["run-status"], ["handoff-record"], owner),
    ]
    if mode in {"graph", "graph_plus_loop"}:
        nodes[:0] = [
            node("reality-anchor", "anchor", "提供执行回路不能改写的现实证据", ["anchor-source"], ["reality-evidence"], owner),
            node("execution", "execution_loop", "在批准范围内产出候选结果", ["task-brief"], ["candidate-artifact"], "待实例化执行者", context_scope="execution-only"),
            node("verification", "verification_loop", "用独立上下文验证候选结果", ["candidate-artifact", "reality-evidence"], ["verification-report"], "待实例化独立验证者", context_scope="fresh-independent"),
            node("synthesis", "synthesis", "仅综合通过验证的结果", ["verification-report"], ["delivery-draft"], "待实例化综合器"),
        ]
    elif mode != "blocked":
        nodes.insert(0, node("execution", "execution", "在批准范围内完成任务", ["task-brief"], ["candidate-artifact"], "待实例化执行者"))
    return nodes


def default_edges(mode: str) -> list[dict[str, str]]:
    edges = [{"from": "human-approval", "to": "stop-handoff", "relation": "hands_off", "artifact": "approval-record"}]
    if mode in {"graph", "graph_plus_loop"}:
        edges[:0] = [
            {"from": "reality-anchor", "to": "verification", "relation": "anchors", "artifact": "reality-evidence"},
            {"from": "execution", "to": "verification", "relation": "feeds", "artifact": "candidate-artifact"},
            {"from": "verification", "to": "synthesis", "relation": "constrains", "artifact": "verification-report"},
            {"from": "human-approval", "to": "execution", "relation": "constrains", "artifact": "approval-record"},
            {"from": "synthesis", "to": "stop-handoff", "relation": "hands_off", "artifact": "delivery-draft"},
        ]
    return edges


def build_spec(brief: dict[str, Any], mode: str) -> dict[str, Any]:
    root_goal = brief.get("root_goal", {})
    owner = root_goal.get("human_owner", "待用户指定") if isinstance(root_goal, dict) else "待用户指定"
    approval = brief.get("approval", {}) if isinstance(brief.get("approval"), dict) else {}
    requested_status = approval.get("status")
    approved = requested_status == "approved" and bool(approval.get("approved_by"))
    rejected = requested_status == "rejected"
    approval_status = "approved" if approved else ("rejected" if rejected else "pending")
    if mode == "blocked" or rejected:
        state = "blocked"
    else:
        state = "ready" if approved else "awaiting_approval"
    design = brief.get("graph_design", {}) if isinstance(brief.get("graph_design"), dict) else {}
    return {
        "schema_version": "1.0",
        "title": brief.get("title", "未命名任务"),
        "mode": mode,
        "state": state,
        "root_goal": root_goal,
        "permissions": brief.get("permissions", {"human_owner": owner, "allowed_actions": [], "forbidden_actions": ["外部执行"]}),
        "frozen_rules": brief.get("frozen_rules", ["根目标、锚点和权限仅可由人类变更"]),
        "approval": {"status": approval_status, "approved_by": approval.get("approved_by"), "record": approval.get("record", "")},
        "budget": brief.get("budget", {"max_agents": 1, "max_concurrency": 1, "max_retries": 0, "max_cost_units": 1}),
        "anchors": design.get("anchors", brief.get("anchors", [])),
        "nodes": design.get("nodes", default_nodes(mode, owner)),
        "edges": design.get("edges", default_edges(mode)),
        "failure_policy": brief.get("failure_policy", {"on_validation_failure": "stop_and_handoff", "on_budget_exhausted": "handoff_to_human"}),
        "stop_handoff": brief.get("stop_handoff", {"owner": owner, "conditions": ["验证失败", "预算耗尽", "权限不足"], "artifact": "handoff-record"}),
        "execution_contract": {"external_execution": False, "note": "本 MVP 只生成准备与记录文件，不执行领域任务。"},
    }


def write_reports(destination: Path, brief: dict[str, Any], spec: dict[str, Any]) -> None:
    mode = spec["mode"]
    destination.joinpath("task-assessment.md").write_text(
        f"# 任务判断\n\n- 任务：{brief.get('title', '未命名任务')}\n- 分类：`{mode}`\n- 原则：只依据简报中明确的信号分类；Graph 需要真实职责、独立验证或相互作用回路。\n",
        encoding="utf-8",
    )
    destination.joinpath("solution-options.md").write_text(
        "# 方案评估\n\n"
        f"- 推荐：`{mode}`\n"
        "- 候选：direct、loop、linear_workflow、graph、graph_plus_loop。\n"
        "- 成本与风险：以 `graph-spec.json` 的预算、权限、锚点和失败策略为准；未经批准不执行。\n",
        encoding="utf-8",
    )
    destination.joinpath("execution-plan.md").write_text(
        "# 执行计划\n\n"
        f"当前状态：`{spec['state']}`。执行前必须有有效人类批准；本文件不启动任何外部任务。\n",
        encoding="utf-8",
    )
    destination.joinpath("validation-plan.md").write_text(
        "# 验证计划\n\n运行 `python3 scripts/validate_graph.py graph-spec.json` 检查结构。"
        "该检查不能证明锚点语义真实、证据新鲜或领域任务已执行。\n",
        encoding="utf-8",
    )
    destination.joinpath("run-report.md").write_text("# 运行报告\n\n- 状态：未运行\n- 外部任务：未执行\n- 证据：无\n", encoding="utf-8")
    destination.joinpath("final-delivery.md").write_text("# 最终交付\n\n- 状态：未交付\n- 现实证据：无\n- 未解决事项：等待批准或领域执行。\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Graph Engineering Agent Builder 契约文件")
    parser.add_argument("task_brief", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        print(f"拒绝覆盖已存在的输出目录：{args.output_dir}", file=sys.stderr)
        return 2
    try:
        brief = load_json(args.task_brief)
    except (OSError, ValueError) as error:
        print(f"无法读取任务简报：{error}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    mode = classify(brief)
    spec = build_spec(brief, mode)
    write_json(args.output_dir / "graph-spec.json", spec)
    write_reports(args.output_dir, brief, spec)
    print(f"已生成七个约定文件：{args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
