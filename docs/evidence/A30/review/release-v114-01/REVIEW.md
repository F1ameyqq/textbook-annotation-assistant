# A30 v1.1.4 客户本机包 独立离线评审报告（公开）

- 评审者: `a30-review-v114-20261025-01`
- 独立性限制（如实记录）: 会话级独立、同模型家族、全新会话；原 Codex 评审者额度不可用，M1 用户批准。本评审者不是先前任何正式评审者。
- 时间: 2026-10-25（约 10 分钟，UTC+8）
- 真实平台调用: 0；真实工作区写入: 0；profile 读取: 0
- 结论: **ACCEPTED_OFFLINE_CUSTOMER_PACKAGE_V114_CANDIDATE**

## 一、评审对象与输入

| 输入 | SHA256 |
|---|---|
| ZIP `D:/1800/.local/releases/A30-v1.1.4-customer-local-win64.zip`（2,724,491 字节） | `7344205c2698be60bc11c7bddddb8e9c92d137c4ccc653997ecbf378526972cc` |
| 发布目录 `.../A30-v1.1.4-customer-local-win64`（261 文件） | — |
| 产品 manifest `D:/1800-private/a30-integrated-flow-r1-fixed-20261024-20/manifest.json`（249 声明文件） | `19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a` |
| 差量基线 `.../A30-v1.1.3-customer-local-win64`（258 文件） | — |

构建方声明与以上 ZIP 哈希、manifest 哈希、holder 哈希均一致。

## 二、T1 ZIP 完整性 — 通过

- 261 个条目，单一根目录 `A30-v1.1.4-customer-local-win64`。
- 路径安全 0 违规：无绝对路径、盘符、`..`、反斜杠分隔、冒号、符号链接、大小写冲突、重复条目。
- 解压到全新私有空目录后 261 个文件与发布目录 261 个文件逐字节哈希一致（无仅 zip / 仅发布目录 / 哈希不一致）。

## 三、T2 来源与包身份 — 通过

- 包内 `source-manifest.json` 与产品 manifest 逐字节相同。
- 249 个声明文件全部存在且哈希/字节一致；`src/`、`tools/`、`tests/` 下无未声明 `.py`。
- holder `app/tools/owned_process.py` SHA256 `90babd87d0ec8e7bcda00f4ff0d2aa3f148ac26b84884735c4301c2a12a74e57` 与声明一致。
- 261 = 249（app 树，与 manifest 集合完全相等）+ 12 个根打包元数据文件（状态/说明/启动脚本/锁/各类记录 JSON）。
- `release-manifest.json`（schema `A30CurrentMachineReleaseFiles/v1`，scope `LOCAL_BOOK46007447_CURRENT_MACHINE_CANDIDATE_ONLY`）：260 个成员与实际 260 个文件（排除自身）完全覆盖，全部哈希匹配。
- v1.1.3 → v1.1.4 差量（未重跑 union20 矩阵）：
  - 新增 3: `app/src/annotation/customer/interrupted_save.py`、`app/tests/test_a30_holder_metadata_exit.py`、`app/tests/test_a30_interrupted_save.py`
  - 变更 12: 源码 5（`delivery_display.py`、`production.py`、`retained_readback.py`、`tools/owned_process.py`、`tools/run_usense_owned.py`）+ 打包记录 7（`CANDIDATE-STATUS.json`、`START_HERE.txt`、`final-handoff-values.json`、`package-record.json`、`release-manifest.json`、`runtime-reference.json`、`source-manifest.json`）
  - 删除 0；不变 246。与"union20 差量 + 打包元数据"描述一致。

## 四、T3 泄漏/安全扫描 — 通过（未打印任何秘密值，仅报文件/类别）

260 个文本文件扫描，48 个命中全部为良性类别：

- `uuid_hex_64` ×38: 固定 sha256 哈希常量/引脚，非凭据。
- `workspace_path_ref` ×5: `START_CUSTOMER.cmd`、`START_HERE.txt`、`final-handoff-values.json`、`runtime-reference.json`、`customer-python.path` 中的本机绝对路径引用——本机包的预期内容，非机密。
- `dot_local_path_ref` ×3: 运行时 JSON 中的 `.local` 路径引用。
- `edge_profile_ref` ×2: `continuation_apply.py` 文档字符串中的 "local state" 短语；`usense_live/core.py` 中**拒绝** "default"/"user data"/"guest profile" 等专用 profile 目录名的校验逻辑（安全正向，非捆绑 profile 数据）。

0 命中：凭据/密码、token/secret、私钥、cookie、basic-auth、完整权威 UUID。唯一二进制为已声明的嵌套 zip `app/runtime/customer-recognition/46007447/viewer15-question-draft-v4.zip`（6 条目，无危险路径）。无未声明二进制。

