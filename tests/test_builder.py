"""Graph Engineering Agent Builder 的标准库回归测试。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "graph-engineering-agent-builder"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import load_json  # noqa: E402
from validate_graph import validate  # noqa: E402


class BuilderTests(unittest.TestCase):
    def test_valid_example_passes(self) -> None:
        spec = load_json(ROOT / "examples" / "valid-graph.json")
        self.assertEqual(validate(spec), [])

    def test_graph_without_anchor_fails(self) -> None:
        spec = load_json(ROOT / "examples" / "valid-graph.json")
        spec["anchors"] = []
        self.assertTrue(any("现实锚点" in message for message in validate(spec)))

    def test_graph_without_independent_verifier_fails(self) -> None:
        spec = load_json(ROOT / "examples" / "valid-graph.json")
        for item in spec["nodes"]:
            if item["kind"] == "verification_loop":
                item["context_scope"] = "shared-execution"
        self.assertTrue(any("fresh-independent" in message for message in validate(spec)))

    def test_rejected_approval_is_blocked(self) -> None:
        brief = load_json(ROOT / "examples" / "valid-task-brief.json")
        brief["approval"] = {"status": "rejected", "record": "负责人拒绝当前方案"}
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
            output = Path(directory) / "contract"
            command = [sys.executable, str(SCRIPTS / "initialize.py"), str(brief_path), str(output)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            spec = load_json(output / "graph-spec.json")
            self.assertEqual(spec["approval"]["status"], "rejected")
            self.assertEqual(spec["state"], "blocked")
            self.assertEqual(validate(spec), [])

    def test_boolean_budget_is_rejected(self) -> None:
        spec = load_json(ROOT / "examples" / "valid-graph.json")
        spec["budget"]["max_agents"] = True
        self.assertTrue(any("max_agents" in message for message in validate(spec)))

    def test_executing_requires_approval_and_external_execution(self) -> None:
        spec = load_json(ROOT / "examples" / "valid-graph.json")
        spec["state"] = "executing"
        messages = validate(spec)
        self.assertTrue(any("人类批准" in message for message in messages))
        self.assertTrue(any("external_execution" in message for message in messages))

    def test_initializer_creates_contract_and_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "contract"
            command = [sys.executable, str(SCRIPTS / "initialize.py"), str(ROOT / "examples" / "valid-task-brief.json"), str(output)]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            expected = {"task-assessment.md", "solution-options.md", "graph-spec.json", "execution-plan.md", "validation-plan.md", "run-report.md", "final-delivery.md"}
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            self.assertEqual(validate(load_json(output / "graph-spec.json")), [])
            second = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn("拒绝覆盖", second.stderr)

    def test_copied_skill_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied_skill = Path(directory) / "graph-engineering-agent-builder"
            shutil.copytree(SKILL, copied_skill)
            output = Path(directory) / "contract"
            initialized = subprocess.run(
                [sys.executable, str(copied_skill / "scripts" / "initialize.py"), str(ROOT / "examples" / "valid-task-brief.json"), str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            validated = subprocess.run(
                [sys.executable, str(copied_skill / "scripts" / "validate_graph.py"), str(output / "graph-spec.json")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            mock_output = Path(directory) / "mock-run"
            mock_result = subprocess.run(
                [sys.executable, str(copied_skill / "scripts" / "mock_executor.py"), str(ROOT / "examples" / "approved-graph.json"), str(mock_output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(mock_result.returncode, 0, mock_result.stderr)
            self.assertFalse(load_json(mock_output / "run-report.json")["domain_completion_claimed"])


class MockExecutorTests(unittest.TestCase):
    def run_executor(self, spec: dict[str, object], output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        spec_path = output.parent / "graph.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "mock_executor.py"), str(spec_path), str(output), *extra],
            capture_output=True,
            text=True,
            check=False,
        )

    def approved_spec(self) -> dict[str, object]:
        return load_json(ROOT / "examples" / "approved-graph.json")

    def test_approved_ready_graph_simulates_parallel_batches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = self.run_executor(self.approved_spec(), output)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = load_json(output / "run-report.json")
            self.assertEqual(report["run_status"], "simulated_success")
            self.assertFalse(report["domain_completion_claimed"])
            self.assertGreaterEqual(len(report["batches"][0]["nodes"]), 2)
            self.assertGreater(len(report["batches"]), 1)
            self.assertTrue((output / "run-report.md").is_file())

    def test_pending_approval_is_rejected(self) -> None:
        spec = self.approved_spec()
        spec["approval"] = {"status": "pending", "approved_by": None, "record": "等待"}
        spec["state"] = "awaiting_approval"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = self.run_executor(spec, output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("approval.status=approved", result.stderr)
            self.assertFalse(output.exists())

    def test_failure_injection_blocks_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = self.run_executor(self.approved_spec(), output, "--fail-node", "worker-a")
            self.assertEqual(result.returncode, 1)
            report = load_json(output / "run-report.json")
            self.assertEqual(report["run_status"], "failed")
            node_results = {item["node_id"]: item for item in report["node_results"]}
            self.assertEqual(node_results["worker-a"]["status"], "failed")
            self.assertEqual(node_results["independent-verifier"]["status"], "skipped")
            self.assertEqual(node_results["synthesis"]["status"], "skipped")

    def test_cycle_is_rejected_with_report(self) -> None:
        spec = self.approved_spec()
        spec["edges"].append({"from": "synthesis", "to": "worker-a", "relation": "revises", "artifact": "synthetic-draft"})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            result = self.run_executor(spec, output)
            self.assertEqual(result.returncode, 1)
            report = load_json(output / "run-report.json")
            self.assertIn("cycle", report["failure"])
            self.assertTrue(report["missing_nodes"])

    def test_existing_output_directory_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            output.mkdir()
            result = self.run_executor(self.approved_spec(), output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("拒绝覆盖", result.stderr)


if __name__ == "__main__":
    unittest.main()
