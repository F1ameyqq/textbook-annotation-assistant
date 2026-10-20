# A16 已批准的一次真实只读观测

2026-10-20。用户已对固定提案 `docs/tasks/A16-observation-only-tls-decision-proposal.md` 明确回复“批准，仅此轮有界只读观测”。该提案 SHA256 `103d036a730cbacc72043ed87b92ffcb8ed5731cdbcf9ae108e05b372c70b849`。用户决定原文与正式机器决定保存在 `docs/approvals/A16-observation-only-tls-user-decision.json`。

这是同一 A16 阶段已准备、尚未使用的一轮 live，执行者仍为 `01a15840-7766-7533-818d-cc016aa0a60b`。已完成正式独立和调度有限接受，无须重跑任何离线 suite 或静态 launcher。原R02未修复，其样题/schema资格能力保持停用。

## 固定运行物与决定

- 产品 `dd22193a30e969aaf90043365f31f84a5a50df59`，final `2453c71c070c153a22a49b772bb2696b3858f5d4`，候选 SHA `e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f`，产品workflow `afed9807c77f33d5363d706d5341acb1fd172baf`。
- 从作者已经冻结的 raw-checkout 执行：`D:/1800-worktrees/a16-current-state/docs/evidence/A16/current-readonly/revisions/observation-only/raw-checkout`。调度先核此目录16候选依赖及候选清单原bytes；不得改源码、依赖、模板，不能另造或替换driver。
- 已接受独立机器报告固定在 `D:/1800/docs/evidence/coordinator/a16-observation-independent-closure/review-output/review-result.json`，SHA `d536d9b2552586a0e1838384a1b2775df1b14023d3e7ad901ac1a2b991e06a0c`。
- activation v2固定在 `D:/1800/.local/stages/a16-current-readonly-activation.json`；具体原字节SHA、决定SHA、UTC窗口、命令argv及派发去重意图在 `D:/1800/docs/evidence/coordinator/a16-observation-live-dispatch/dispatch-intent.json`。必须匹配，不自行改期或补写激活。
- 原profile非敏感指纹固定 `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00`。只由固定产品一次性做实际指纹/锁/占用核实；调度旧参考不证明当前认证。不能复制凭据、换profile、清锁或批量结束进程。

## 唯一启动及停止

读本任务、决定和意图后，确认指纹、候选及报告SHA与固定值一致，便按意图里的 `argv` 在固定 raw-checkout 调用一次外层 `tools/a16_current_state_launcher.py`，带显式 `--live --certificate-exception` 及完整绑定参数。不要先运行默认静态模式、旧suite、旧A15驱动或另一次探测。用当前Python解释器，环境 `PYTHONIOENCODING=utf-8`；若使用PowerShell后台helper必须Hidden，但不需要自行另加helper。

一次启动含原专用无头context≤1、主导航≤1、书46007447、viewer14/173、六业务GET各一次、两原图各一次，总窗口≤900秒含释放。sample0、自动schema=false、登录提交/业务写入/上传/OCR/送交0。获准同源session/static辅助资源不扩大，不混称总请求8次。context TLS例外也影响获准OSS原图请求，用户已确认这一点。

所有前检、启动和运行异常都是本轮证据；首个意外失败即停并保留后继NOT_RUN。即便在真正浏览器启动前失败，也不得修改产品、命令、activation、输出位置或标记后再试。过期不重开窗口，取消/拒绝/失败不恢复旧任务额度。单次启动已占用本轮唯一派发，实际context/navigation/API次数如实报告，不与额度混淆。

唯一输出 `D:/1800/.local/stages/a16-current-readonly-live` 由固定launcher独占创建；调度和作者都不得预建。若已存在或任何标记冲突，停止，不删、不另换路径。网络/方法/逐跳/WS/子target/身份/登录/期限守卫保持；未知API和意外样题请求仍停止。只在既定被动资源预期拒绝规则内继续。

执行时等待自己的工具子进程完成或正常用同一session轮询，不重复调用launcher。只记录其wait/exit和可证身份；外层launcher自身OS退出身份UNKNOWN如实保留。不得通过全机扫描、批量kill、清锁或移除profile做收尾。固定产品负责其自有句柄/Job/context清理；释放UNKNOWN则只封存，不能继续访问。

## 固定交付

结束后将新的报告、统计、脱敏运行证据和raw清单新增到作者工作区 `docs/evidence/A16/current-readonly/revisions/observation-only/live-delivery/`，提交一个固定交付final并释放；不改此前任何冻结证据或产品文件，不重跑检查来补证。保持根JSON/调度文件由调度写入。

**真实静态脚本bytes及完整来源sidecar只留 `.local`，不得打印、复制到Git或报告内。** 可以交付其相对引用、SHA、长度、脱敏来源及保存清单；独立需要时将在释放后只读核本地原件。不得包含cookie/token/auth/headers/profile或未脱敏请求/原视频。原图和明确非敏感书/目录/框投影可按原策略交付，若无法确认字段安全只保留本地并报告限制。

报告区分已取得和UNKNOWN/NOT_RUN：认证是否证明；当前书籍/目录/题框库存的覆盖性；viewer14/173原图及映射；静态素材数量与摘要；实际首个阻断的脱敏scheme/hostname/port/resourceType/reason；context/navigation/固定GET/原图与审计事件数量分别记载，不能把双守卫事件当请求次数。成功仅是只读真实证据，不代表schema、首题或保存资格。

固定候选、原决定与activation、原始输出、失败/释放、版本/命令/时间及资源限制要能交独立核证。记录未保留OS创建身份等限制。样题NOT_RUN、正文/schemaUNKNOWN、production_ready/write_eligible=false、原R02 REWORK保持。其他三例HOLD、Q22不导航重放、0 B及外部联系人消息；首题保存和刷新重开独立读回仍留待下一正式阶段。

本轮交付释放后，由调度提供固定raw给同一正式独立对话验收实际结果。禁止作者自行接受或启动后继业务。
