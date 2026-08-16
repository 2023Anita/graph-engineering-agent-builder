"""兼容入口；核心规则位于内嵌的自包含 Skill。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "skills" / "graph-engineering-agent-builder" / "scripts" / "common.py"
SPEC = importlib.util.spec_from_file_location("graph_builder_skill_common", CORE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"无法载入核心规则：{CORE}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

MODES = MODULE.MODES
STATES = MODULE.STATES
NODE_KINDS = MODULE.NODE_KINDS
RELATIONS = MODULE.RELATIONS
load_json = MODULE.load_json
write_json = MODULE.write_json
classify = MODULE.classify
