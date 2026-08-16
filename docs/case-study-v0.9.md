# Case study: Graph Writing v0.9 Choice-Gates

## Scope

This is a local, evidence-bound practice of the standalone Graph Writing v0.9 extension in the [Academic Research Loop Workflow](https://github.com/2023Anita/academic-research-loop-workflow). The original v0.8 runtime remains the read-only compatibility boundary.

The case is intentionally narrower than a production Agent system:

- the author selected `C / cautious`;
- the practice recorded S0-S9 local checkpoints and independent Reviewer reports;
- the local chain closed with `closed_local`;
- external execution, publication, upload, Git effects and sensitive-data egress stayed unauthorized;
- `closed_local` does not mean a final manuscript, production runtime, quality claim or cost claim.

## Graph responsibilities

| Responsibility | Case node | Evidence / artifact |
|---|---|---|
| Ground the work | Source anchors | Frozen source manifest and hashes |
| Explore evidence | Evidence scout A/B and counter-evidence | Evidence packets |
| Check provenance | Evidence audit | Audit record |
| Organize writing | Outline and section drafting A/B | Outline and draft sections |
| Check claims | Claim verification | Claim-to-source bindings |
| Synthesize | Synthesis | Evidence-bound draft |
| Independently review | Fresh Reviewer context | Reviewer report v2 |
| Own the decision | Choice Gate C / cautious | Author choice record |
| Stop or resume | Stop / handoff | Handoff record |

## Boundary with v0.8

The v0.8 G0-G3 and A/B/C/D rules are read-only constraints for this practice. They do not become a hidden execution permission. The Graph Writing package preserves the original v0.8 Skill and directory, and its local `.workflow` state is not part of the public package.

## Reproduce the contract checks

From the package directory:

```bash
python3 scripts/doctor.py --strict
python3 scripts/validate_practice.py examples/practice-graph-engineering-writing
make verify
```

These checks validate structure, source bindings, edge requirements, reviewer binding and the no-external-execution contract. They do not replace the author's scientific judgment or prove that an external publication occurred.

## Exact topology

The editable Graphviz source is [`graph-writing-v09.dot`](graph-writing-v09.dot). The rendered SVG is [`../assets/graph-writing-v09-exact.svg`](../assets/graph-writing-v09-exact.svg).