## 五、T4 运行入口与默认安全 — 通过（源码审读）

- `START_CUSTOMER.cmd`: 硬编码本机 venv python 与工作区路径，任一缺失即 exit 2 拒绝启动；仅运行 `customer.py --workspace ... --customer-deployment`。
- `customer.py`: 部署模式下 CLI 命令一律 Hold，仅 GUI 向导；所有业务动作（prepare/produce/reconcile/display/login/公式识别）均为显式用户点击；设置合并仅在内存，不写原 settings.json（显式首次设置除外）；TLS 仅可选精确证书绑定，"不关闭通用证书校验"。
- `production.py`: 存在未对账保存时 Hold（Q12 门："先对账；不重发后继"）；复用已接受保存；失败 → `UNKNOWN_NO_RETRY` 不重发；`reconcile()` 只读、每记录一次。
- `transport.py`: 导入无动作；平台未启用则 Hold；子进程经冻结 sha 校验的 holder；login 为人工可见浏览器操作（`credential_values_filled: False`、`login_clicked_by_program: False`）。
- 公式推理仅经 review UI 显式按钮触发；模型文件未捆绑（本机引用）；历史记录自陈 `contains_errors_or_incomplete: true`。
- 结论: 无自动登录、无密码填充、无默认忽略证书、无全局设置写入、无自动平台写入、无用户未操作时的模型/OCR、无 full16 权威自激活；仅解包或启动 UI 不能作用于真实 workspace/平台；默认离线/待命。

## 六、T5 声明一致性 — 通过（两处冻结时点痕迹，非夸大）

- `START_HERE.txt` 事实全部准确: 11/16 已接受、Q12 UNKNOWN 且禁止重发、13–16 未运行、完整16题导出待完成、`CUSTOMER_READY=false`、原 20b 已耗 1/0 释放 false 历史保留、v1.1.4 为待审候选、"不代表整章或整书完成"、客户耗时与人工介入未测。
- `CANDIDATE-STATUS.json` 字段准确。
- 两处冻结于构建时（2026-10-24T13:51Z）的时点痕迹: `package-record.json` 中 `"zip": "NOT_CREATED"`；`START_HERE.txt`/`CANDIDATE-STATUS.json` 中 union20 标"审查待定"——现已由 `docs/evidence/A30/review/union20-reconcile-launch03-01/REVIEW.md` 正式接受，属时点滞后而非错误。
- 未发现 "complete"/"16/16"/"customer ready"/"final" 类夸大。

## 七、T6 有限离线检查 — 全部通过

- 解释器: 包声明的固定 venv Python **3.12.14**（本机路径与 `START_CUSTOMER.cmd` 一致）；系统 Python 3.9.13 非目标，未使用。
- 全新副本上运行；全部子进程 `-I -B` + `PYTHONDONTWRITEBYTECODE=1`，cwd 始终在评审私有根（绝不在包树内）；运行后副本仍 261 文件、无 `__pycache__`/`.pyc`。
- 入口模块导入 6/6 exit 0（`tools/customer.py`、`tools/run_usense_owned.py`、`annotation.customer.{production,interrupted_save,retained_readback,delivery_display}`）。
- `--help` 2/2 exit 0（`customer.py` 命令面、`run_usense_owned.py` batch/recovery/live）。`customer.py` 中文帮助在 GBK 控制台捕获中显示乱码为采集环境编码现象，非包缺陷。
- 新差量测试（先审读确认合成/模拟、tempfile 临时目录、无真实资源）:
  - `test_a30_interrupted_save.py`: **12/12 OK**
  - `test_a30_holder_metadata_exit.py`: **9/9 OK**
- 未运行 `START_CUSTOMER.cmd`、未启动 Edge/专用 profile、未调用平台、未运行 OCR/模型/login、未写真实 workspace/settings/profile、未重跑旧接受矩阵。

## 八、限制

1. 独立性为会话级 + 同模型家族；非原 Codex 评审者；M1 用户批准（如实记录）。
2. 仅离线验证：未做真实打包启动、平台、OCR、模型验证；`CUSTOMER_READY` 仍为 false，真实运行验证留待授权后的实际执行。
3. 全部运行检查使用包声明的固定 venv 解释器（3.12.14）；未验证系统 Python 3.9.13 兼容性。
4. 未验证客户独立完成体验维度。

## 九、结论

**ACCEPTED_OFFLINE_CUSTOMER_PACKAGE_V114_CANDIDATE**。ZIP 完整性、来源/包身份、差量、泄漏扫描、入口与默认安全、声明一致性、有限离线运行检查全部通过；未发现任何凭据泄漏、越界写入路径或声明夸大。本结论仅覆盖离线候选包本身，不构成真实平台/OCR/模型运行的验收。
