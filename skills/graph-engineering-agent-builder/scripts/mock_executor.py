#!/usr/bin/env python3
"""本地确定性 Graph 调度模拟器；不调用真实 Agent、模型、网络或任意代码。"""

from __future__ import annotations

import argparse
import concurrent.futures
import sys
from pathlib import Path
from typing import Any

from common import load_json, write_json
from validate_graph import validate


def preflight_errors(spec: dict[str, Any]) -> list[str]:
    """返回 Mock Executor 特有的执行前置条件错误。"""
    errors = validate(spec)
    approval = spec.get("approval")
    if not isinstance(approval, dict) or approval.get("status") != "approved":
        errors.append("Mock Executor 只接受 approval.status=approved 的 Graph Spec。")
    elif not isinstance(approval.get("approved_by"), str) or not approval["approved_by"].strip():
        errors.append("Mock Executor 要求批准记录包含非空 approved_by。")
    if spec.get("state") != "ready":
        errors.append("Mock Executor 只接受 state=ready 的 Graph Spec。")
    execution_contract = spec.get("execution_contract")
    if not isinstance(execution_contract, dict) or execution_contract.get("external_execution") is not False:
        errors.append("Mock Executor 只允许 execution_contract.external_execution=false。")
    return errors


def make_artifact(node: dict[str, Any], status: str) -> dict[str, Any]:
    kind = node["kind"]
    evidence_kind = {
        "anchor": "synthetic-reality-evidence",
        "execution": "synthetic-candidate",
        "execution_loop": "synthetic-candidate",
        "verification_loop": "synthetic-verification-report",
        "synthesis": "synthetic-draft",
        "human_gate": "synthetic-approval-record",
        "stop_handoff": "synthetic-handoff-record",
    }.get(kind, "synthetic-node-artifact")
    return {
        "node_id": node["id"],
        "status": status,
        "outputs": node["contract"]["outputs"],
        "evidence_kind": evidence_kind,
        "synthetic": True,
    }


def run_node(node: dict[str, Any], predecessors: list[dict[str, Any]], fail_node: str | None) -> dict[str, Any]:
    """执行一个不具副作用的确定性节点模拟。"""
    node_id = node["id"]
    kind = node["kind"]
    if node_id == fail_node:
        return {**make_artifact(node, "failed"), "error": "测试失败注入。"}
    if kind == "verification_loop":
        independent = node.get("context_scope") == "fresh-independent"
        inputs_ready = bool(predecessors) and all(item.get("status") == "passed" for item in predecessors)
        status = "passed" if independent and inputs_ready else "failed"
        result = make_artifact(node, status)
        if status == "failed":
            result["error"] = "验证节点需要 fresh-independent 上下文和完整的成功上游输入。"
        return result
    if kind == "synthesis":
        verification_passed = any(
            item.get("kind") == "verification_loop" and item.get("status") == "passed" for item in predecessors
        )
        status = "passed" if verification_passed else "failed"
        result = make_artifact(node, status)
        if status == "failed":
            result["error"] = "综合节点只可消费已通过的独立验证结果。"
        return result
    if kind == "human_gate":
        status = "passed"
    else:
        status = "passed"
    return make_artifact(node, status)


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Mock Executor 运行报告",
        "",
        f"- 运行状态：`{report['run_status']}`",
        "- 领域任务完成声明：`false`（仅本地确定性模拟）",
        f"- 下一步：{report['next_action']}",
        "",
        "## 批次",
        "",
    ]
    for batch in report["batches"]:
        lines.append(f"- 批次 {batch['batch']}: {', '.join(batch['nodes'])} — {batch['status']}")
    lines.extend(["", "## 节点结果", ""])
    for result in report["node_results"]:
        lines.append(f"- `{result['node_id']}` ({result['kind']}): {result['status']}")
    if report["missing_nodes"]:
        lines.extend(["", "## 未运行节点", "", *[f"- `{node_id}`" for node_id in report["missing_nodes"]]])
    if report.get("failure"):
        lines.extend(["", "## 失败", "", f"{report['failure']}"])
    lines.append("")
    return "\n".join(lines)


