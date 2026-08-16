PYTHON := python3
SKILL := skills/graph-engineering-agent-builder
SKILL_CREATOR_ROOT ?= $(HOME)/.codex/skills/.system/skill-creator

.PHONY: verify
verify:
	$(PYTHON) -m compileall -q scripts $(SKILL)/scripts tests
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) $(SKILL_CREATOR_ROOT)/scripts/quick_validate.py $(SKILL)
	$(PYTHON) scripts/validate_graph.py examples/valid-graph.json
	$(PYTHON) scripts/validate_graph.py examples/approved-graph.json
