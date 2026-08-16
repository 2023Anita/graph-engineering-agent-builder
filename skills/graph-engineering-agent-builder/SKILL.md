---
name: graph-engineering-agent-builder
description: 将用户任务转化为可审查、可授权执行的 Graph Engineering 系统。用于判断任务应采用 direct、loop、线性工作流、graph 或 graph-plus-loop；评估候选方案；定义节点契约、真实边、现实锚点、预算、失败策略与交接；并在人类明确批准后按图调度可用 Agent 或工具。不要用它绕过人工审批、扩大权限或宣称未验证的完成。
---

# Graph Engineering Agent Builder

将根目标、现实锚点、权限和冻结规则视为 human-owned；任务不清或这些项缺失时输出 `blocked`，不要推测补全。节点表示职责，不默认等于一个 Agent。

## 四阶段工作流

### 1. 任务判断

先明确任务、根目标、范围、权限、验收、风险和预算。调用 `$graph-engineering-architect` 的分类原则，在 `direct`、`loop`、`linear_workflow`、`graph`、`graph_plus_loop`、`blocked` 中选择最小可行模式。找不到两个真正独立的职责时不要创建 Graph。

### 2. 方案评估

比较最小方案与 Graph 方案的价值、成本和风险。逐边执行假边测试；将共享文件、工作区、速率限制与其他共享资源视为隐藏依赖。使用 `$cost-aware-task` 选择最便宜的合适角色和最少 Agent 数；需要写入时只允许一个写入者。

### 3. 详细规划

使用 `scripts/initialize.py <task-brief.json> <新输出目录>` 生成七份契约文件，输出目录必须不存在。为每个节点写明 owner、输入、输出和验收；为每条边写明真实关系和产物。对 `graph` 和 `graph_plus_loop`，要求 fresh-independent 验证者、执行回路不能改写的 frozen reality anchor、人类 gate、预算与 stop/handoff。节点内部需要持久迭代时使用 `$loop-engineering-co-builder`。运行 `scripts/validate_graph.py <graph-spec.json>`，并向用户展示方案、权限、预算和剩余风险。

### 4. 授权执行

未获得明确批准时保持 `awaiting_approval`，不得执行领域任务。批准后记录 `approved_by` 和批准证据；仅在用户授权的动作范围内将 `execution_contract.external_execution` 设为 `true`，重新验证后再进入 `ready` 或 `executing`。按真实依赖顺序调度节点；无依赖节点才并行。验证者使用独立上下文和独立证据来源，汇合时核对预期输入数量。将节点结果、失败、重试、成本和证据写入 `run-report.md`，将可恢复状态写入交接文件。

高风险、删除、提交、推送、发布、上传、生产写入或权限扩大必须在动作前单独确认。脚本只生成和验证本地契约，不替代宿主 Codex 的权限检查，也不直接执行领域任务。

### 本地调度测试

`scripts/mock_executor.py <graph-spec.json> <新运行目录> [--fail-node NODE_ID]` 是确定性 Mock Executor，仅用于检验已批准 `ready` Graph 的拓扑批次、失败传播和运行报告。它要求 `execution_contract.external_execution=false`，不创建真实 Agent、不联网、不调用模型或执行领域任务。模拟报告只能标记 `simulated_success`，并固定写入 `domain_completion_claimed: false`；不要据此声明现实任务完成。

## 完成规则

不得因节点全部返回或 Agent 相互同意而标记 `completed`。只有现实锚点新鲜、独立验证通过、冲突已解决、冻结规则未变且最终交接可用时才能完成；否则如实报告 `blocked`、`failed` 或 `budget_exhausted`。

详细字段和失败检查见 [references/graph-spec.md](references/graph-spec.md)。
