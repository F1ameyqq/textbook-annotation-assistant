# A30 launch03-r1 执行者身份差量 独立复核

- 复核上下文：`a30-review-launch-r1-20261025-01`（独立 Agent 上下文，非执行者 `a30-exec-20261025-01`，不与执行者共享工作目录）。
- 结论：**ACCEPTED_OFFLINE_EXECUTOR_IDENTITY_DELTA_ONLY**
- 本结论只接受：子包相对已正式接受的父包（union20/launch03，复核 `docs/evidence/A30/review/union20-reconcile-launch03-01/REVIEW.md` `519d0976…`，根收口 receipt `70d6bdb5…`）仅发生执行者身份差量，且所有不变式、guard、只读 preflight 由复核者独立重算/重跑验证。不代表：已激活、已运行 actual、已平台调用、子包已获正式接受或客户可交付（`CUSTOMER_READY=false`、1800-a PAUSED 保持）。

## 独立性限制

同一模型家族、不同会话；不是原 Codex 正式复核；原 Codex 复核额度耗尽，本复核为用户批准 M1 的替代独立复核。不得声称是原正式复核或不同模型供应商复核。

## 输入与哈希（全部为复核者自行计算）

父包 `D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261024-03`（10 文件）：

| 路径 | bytes | sha256 |
|---|---|---|
| authority-template.json | 3313 | `1f80eaf925925ad241a9fac2c6a1067daad35310066a80431c198aea981dc161` |
| binding.json | 3425 | `35f87bd50b1e08f0241557ac8a65517697995b56c1e605955ea41152e2905688` |
| continuation-plan.json | 99586 | `eabbb944c938304d96969a8fae02d5f194e28717d114225e4781f7d4dc1860c8` |
| evidence/build_full16_reconcile_continue03.py | 16220 | `ea77f826ed71912144ecf9cc9dfb080c0393f7e2f159ff71781d412439c9be5b` |
| evidence/full16-reconcile-launch03-preflight-01.exit.txt | 1 | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` |
| evidence/full16-reconcile-launch03-preflight-01.log | 378 | `a90aa8bd378fac393861cef3a8875c66fa39e9613fc59c979db0b70426bfe3d1` |
| manifest.json | 1434 | `3bc46a59a3fcc23b2ff7d9041f41feee076afcd8560c58c0586dea3639514faf` |
| receipt.json | 643 | `051b872cb2d91a7432d2070ca25fbbcee52cc9e02fe66aa32dba5f80bd294732` |
| report.json | 2839 | `47c7921eeebcd4442e4a98e565d1ac9bc74ffa128f0a7e8e355882b50605eed7` |
| run_once.py | 15431 | `17897293f299aa39eb8321e68c59feabbd92acbb02302f9ad4c7bfb13d4262a7` |

与任务书声明的父哈希逐一相符。

子包 `D:/1800-private/a30-full16-reconcile-continue-launch-fixed-20261025-01`（14 文件，12 manifest 成员）：

| 路径 | bytes | sha256 | 相对父包 |
|---|---|---|---|
| authority-template.json | 3297 | `45bb0275c77e410a65ceacb689b7259a2e6a41ec86c0234263fcfa8208fde76f` | changed |
| binding.json | 3425 | `35f87bd50b1e08f0241557ac8a65517697995b56c1e605955ea41152e2905688` | identical |
| continuation-plan.json | 99586 | `eabbb944c938304d96969a8fae02d5f194e28717d114225e4781f7d4dc1860c8` | identical |
| evidence/build_full16_reconcile_continue03.py | 16220 | `ea77f826ed71912144ecf9cc9dfb080c0393f7e2f159ff71781d412439c9be5b` | identical |
| evidence/build_launch_r1.py | 24569 | `12ee0d77979ba02d9535007ddea2cc712762d6a85a10c55dc70bb185c1296006` | added |
| evidence/delta-record.json | 9318 | `15cc3edaeb0f6a63719291a19ac61b30d7895a5ed884bb7ab56a83ffee488eab` | added |
| evidence/full16-reconcile-launch-r1-preflight-01.exit.txt | 1 | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` | added |
| evidence/full16-reconcile-launch-r1-preflight-01.log | 378 | `a90aa8bd378fac393861cef3a8875c66fa39e9613fc59c979db0b70426bfe3d1` | added |
| evidence/full16-reconcile-launch03-preflight-01.exit.txt | 1 | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` | identical |
| evidence/full16-reconcile-launch03-preflight-01.log | 378 | `a90aa8bd378fac393861cef3a8875c66fa39e9613fc59c979db0b70426bfe3d1` | identical |
| manifest.json | 2153 | `55a6af3120f50288a3c28a002495a06a4467cba728931e07ddf79b063ce855df` | changed（非成员，父约定） |
| receipt.json | 1672 | `7f557605b1a525e6bca062fdc70cf7a453cd3db2dab2bfa4e81ebf97ed2239c5` | changed（非成员，父约定） |
| report.json | 4297 | `4298b516b34b567ef68aaae1b460596d30a558c7f8add5b1f9e0d283436218b6` | changed |
| run_once.py | 15415 | `fbfa867331c141f70f4d1e10a9393b78dd67aaabcb4fc61310d2a5d03ef7606a` | changed |

与执行者声明（manifest 55a6af31…/2153B、entry fbfa8673…/15415B、template 45bb0275…/3297B、report 4298b516…/4297B、receipt 7f557605…/1672B、12 成员）逐一相符。12 个 manifest 成员 bytes/sha256 与磁盘读取全部一致；无 `__pycache__`/`.pyc`；除 manifest 自身与 receipt.json 外无未声明文件（不进成员列表是父包已接受约定，delta-record `top_level_records` 已注明；父包同构：10 文件 = 8 成员 + manifest + receipt）。

## 逐项差量

1. **run_once.py**：`diff` 唯一差异为第 6 行 `EXECUTOR = '01a16bf6-ed2d-7950-b2c9-9df30e7e6bd6'` → `EXECUTOR = 'a30-exec-20261025-01'`，其余所有字节一致。guard 均在与父字节一致：`check_binding`（binding 哈希/模式、产品 249 源文件哈希、workspace/head 绑定、plan 绑定、EXACT_SCOPE_REQUIRED、冻结 actual02 10748 成员、state.sqlite ro 校验 85 operations、settings 哈希与平台/公式开关、保留 python 哈希、profile 指纹、blob 只读、16 候选内容与 acceptance、Q12 原 receipt/node 只读恢复校验）、`activated`（authority 哈希/模式/activated=true/executor==EXECUTOR、窗口 ≤1800s 且含时区、entry 哈希==自身、root_receipts≥4 且哈希校验、输出目录与 app/workspace/profile 隔离）、preflight 分支只读不写。
2. **authority-template.json**：解析比较唯一变化的 4 字段为 `executor`、`entry_path`、`entry_sha256`、`binding_path`。不变式全部成立：`activated=false`、`authority_id/not_before/expires_at/output_directory=null`、`root_receipts=[]`、`binding_sha256=35f87bd5…`、`selected_keys`（16 键）、`limits`、`expected_cost`、`book_id/job_id` 均不变；新 `entry_sha256` 等于新 entry 实测哈希 `fbfa8673…`；原始 20b authority 保持 spent1/remaining0，`new_authority_does_not_restore_old_round=true`。
3. **binding.json / continuation-plan.json / 产品**：两文件与父包逐字节一致。产品 manifest `19a3497e…` 实测不变，249 source_files 全部哈希匹配，无未声明 src/tools .py，holder `tools/owned_process.py` 实测 `90babd87d0ec8e7bcda00f4ff0d2aa3f148ac26b84884735c4301c2a12a74e57`。plan 结构化字段：workspace、job_id `55f20a7e…`、expected_head `7077df60…`、product_manifest_sha256 `19a3497e…`、selected16/reused11/pending4/readonly_reconcile1、book46007447，selection 印刷号 1–16。
4. **只读 preflight 独立重跑**：复核者以新 entry 执行与记录一致的命令（venv python `-I -B run_once.py --preflight --binding binding.json --binding-sha256 35f87bd5…`，cwd 子包，`PYTHONDONTWRITEBYTECODE=1`），exit 0，stderr 0 字节，stdout 378 字节、sha256 `a90aa8bd…`，与子包记录 r1 preflight log 逐字节一致；值 `selected=16, reused=11, pending=4, readonly_reconcile=1, platform_calls=0, candidate_edits=0, settings_writes=0, new_model_calls=0, activated=false` 全部复现。r1 log 与父 launch03 log 哈希相同是 preflight 输出确定且不含 entry 身份所致；复核者重跑逐字节一致，证实其为真实运行产物而非复制件。preflight 内部按已接受 check_binding 设计计算 profile 指纹并只读打开 workspace/state.sqlite/产品源文件，无 profile 内容进入复核者上下文。
5. **写自由**：复核者 preflight 前后快照一致——workspace 成员 10748→10748，`settings.json` `56f07eb9…` 不变，子包 14 文件、父包 10 文件不变，app src/tools `__pycache__` 0→0。零写入。无 Q12 重发（plan 不变 `read_only_reconcile=1`、`original_q12_resaves=0`）、无 11 题重存（`accepted_eleven_resaves=0`）、old9/OCR/公式模型/付费模型/登录/重试/上传全 0；旧 authority 未复用（模板 inactive、新 ID 未绑定）。
6. **report/receipt/delta-record 准确性**：report `delta` 的 parent 路径与 4 个父哈希、changed/identical/added 分类、`only_executor_identity_changed` 与实测一致；`preflight_exit_code=0`、`preflight_log_sha256=a90aa8bd…` 与实测一致。receipt 的 manifest/report/entry/binding/batch_plan/template 哈希、members 12 / parent members 8、旧新执行者与模板 4 字段与实测一致。delta-record 的 parent_file_table（10 项）、new_file_table（12 项 + 自引用说明）、run_once_patch（CRLF、唯一行、其他字节一致证明）、authority_template_patch、product_manifest（249/holder/unchanged）、preflight 记录（命令/exit/status/值/log+exit 哈希/stdout 原文）与复核者计算一致；`actual_run=NOT_RUN`、`authority_bound=false`、`activation=false`。无“已激活/已接受/已运行 actual/客户可交付”声称（report `activated=false, customer_ready=false, new_platform_calls=0`；全包扫描的 ACCEPTED 字样均为父包已有 guard 字符串、既有接受复用标记或对父包已接受状态的引用）。

## preflight 复跑结果

- exit code 0；stdout sha256 `a90aa8bd378fac393861cef3a8875c66fa39e9613fc59c979db0b70426bfe3d1`（= 记录 log）；stderr 0 字节。
- `READONLY_BINDING_PREFLIGHT_PASS`，selected 16 / reused 11 / pending 4 / readonly_reconcile 1 / platform_calls 0 / candidate_edits 0 / settings_writes 0 / new_model_calls 0 / activated false。

## 未做事项

未运行 actual/`--child`；未绑定/激活 authority；无平台/网络/浏览器/Edge 调用；未直接读 profile 文件/凭据；未写 workspace/settings/产品/父包/子包；未重跑已接受测试；无 git/commit/push。本复核只写自己的私有输出目录与本公开 REVIEW.md。

## 结论

**ACCEPTED_OFFLINE_EXECUTOR_IDENTITY_DELTA_ONLY**。子包是父包的纯执行者身份差量：唯一代码差量为 `run_once.py` 第 6 行 EXECUTOR，唯一模板差量为 4 个身份字段；binding/plan/产品/limits/cost/guard 全部不变；新 entry 只读 preflight 经复核者独立重跑 PASS 且与记录逐字节一致；全程零写入、零平台调用、未激活。此接受不构成实际平台执行授权，也不表示子包已获正式接受（独立性限制见上）。