def execute(spec: dict[str, Any], fail_node: str | None = None) -> dict[str, Any]:
    """依据边的 from→to 关系模拟拓扑执行，并返回可序列化的运行报告。"""
    nodes = spec["nodes"]
    node_by_id = {node["id"]: node for node in nodes}
    dependencies: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    children: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    for edge in spec["edges"]:
        source, target = edge["from"], edge["to"]
        dependencies[target].add(source)
        children[source].add(target)

    max_workers = min(spec["budget"]["max_concurrency"], spec["budget"]["max_agents"])
    pending = set(node_by_id)
    results: dict[str, dict[str, Any]] = {}
    batches: list[dict[str, Any]] = []
    batch_number = 0
    failure: str | None = None

    while pending:
        blocked = [
            node_id for node_id in pending
            if any(results.get(parent, {}).get("status") in {"failed", "skipped"} for parent in dependencies[node_id])
        ]
        for node_id in blocked:
            node = node_by_id[node_id]
            results[node_id] = {
                **make_artifact(node, "skipped"),
                "kind": node["kind"],
                "reason": "上游节点失败或未运行，按 Graph 依赖规则跳过。",
            }
            pending.remove(node_id)
        if blocked:
            failure = failure or "一个或多个节点失败；其下游已阻止运行。"
            continue

        ready = [node_id for node_id in node_by_id if node_id in pending and all(parent in results and results[parent]["status"] == "passed" for parent in dependencies[node_id])]
        if not ready:
            cycle_nodes = sorted(pending)
            failure = f"检测到 cycle 或无法满足的依赖：{', '.join(cycle_nodes)}。"
            break
        batch_number += 1
        batch_nodes = ready[:max_workers]
        predecessor_results = {
            node_id: [results[parent] for parent in dependencies[node_id]] for node_id in batch_nodes
        }
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch_nodes)) as executor:
            futures = {
                node_id: executor.submit(run_node, node_by_id[node_id], predecessor_results[node_id], fail_node)
                for node_id in batch_nodes
            }
            for node_id in batch_nodes:
                result = futures[node_id].result()
                result["kind"] = node_by_id[node_id]["kind"]
                results[node_id] = result
                pending.remove(node_id)
        batch_status = "failed" if any(results[node_id]["status"] == "failed" for node_id in batch_nodes) else "completed"
        batches.append({"batch": batch_number, "nodes": batch_nodes, "status": batch_status})
        if batch_status == "failed":
            failure = failure or "节点模拟失败；不会继续其下游节点。"

    missing_nodes = [node["id"] for node in nodes if node["id"] not in results]
    ordered_results = [results[node["id"]] for node in nodes if node["id"] in results]
    synthetic_artifacts = [result for result in ordered_results if result["status"] == "passed"]
    run_status = "simulated_success" if not failure and not missing_nodes else "failed"
    return {
        "run_status": run_status,
        "domain_completion_claimed": False,
        "batches": batches,
        "node_results": ordered_results,
        "missing_nodes": missing_nodes,
        "synthetic_artifacts": synthetic_artifacts,
        "failure": failure,
        "next_action": "由人类审阅合成运行记录；不得据此宣称领域任务已经完成。" if run_status == "simulated_success" else "检查失败节点与依赖；由人类决定修订 Spec、重试或交接。",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行本地确定性 Mock Graph Executor")
    parser.add_argument("graph_spec", type=Path)
    parser.add_argument("run_output_dir", type=Path)
    parser.add_argument("--fail-node", help="仅测试使用：使指定节点模拟失败")
    args = parser.parse_args()
    if args.run_output_dir.exists():
        print(f"拒绝覆盖已存在的运行输出目录：{args.run_output_dir}", file=sys.stderr)
        return 2
    try:
        spec = load_json(args.graph_spec)
    except (OSError, ValueError) as error:
        print(f"无法读取 Graph Spec：{error}", file=sys.stderr)
        return 2
    errors = preflight_errors(spec)
    if errors:
        print("Mock Executor 执行前检查失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    report = execute(spec, args.fail_node)
    args.run_output_dir.mkdir(parents=True)
    write_json(args.run_output_dir / "run-report.json", report)
    (args.run_output_dir / "run-report.md").write_text(markdown_report(report), encoding="utf-8")
    print(f"Mock Executor 已写入运行报告：{args.run_output_dir}")
    return 0 if report["run_status"] == "simulated_success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
