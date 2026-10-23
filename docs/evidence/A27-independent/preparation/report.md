# A27 独立验收准备记录

当前状态：`WAITING_EXECUTION`。已准备有限标准，尚未收到根协调者送达的 A27 精确冻结候选；产品审阅、新边界测试及真实验证均为 `NOT_RUN`。本记录不是产品接受或返工结论。

本次只读取两份 A27 任务书、指定的四组 A25 固定公开报告/结果/清单和对应根收口 receipt。22 份公开来源已按原字节复制到 `D:/1800/.local/stages/a27-independent-20261023/preparation-inputs/`；四个旧 review-files 清单的摘要与根 receipt 相符，12 份 report/result/raw-manifest 与旧固定清单相符，result/raw-manifest 另与根 receipt 相符。每份复制前后源摘要和副本摘要一致。未重新遍历或验收 A25 私有底层原件。

A25 的既有结论依当前已核固定报告继承：五题已分别保存一次并完成新鲜独立读回，其中四题 strict 全量匹配、一题适用有限新增区键序对账。第三题原 strict FAIL、第四题原 context/runtime TimeoutError 和 false 标记均保留；第 3/4 题没有标准 accepted marker，不能由这些旁证取得旧 revision 前驱资格。旧第四题最终整批 OS 释放不覆盖其框架关闭失败；根因仍 UNKNOWN。上述事实无需为 A27 再保存或再回读。A26 的原生导出/显示交付不在本次独立审查范围。

冻结候选接收门：根须提供准确 base/product/final commit、最小差异、Git 原 blob 与依赖清单、固定原件/副本路径和 SHA-256、作者命令/环境/退出码/未裁剪 stdout/stderr，以及首次失败和后继 NOT_RUN。基线任务指定 `389d2e7a282d21efa25db8d01c02d115ce9e83b7`。仅从根指定冻结入口获取候选，在本独立隔离目录中建立新候选快照；不扫描作者活动目录，不以 Windows checkout 换行规范化结果替代原 blob 身份。根尚未送达候选，因此本次没有产品源码扫描、导入或执行。

有限验收矩阵如下。实际新控制在收到候选后按其真实入口最小化实施；以下均为拟验收项，不是通过计数。

|编号|验收标准与最小拒绝控制|
|---|---|
|K1|沿正常 batch 入口追踪比较器调用和结果消费。既有 strict 成功仍成功；合成的新建题干/答案区有限键序例必须经实际正常调用链产生清楚标记的结果，不能仅孤立 helper 成功。|
|K2|只接纳本 plan 从严格 absent 新增的对应直接 data 对象，且精确三个键从 `rect_ids,ocr_result,success` 到 `success,ocr_result,rect_ids`；调整 expected 私有副本后仍作完整严格比较。其他排列、既存区、非目标区、嵌套对象键序变化均拒绝。若候选改变此有限规则，需要明确新增证据，不能默认扩大。|
|K3|拒绝任一值变化、bool/int 或其他类型替换、缺失/null 替换、未知/缺失字段、数组顺序或内容改变、OCR 字符串改变；同时核未涉及的目录/框/info/其他区域和完整快照保护未放松。输入 plan/after 原字节摘要不变。反例选择可区分错误全局排序、浅比较和宽松数值相等的最小变体。|
|L1|通过候选真实关闭调用链注入 context.close 与 runtime.stop 分别超时/异常及正常关闭；核 deadline/取消/后续清理是否有界、首次错误是否保留。不能靠延长原超时、吞异常、任意标 true 制造成功。仅对候选所宣称的有界行为结论负责；原历史根因继续 UNKNOWN。|
|L2|框架 context/runtime 成功与 OS 释放分字段、分证据。拒绝仅 shell exit、关闭 handle、PID 无创建身份、只见 writer 退出但持有子进程未证、Job 未空/未知、释放时间晚于 reader 的情况；最终整批 Job0 不能冒充 reader 启动前逐写进程及其资源释放。|
|R1|恢复前绑定同一稳定保存意图、plan/目标身份、唯一精确成功原回执、保存次数及受信固定引用。缺回执、HTTP 成功但业务失败、错误目标/intent/hash、UNKNOWN 业务结果均拒绝；不能信任单个 success 布尔。拒绝须发生在创建 reader/获取 profile 等真实资源之前。|
|R2|只有该 writer 及持有资源确切释放、同一 profile 独占、新进程/context reader、完整原始响应/时间/身份/摘要门禁满足时才允许恢复。比较必须覆盖完整约定快照，并保留有限键序类型与 strict 类型区别。旧 writer 释放 false 不被恢复成功改写。|
|R3|通过真实恢复调用路径及替身调用计数证明最多一次只读 reader，所有分支零恢复 POST。相同恢复意图再次进入、reader 失败/超时、比较失败、已消费或不明状态均停止；不存在以再次 writer/POST 作为关闭异常或业务未知的补救分支。必要时核一次消费发生在启动前。|
|E1|旧 FAIL/intent/ledger/accepted 原件不能被补写、替换或清理。合成历史第 3/4 失败证据不得被新入口升级成旧标准 accepted；新的证据必须清楚命名并区分完整保存读回、纯比较、框架释放和 OS 释放。|
|E2|检查新证据的所有实际消费入口，尤其 revision 前驱。若旧标准不消费新类型，证明保持拒绝；若支持新类型，验证完整来源/身份/计划/回执/读回/释放链并对伪造或截断链拒绝，不能仅检查 type/accepted=true。不得回写历史资格。|
|P1|核最小差异及被复用 guard/supervisor/纯比较器原字节，保留作者/审阅首次错误，首个阻断反例停止并记录后继 NOT_RUN。只运行必要的新控制，不跑旧 194、OCR、网络、平台或 Edge，不触碰真实 profile/ledger。|

独立结论按层给出：来源身份、离线实现/新控制、实际平台行为、历史保存读回继承、释放证据。无阻断项且必要离线控制完成才可给 `ACCEPTED_OFFLINE_ONLY`；存在可复现违约给 `REWORK` 并保留原输出；证据或执行尚缺保持 `WAITING_EXECUTION`/`NOT_RUN`。任何离线通过均不构成新 live 授权，也不要求重做五题已成功实测。

本次公开准备件的命令、退出码和原输出分别见 `freeze-process.json`、`freeze.stdout.txt`、`freeze.stderr.txt`，输入逐件清单见 `input-manifest.json`。固定清单 `review-files.sha256` 不包含自身，另以 `review-files.sha256.self` 记录其原字节摘要，避免循环自摘要。

未修改根 state/AGENTS、作者产品、真实 ledger/profile 或自动化；未提交 Git、未发其他聊天消息、未运行平台/测试。1800-a 保持任务规定的 PAUSED；本次没有读取或更改其实时配置。准备工作完成，等根送达冻结候选后继续。
