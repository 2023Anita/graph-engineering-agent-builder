# Graph Spec 字段

`graph-spec.json` 必须包含：`schema_version`、`title`、`mode`、`state`、`root_goal`、`permissions`、`frozen_rules`、`approval`、`budget`、`anchors`、`nodes`、`edges`、`failure_policy`、`stop_handoff` 与 `execution_contract`。

`mode` 只能是 `direct`、`loop`、`linear_workflow`、`graph`、`graph_plus_loop`、`blocked`；`state` 只能是 `designed`、`awaiting_approval`、`ready`、`executing`、`blocked`、`failed`、`completed`、`budget_exhausted`。

每个节点必须有唯一 `id`、受支持的 `kind`、明确 `owner`、单一 `responsibility` 以及非空 `contract.inputs` 和 `contract.outputs`。受支持类型为 `execution`、`execution_loop`、`verification_loop`、`counter_metric_loop`、`audit_loop`、`arbitration`、`governance_loop`、`anchor`、`human_gate`、`stop_handoff`、`reducer`、`synthesis`。每条边必须有存在的 `from` / `to`、真实关系和明确 `artifact`。可用关系为 `feeds`、`observes`、`verifies`、`constrains`、`vetoes`、`escalates`、`arbitrates`、`revises`、`anchors`、`hands_off`。

Graph 模式须包含 `human_gate`、`stop_handoff`、`verification_loop`、`anchor` 节点和至少一个 `frozen: true` 锚点。锚点要用 `node_id` 关联该节点，并记录 `source`、`evidence_form`、`owner`、`freshness_rule`；还须有从锚点节点发出的 `anchors` 边。验证节点需 `context_scope: fresh-independent`。

`ready` 和 `executing` 要有 `approval.status: approved` 与人类 `approved_by`。`completed` 还要提供 `reality_evidence`，而非仅依赖 Agent 声明。

## Mock Executor 边界

本 Skill 附带的 `scripts/mock_executor.py` 仅接受 `approval.status: approved`、非空 `approved_by`、`state: ready` 且 `execution_contract.external_execution: false` 的 Spec。它按 `edges` 模拟本地拓扑调度，生成合成 artifact 与 `run-report.json`/`run-report.md`，不调用真实 Agent、网络或模型。任何成功都只能是 `simulated_success`，并且 `domain_completion_claimed` 固定为 `false`。

本地初始化器始终写入 `execution_contract.external_execution: false`。只有宿主 Codex 收到针对具体动作范围的明确授权后，才能将其改为 `true`；`executing` 状态还必须重新通过结构校验。批准 Graph 设计不自动批准删除、提交、推送、发布、上传、生产写入或权限扩大。
