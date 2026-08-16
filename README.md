# Graph Engineering Agent Builder

Graph Engineering Agent Builder 是一个“推理型总控 Skill + 确定性本地工具”项目：先判断任务是否值得建 Graph，再评估方案、生成可审查的 Graph Spec，最后在明确授权后准备执行。它把节点、边、现实锚点、独立验证、成本预算、人工门禁和 stop/handoff 固化为可验证契约。

它不是一个默认替用户执行任务的 Agent 集群，也不会因为 Mock Executor 成功就宣称现实任务完成。

## 项目总览

![Graph Engineering Agent Builder architecture](assets/graph-engineering-agent-builder-architecture.png)

上图按 `graph-engineering-architect` 的设计原则组织：执行回路产生候选，独立验证者使用 fresh-independent 上下文检查，现实锚点提供不能被执行回路改写的证据，audit / counter-signal 与 arbitration 负责发现漂移和冲突，Human Gate 持有目标、权限和冻结规则的最终权力。

精确的可编辑拓扑源文件见 [`docs/architecture.dot`](docs/architecture.dot)，渲染版本见 [`assets/architecture-exact.svg`](assets/architecture-exact.svg)。

## 四阶段工作流

| 阶段 | Builder 负责什么 | 典型产物 |
|---|---|---|
| 1. 任务判断 | 将请求分类为 `direct`、`loop`、`linear_workflow`、`graph`、`graph_plus_loop` 或 `blocked` | Task Brief |
| 2. 方案评估 | 比较最小方案与 Graph 方案，检查独立性、假边、成本、风险和权限 | Proposal / risk notes |
| 3. 详细规划 | 写入根目标、节点契约、真实边、现实锚点、预算、失败策略和交接 | Graph Spec |
| 4. 授权执行 | 只有人类明确批准后才进入 `ready` / `executing`；持续记录证据、失败、成本和交接 | Approval record / run report / handoff |

节点表示职责，不默认等于一个 Agent。每条边都必须说明关系和传递的 artifact；“协作”“沟通”这类模糊边不够作为控制契约。

## 已实际运行的案例：Graph Writing v0.9

本项目已用于设计和审查独立的 [Academic Research Graph Writing v0.9 Choice-Gates 工作流](https://github.com/2023Anita/academic-research-loop-workflow/tree/main/academic-research-graph-writing-v0.9-choice-gates)，并随 [v0.9.0 GitHub Release](https://github.com/2023Anita/academic-research-loop-workflow/releases/tag/v0.9.0-graph-writing-choice-gates) 发布。原仓库的 v0.8 运行时没有被覆盖；v0.9 是新增的写作工程扩展。

![Graph Writing v0.9 Choice-Gates practice](assets/graph-writing-v0.9-choice-gates-practice.png)

这次实践中的 Graph 路径是：

```text
source anchors
  -> evidence scout A / evidence scout B / counter-evidence
  -> evidence audit
  -> outline
  -> section drafting A/B
  -> claim verification
  -> synthesis
  -> independent Reviewer
  -> author Choice Gate C (cautious)
  -> stop / handoff
```

实际记录包括：

- S0–S9 本地 checkpoint、来源清单、Graph Spec、handoff 和 Reviewer reports；
- `C / cautious` 作者选择，以及 `closed_local` 的本地收束状态；
- v0.8 的 G0–G3 与 A/B/C/D 门禁作为只读约束；
- 原 v0.8 Skill、目录和安全边界保持不变；
- 实践只证明本地证据链收束，不声称生产 Agent、最终论文、质量/成本实验或外部发布完成。

详细案例说明见 [`docs/case-study-v0.9.md`](docs/case-study-v0.9.md)，精确拓扑源文件见 [`docs/graph-writing-v09.dot`](docs/graph-writing-v09.dot)。

## 快速开始

```bash
python3 scripts/initialize.py examples/valid-task-brief.json /tmp/graph-builder-demo
python3 scripts/validate_graph.py /tmp/graph-builder-demo/graph-spec.json
make verify
```

初始化器拒绝已存在的输出目录，避免覆盖成果。可以复制并修改 `examples/valid-task-brief.json` 作为任务简报。

## 全局安装这个 Skill

项目内置的自包含 Skill 位于 `skills/graph-engineering-agent-builder/`。从仓库根目录安装到当前 Codex 的全局 Skills 目录：

```bash
SKILL_HOME="${CODEX_HOME:-$HOME}/.codex/skills/graph-engineering-agent-builder"
mkdir -p "$(dirname "$SKILL_HOME")"
cp -R skills/graph-engineering-agent-builder "$SKILL_HOME"
python3 "${CODEX_HOME:-$HOME}/.codex/skills/.system/skill-creator/scripts/quick_validate.py" "$SKILL_HOME"
```

安装只复制 Skill 说明、引用和确定性脚本，不复制项目数据、对话、凭证或 `.workflow` 状态。更新版本时应重新审查后再复制，避免无意覆盖本地改动。

## Mock Executor 的边界

```bash
python3 scripts/mock_executor.py examples/approved-graph.json /tmp/graph-builder-run
```

Mock Executor 只验证已批准 Graph 的拓扑批次、失败传播和运行报告：不创建真实 Agent、不调用模型或网络，也不执行领域任务。报告的成功状态只能是 `simulated_success`，并固定写入 `domain_completion_claimed: false`。

## 与其他组件的分工

- [`graph-engineering-architect`](https://github.com/2023Anita/graph-engineering-architect)：判断 Graph 是否合理，设计拓扑、现实锚点、治理和跨回路约束。
- `loop-engineering-co-builder`：负责单个持久迭代节点内部的状态、恢复、预算和停止逻辑。
- Graph Engineering Agent Builder：把任务判断、方案评估、Graph Spec 生成、确定性校验和执行准备物串成一条可审查路径。
- [`academic-research-loop-workflow`](https://github.com/2023Anita/academic-research-loop-workflow)：提供 v0.8 Choice-Gates 运行时；本项目只读使用其边界，不替换它。

## 安全边界

- 根目标、现实锚点、权限和冻结规则必须由人类拥有。
- Graph 模式必须有独立验证者、独立且冻结的现实锚点、人类门禁和可用的 stop/handoff。
- 删除、提交、推送、发布、上传、生产写入、敏感数据出站和权限扩大必须单独确认。
- `execution_contract.external_execution` 默认关闭；批准 Graph 设计不等于批准外部动作。
- 结构验证只能证明契约完整，不能证明锚点真实独立或现实任务已经完成。

## 图示制作说明

图示先依据 `graph-engineering-architect` 的节点/边/锚点/治理约束建模，再按 `scientific-infographic` 的学术信息图规范生成视觉稿；同时保留 Graphviz `.dot` 源文件，便于审查和重新渲染。图片是解释性工程文档，不替代运行契约或安全规程。

图示来源与制作边界记录在 [`docs/visual-provenance.md`](docs/visual-provenance.md)。
