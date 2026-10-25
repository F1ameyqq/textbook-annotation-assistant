# A30 v1.1.4 客户包独立离线复核

## 角色与独立性

- 复核上下文：`a30-review-v114-20261025-01`（新开 Agent 上下文，思考强度 max）。
- 不得是包构建者或 A30 执行者，不得修改发布目录/zip。
- 独立性限制：同一模型家族、不同会话；原 Codex 复核额度耗尽。用户已批准 M1；该限制必须写入结论，不得声称是原正式复核或不同模型供应商。

## 输入（均须自行核验，intake 只是待核声明）

- zip：`D:/1800/.local/releases/A30-v1.1.4-customer-local-win64.zip`，2,724,491 字节，SHA-256 `7344205c2698be60bc11c7bddddb8e9c92d137c4ccc653997ecbf378526972cc`。
- 发布目录：`D:/1800/.local/releases/A30-v1.1.4-customer-local-win64`。
- intake：`D:/1800-private/a30-release-v114-independent-20261024-01/intake.json`（`ef9a70120e64a6a2787252c43656451a725936300a9ca26f0f781d640c238dac`），声明 `PASS`、`source_exact=249`、`package_and_zip_exact=261`；声明相对 v1.1.3 变更 12 文件、新增 3 文件、删除 0。
- 产品源 manifest：`D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20/manifest.json`（`19a3497e…`，249 文件）。
- union20 复核：`docs/evidence/A30/review/union20-reconcile-launch03-01/REVIEW.md`（`519d0976…`）。
- v1.1.3 已接受包：`D:/1800/.local/releases/A30-v1.1.3-customer-local-win64`（zip `b8044d97…`，2,711,918 字节，246 源/258 包）；复核 `docs/evidence/A30/review/release-v113-01/`；根收口 `docs/evidence/coordinator/a30-release-v113-independent-closure/`（`1d339058…`）。
- `START_HERE.txt`、`CANDIDATE-STATUS.json`、`release-manifest.json`、`source-manifest.json`、`package-record.json`、`final-handoff-values.json`。

## 当前业务事实（复核声明一致性用）

11/16 已 formal/root 接受（1/5/10/11 复用；2/3/4/6/7/8/9 新保存+新鲜独立读回）；Q12 一次 POST/HTTP200 receipt 但完整新鲜读回不完整，`UNKNOWN_NO_RETRY`，不得重发；13–16 `NOT_RUN`；全16原生导出/展示 `NOT_RUN`；旧 20b spent1/remaining0、release false 保留；`CUSTOMER_READY=false`，1800-a PAUSED。

## 必须核验

1. zip 完整性、条目数、路径安全（绝对路径/`..`/盘符/符号链接/重复/大小写冲突）、解压后逐文件与发布目录一致；解压到新的空私有目录，不在解压树内以其为 cwd 运行解释器。
2. 源/包身份：产品 manifest `19a3497e…` 的 249 文件逐一哈希一致；无未声明 `.py`；holder `90babd87…`；261 包/zip 计数口径核实；v1.1.4 相对 v1.1.3 的实际增删改与 intake 声明一致，且变更集对应已接受 union20 差量（production.py、retained_readback.py、delivery_display.py、holder 相关、interrupted_save.py 及测试）加打包元数据；任何未解释变更须报告。
3. 泄漏/安全：不得含凭据、token、cookie、`.local` profile 内容、私有 raw、full16 authority JSON、workspace state blob/db、原始视频、未声明二进制。预期的本机绝对路径（workspace/Python/Edge/profile 引用）与秘密泄漏须区分；发现秘密只报告文件/类别，不打印值。
4. 运行入口与默认安全：检查 `START_CUSTOMER.cmd`、客户入口、`--customer-deployment` 内存合并、settings、公式识别接线；确认不自动登录、不填密码、不默认忽略证书、不写全局设置、不自动平台写入、不在无用户动作时调用模型/OCR、不能自行激活 full16 authority；仅解压或启动 UI 不得作用于真实工作区/平台；默认离线/已准备状态。
5. 声明一致性：`START_HERE.txt` 和所有状态/发布记录必须准确反映 11/16、Q12 未知禁重发、13–16 未运行、全16导出/展示待完成、`CUSTOMER_READY=false`、旧 20b 1/0 与 release false 保留、v1.1.4 仅是待复核候选且 actual 未运行。任何“完成/16/16/可直接交付/最终”过度声明须指出。
6. 仅有限离线检查：在新副本用 `-I -B`/`PYTHONDONTWRITEBYTECODE=1` 导入入口、跑 `--help`/dry-run（如有）、只跑不依赖真实工作区/平台/profile/模型/网络的包内离线单测。不得运行 `START_CUSTOMER.cmd`、不得启动 Edge/专用 profile、不得调用平台/OCR/模型/登录、不得写真实 workspace/settings、不得重跑已接受 union20/old9/first4 矩阵。
7. 输出：私有 `D:/1800-private/a30-release-v114-review-20261025-01/`（`REVIEW.md`、`decision.json`、`manifest.json`、`raw/`）；公开 `docs/evidence/A30/review/release-v114-01/REVIEW.md`。结论枚举 `ACCEPTED_OFFLINE_CUSTOMER_PACKAGE_V114_CANDIDATE` 或 `REWORK`。接受仅是包级离线候选，不使 `CUSTOMER_READY=true`，不授权 actual，也不替代后续 actual 结果复核。
8. `decision.json` 须含 `reviewer: "a30-review-v114-20261025-01"`、独立性限制、`actual_platform_calls: 0`、`workspace_writes: 0`、`profile_reads: 0`、`actual_run: "NOT_RUN"`。

## 禁止

- 不修改发布目录/zip/产品树/工作区/设置/profile/已接受证据；不执行 git/commit/push；不删除私有复核目录和公开 REVIEW.md 以外的任何文件。
