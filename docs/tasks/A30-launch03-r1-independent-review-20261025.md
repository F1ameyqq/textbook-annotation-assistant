# A30 launch03-r1 独立复核（执行者身份差量）

## 角色与独立性

- 复核上下文：`a30-review-launch-r1-20261025-01`（新开 Agent 上下文，思考强度 max）。
- 不得是执行者 `a30-exec-20261025-01` 或同一上下文；不得共享执行者的工作目录写入。
- 独立性限制：同一模型家族、不同会话；原 Codex 复核额度耗尽。用户已批准 M1，此限制必须写入结论，不得声称是原正式复核或不同模型供应商。

## 输入

- 父包：`D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261024-03`（10 文件，manifest `3bc46a59…`，entry `17897293…`，template `1f80eaf9…`，binding `35f87bd5…`，plan `eabbb944…`，report `47c7921e…`，receipt `051b872c…`）。
- 子包：`D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261025-01`。
- 已接受的 union20/launch03 复核：`docs/evidence/A30/review/union20-reconcile-launch03-01/REVIEW.md`（`519d0976…`）；根收口 `docs/evidence/coordinator/a30-union20-reconcile-launch03-independent-closure/receipt.json`（`70d6bdb5…`）。
- 产品：`D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20/manifest.json`（`19a3497e…`，249 文件）。

## 必须核验

1. 父包 10 文件字节/SHA 全匹配；子包 manifest 自身与全部成员读取一致，无 `__pycache__`/`.pyc`/未声明文件。
2. `run_once.py` 与父包逐字节比较：唯一差异是第 6 行 `EXECUTOR` 旧 ID → `a30-exec-20261025-01`；其余所有字节、所有 guard（`check_binding`、`activated`、root receipts、窗口、输出目录、binding/plan/limits/cost 校验）不变。
3. `authority-template.json` 与父包解析比较：只允许 `executor`、`entry_path`、`entry_sha256`、`binding_path` 四个字段变化；`activated=false`、`authority_id/not_before/expires_at/output_directory=null`、`root_receipts=[]`、`binding_sha256`、`selected_keys`、`limits`、`expected_cost` 不变；`entry_sha256` 与实际新 entry 哈希一致。
4. `binding.json`、`continuation-plan.json` 与父包逐字节一致；产品 manifest `19a3497e…`、249 文件、holder `90babd87…` 不变。
5. 只读 preflight 确实以新 entry 运行且结果 PASS：`selected=16/reused=11/pending=4/readonly_reconcile=1`，`platform_calls=0`，`candidate_edits=0`，`settings_writes=0`，`new_model_calls=0`，`activated=false`；日志/退出码/哈希与记录一致。
6. `report.json`、`receipt.json`、`evidence/delta-record.json` 的路径/哈希/成员数/父包 lineage/差量描述准确；不得声称已激活、已接受、已运行 actual、客户可交付。
7. 没有实际平台/网络/浏览器/profile/工作区/产品/父包写入；没有 Q12 重发、11 题重存、old9/OCR/模型/登录/旧 authority 复用。
8. 结论枚举：`ACCEPTED_OFFLINE_EXECUTOR_IDENTITY_DELTA_ONLY` 或 `REWORK`。REWORK 必须给出具体文件/原因，不得软化。

## 输出

- 私有：`D:/1800-private/a30-launch-r1-review-20261025-01/`，含 `REVIEW.md`、`decision.json`、`manifest.json`、`raw/`。
- 公开：`D:/1800/docs/evidence/A30/review/launch-r1-01/REVIEW.md`，自包含，含父/子哈希、逐项差量、preflight 结果、限制和结论。
- `decision.json` 记录 `reviewer: "a30-review-launch-r1-20261025-01"`、独立性限制、`actual_platform_calls: 0`、`workspace_writes: 0`、`profile_reads: 0`、`actual_run: "NOT_RUN"`、`authority_bound: false`。

## 禁止

- 不运行 actual/`--child`、不绑定/激活 authority、不调用平台/网络/浏览器/Edge、不读 profile 文件/凭据、不写 workspace/settings/产品/父包/子包、不重跑已接受测试、不执行 git/commit/push。
- 不得以执行者的报告或 preflight 日志替代独立核验；必须自己读字节、算哈希、核字段。
