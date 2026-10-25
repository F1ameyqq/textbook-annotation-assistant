# A30 launch03-r1 执行者身份最小差量（仅构建与只读预检）

## 决定与授权

2026-10-25 用户明确：原 Codex 执行/复核额度耗尽，接管调度；执行者替换接受；M1（Agent 新上下文作为正式新对话，思考强度 max）；1800-a 保持 PAUSED；可提交和推送；每个任务的审查可另开子对话。授权记录见 `docs/approvals/A30-coordinator-takeover-and-m1-20261025.json`。

## 已接受父包（不可修改）

- 目录：`D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261024-03`
- manifest：`3bc46a59a3fcc23b2ff7d9041f41feee076afcd8560c58c0586dea3639514faf`
- entry：`17897293f299aa39eb8321e68c59feabbd92acbb02302f9ad4c7bfb13d4262a7`
- template：`1f80eaf925925ad241a9fac2c6a1067daad35310066a80431c198aea981dc161`
- binding：`35f87bd50b1e08f0241557ac8a65517697995b56c1e605955ea41152e2905688`
- plan：`eabbb944c938304d96969a8fae02d5f194e28717d114225e4781f7d4dc1860c8`
- product：`19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a`（249 源文件，holder `90babd87d0ec8e7bcda00f4ff0d2aa3f148ac26b84884735c4301c2a12a74e57`）
- 接受结论：`ACCEPTED_OFFLINE_UNION20_ORDINARY_INTERRUPTED_RECONCILE_AND_LAUNCH03_CONTINUATION_SCOPE_ONLY`；REVIEW.md `519d0976bccbf1470a6c976562df3494a571a35e491457f507a8e805aa0360a2`；根收口 `docs/evidence/coordinator/a30-union20-reconcile-launch03-independent-closure/receipt.json`（`70d6bdb5ed98c7077416ed0be0ed921f883dcf1701c2bd95104b9f7271371261`）。
- 范围：16 题，11 复用，4 首次保存，1 次 Q12 只读对账；2,997 业务 GET、最多 4 POST、59 平台 context、1 本地展示 context、最多 11 个绑定题图裁剪；1,800 秒窗口 + 60 秒释放余量；Q12 不重发。

## 唯一差量

新唯一执行者 ID：`a30-exec-20261025-01`。父包的 `run_once.py` 第 6 行与 `authority-template.json` 的 `executor` 固定为旧 Codex ID；本差量只替换这两处身份以及模板内的 entry/binding 路径与 entry 哈希。其他所有 guard、范围、预算、产品、binding、plan 字节不变。

## 允许写入

- 新包目录 `D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261025-01`
- 构建脚本目录 `D:/1800-private/a30-launch-r1-builder-20261025-01`

## 禁止

- 不运行 actual、不绑定/激活 authority、不传 `--child`；不调用平台/网络/浏览器/Edge；不读取 profile 文件；不读取/填写凭据；不运行 OCR/模型/登录。
- 不写入 workspace、settings、profile、产品树；不修改父包；不运行父包的旧 build 脚本。
- 不删除新包/构建目录以外的任何文件；不执行 git/commit/push。
- 不重跑任何已接受测试矩阵；唯一执行是只读 preflight。

## 构建要求

1. 先核对父包 10 个文件的字节数与 SHA-256，全部匹配后再复制。
2. `run_once.py` 仅做字节级替换：`EXECUTOR = '<旧 ID>'` → `EXECUTOR = 'a30-exec-20261025-01'`（含 CRLF），断言旧行恰好一次，且 `new_bytes == old_bytes.replace(old_line, new_line)`。
3. `authority-template.json` 只改四个字段：`executor`、`entry_path`、`entry_sha256`、`binding_path`。`activated=false`、`authority_id=null`、`not_before/expires_at/output_directory=null`、`root_receipts=[]`、`binding_sha256`、`selected_keys`、`limits`、`expected_cost` 全部保持。
4. `binding.json`、`continuation-plan.json` 必须与父包逐字节一致。
5. JSON 写法沿用父包：`json.dumps(..., ensure_ascii=False, indent=2)`、CRLF、无末尾换行。
6. 只读 preflight 命令：
   `D:/1800/.local/stages/a30-customer-independent-20261024/runtime-support/venv-customer-py312/Scripts/python.exe -I -B run_once.py --preflight --binding binding.json --binding-sha256 35f87bd50b1e08f0241557ac8a65517697995b56c1e605955ea41152e2905688`
   输出必须为 `READONLY_BINDING_PREFLIGHT_PASS`，`selected=16/reused=11/pending=4/readonly_reconcile=1`，`platform_calls=0`，`candidate_edits=0`，`settings_writes=0`，`new_model_calls=0`，`activated=false`。失败即停止，不得为通过而改工作区/设置/profile/产品/binding/父包。
7. 交付 `report.json`、`receipt.json`、`evidence/delta-record.json`、新 preflight 日志/退出码、可复现的 `evidence/build_launch_r1.py`；`manifest.json` 覆盖除自身与 receipt 外的全部成员。

## 验收与后续

- 本差量必须先由独立复核上下文 `a30-review-launch-r1-20261025-01` 接受（见 `docs/tasks/A30-launch03-r1-independent-review-20261025.md`），根才可绑定新的唯一 authority。
- 本次不激活、不运行 actual；Q12 仍 `UNKNOWN_NO_RETRY`，Q13–16 仍 `NOT_RUN`，全16导出/展示仍 `NOT_RUN`。`CUSTOMER_READY=false`，1800-a 保持 PAUSED。
