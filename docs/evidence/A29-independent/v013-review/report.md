# A29 v0.1.3 独立接手验收

结论：`ACCEPTED_OFFLINE_ONLY`，限定为**当前电脑、固定外部运行时、本机离线接手**。没有阻断发现。独立解包后，README 的实际命令可运行；不据此宣布新的平台保存、读回或 A28 能力完成。

固定代码 `1267b9f19d68ed01f205d3c17a831931783d6365`，最终文档提交 `dd369096ef01a6ed2e235ae22df3983d724a8aa0`，已接受产品基线 `ebca4c71a70bdfb5fbccc023d00e0207ae532470`。ZIP 为 `A29-v0.1.3-local-win64.zip`，2,477,179 字节，SHA256 `6530fc9c7d42e509fbc0048bca1c9ba9ed5c2cebdf535a6ba7218032331df006`。manifest SHA256 `5a727e73aaf58205f12b3696ffb0c24c66eeb3efe9410989d4992d401cf8b1f8`。

根冻结清单 SHA256 为 `18e625b93fdc4c9fb9da1f4ab925216a81dd1c3dd7928eb39dcb51d86c56c2fa`。177 个冻结输入逐项核验并复制到独立私有目录，只读取 root-index 的 frozen 路径，未读活动作者源码或原 source 路径。ZIP CRC、成员路径及大小写重复检查通过；解包目录为 `D:/1800/.local/stages/a29-independent-20261023/v013-review-01/unpacked with spaces/A29-v0.1.3-local-win64`，包内无 `.git`。

包内 100 个清单成员加 manifest 共 101 个文件逐字节核验。96 个来源文件与固定提交 raw Git blob 相同，其中 92 个 app 文件与已接受 A27 基线完全相同；不做换行归一。最终文档与 final commit 的 raw blob 相同，code 至 final 仅两份文档变化。内嵌 A26 ZIP 仍为原接受摘要 `7b1718ff909b013e0426dad890189dfa22bea5c101a6535a166544cc7c0c0bfc`、59 个文件；未重开浏览器或重做旧五题验收。

15 条独立命令均达到预期，11 条正常退出 0，4 条有意拒绝退出 2。命令脚本、cwd、开始时间、退出码、原始 stdout/stderr 和摘要保存在 commands.json 及相应私有原件。

| 检查 | 实际结果 |
| --- | --- |
| 无参数启动、显式 check | LOCAL_PACKAGE_CHECK_PASSED；100 个包成员、1415 个固定运行时文件通过 |
| batch / recovery / live 三类 tool-help | 原入口帮助正常输出 |
| sample-preflight，输出路径含空格 | 生成合成输入和 batch-preflight.json，PREFLIGHT_ONLY_NO_BROWSER |
| README `batch-preflight -- @batchArgs` | 参数原样传入，预检通过 |
| README 固定 Python 直接原批入口 | 预检通过；与 sample、包装入口三份结果深度相等 |
| recovery-run prepare --help、live-run capture --help | 子命令和选项正确透传；未传入真实资源 |
| 再用同一 sample 输出目录 | FRESH_OUTPUT_OUTSIDE_PACKAGE_REQUIRED；旧产物不变 |
| 合成参数传入 batch-run | SYNTHETIC_INPUT_IS_OFFLINE_ONLY；原批生产工具未进入 |
| 独立复制包后损坏 README | PACKAGE_BYTES_CHANGED:README.md；原验收包不变 |
| 独立解释器/包来源探针 | Python 3.12.14、OpenSSL 3.5.8，六个模块来源已记录 |
| manifest SHA 改为全零 | BATCH_INPUT_HASH_MISMATCH；仅生成失败 summary，全部 NOT_RUN、identity_validated=false |

实际 annotation 来源是独立解包目录。Playwright 1.58.0、Pillow 11.3.0、greenlet 3.5.6、pyee 13.0.1、typing_extensions 4.16.0 均来自 README 明确绑定的 A25 venv；基础解释器来自 Codex 已有 Python 目录。`-I -B` 生效，没有活动 A29 作者目录导入。这里允许使用明确声明的既有 A25 运行时，未将其冒充随 ZIP 分发的运行时。

合成样例虽沿用 book 46007447/native order 18 的格式，但 node/info/目录身份均为 synthetic，语义课时为 SYNTHETIC_ONLY，plan 明确 write_authorized_by_this_module=false。独立合成 profile 和 ledger 始终为空；示例不是旧五题成功输入。包成员分类为固定源码/说明、哈希元数据/依赖锁与已接受 A26 成品，没有携带实际 profile、cookie、密码或 token 文件。未读取现有登录资料。

README 已明确输入结构、解释器和依赖、默认入口、输出目录、失败检查与接续：首次失败停止，保留原件、锁、ledger 与释放证据，后继 NOT_RUN，不自动重发或补造 accepted marker。负例确认错误输入会保留失败摘要；原样例结果保留。历史 v0.1.0 参数绑定失败、v0.1.1 透传失败、中间错误成功声明的撤回、v0.1.2 换行问题及旧 ZIP 都保留在本次冻结输入，不覆盖或重跑旧失败。

限制：这是当前电脑限定的代码包，Python/OpenSSL/依赖和 Edge 不随包提供；运行时路径或字节变化需要新的绑定。A28 新能力、具体生产输入/authority 和外层持有器未纳包；新操作者必须另行取得已接受的这些材料才能生产。既有登录依赖不等于当前平台身份已验证。A27 新恢复、真实 Edge 进程枚举及真实恢复仍 NOT_RUN。A25 q3/q4 历史限制不升级，不能据本验收获得严格 revision 前驱资格。跨机器、完整独立生产部署、整书完成均未验收，不作为这次 v0.1 门槛。

本轮产品验收前，审查辅助脚本在 Python 3.9 下调用不支持的 Path.write_text(newline=...) 失败，产品进程尚未启动；原脚本及错误留存。新辅助脚本改为显式 UTF-8 write_bytes 后执行，原空输出目录保留。此前 readiness 的独立编码失败也保留。两者均为审查辅助工具错误，不计作产品失败，也不抹去。

本轮平台请求、浏览器启动、真实 profile/credential 读取、OCR、旧业务套件及成功保存重放均为 0。15 个自有命令进程已完成、无超时；PowerShell 同步等待 Python 并传回退出码，所跑离线分支没有浏览器或后台子任务。未执行真实进程全局枚举，不借此证明生产外层持有器。没有待释放自有会话。仅新增审查证据与独立解包/合成输出；未修改产品、根 JSON、AGENTS、自动化，未推送或发送 B/外部消息。1800-a 未被本审查操作。
