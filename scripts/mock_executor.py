#!/usr/bin/env python3
"""调用项目内嵌自包含 Skill 的 Mock Executor。"""

from pathlib import Path
import runpy
import sys

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "graph-engineering-agent-builder" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
runpy.run_path(str(SKILL_SCRIPTS / "mock_executor.py"), run_name="__main__")
