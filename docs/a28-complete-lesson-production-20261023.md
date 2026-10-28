# A28 第二课时完整生产：四个新增单元

基线 `ebca4c71a70bdfb5fbccc023d00e0207ae532470`，分支 `codex/a28-complete-lesson-production-20261023`。本文件是执行准备记录；正式独立接受、实际保存、独立读回和原生导出分别留证，不以本地通过代替平台成功。原 A25/A26 五题和第一课时成果保持，sole1800-a 为 PAUSED。

## 原图分母与固定内容

viewer12（印刷4）、viewer13（印刷5）和 viewer173（答案印刷25）已目视核对：第2课时“勾股定理的验证及简单应用”有编号1–8及第8题变式，共9个独立单元。印刷5下方“漫话勾股世界”另属一节，不计入本次分母。复用已接受的1–5，本轮新增6、7、8、8变式，共4题、14框。Q6=C（2.7米），Q7=D（44），Q8能通过，变式不能通过。

私有 `content-v1/bundle-manifest.json` SHA256 `22b0390244e8063c6ba35764538cc46c09ce56f4d7d772378ae94b4101e899e7` 固定四候选、四来源复核、十四本地裁片及三原图。Q6只用梯子图，Q7用其题干上方两个弦图；开放题 `wenda` 来自既有原生info。所有正文/选项/答案均绑定UTF-8摘要，不执行OCR。十四个精确源裁片URL各GET一次，HTTP200、尺寸和完整像素解码通过，四组合图已目视；`remote-crops-01/crop-proof.json` SHA256 `a08c9ff26f7c392ac48decdb2e77c3b1d217eb0aa55240acb72a85e493f64cad`。

## 当前结构与唯一后继保全

当前实际6GET和必要后继13GET均成功、context/runtime与各自外层Job/持有进程全部释放。原目录23题、76框；正确第二课时目录 `dir-1792063578574-lvqkxdluj` 为空。既有五题仍在原父目录 `dir-1792063578574-2a6vq8zom`，不迁移。唯一后继是下一节 `node1792148510557 / info2111049977118109698`，native23，两个框；它不是第6题。

已冻结官方前端JS原件SHA `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41` 的 `nse/CB/rse` 直接证明：选空目录新增时以此前最后题号22为插入锚点；`C0` 按目录DFS排列全局序号。实际回执及读回仍须证明服务端效果。四题依次在22、23、24、25后新增；后继旧题顺移到24、25、26、27，稳定node/info和题答保持。新身份始终从当前原回执及新鲜info取得。

## 最小产品适配

`lesson_insert.py` 只接受本书、本课时和四固定逻辑单元。复用已有Q7插入格式、`commit_unified_submit`、双层 `ExactPolicy` 和 `SEND`，不改旧Q7纯合同。已有 `insertion_writer.py` 根据明确计划schema选择13响应保全范围和3/4框演员绑定；原22题/7框路径保留。所有插入writer使用已接受A27 `close_framework` 和 `run_owned_writer`，持久intent和精确body摘要先于唯一POST；任何UNKNOWN不重发。

`run_usense_reviewed_batch.py` 的新 `A28ReviewedLessonManifest/v1` 分支接入四题串行生产。全部来源、候选、审校、远端裁片、当前raw、ledger及第一计划在浏览器前核验。第一题由当前13响应构造计划；后续题只使用上一题已独立读回接受的真实快照。每次writer退出且释放后，另PID/新context的reader读取新题、唯一后继和本轮已插入的所有前题：20、27、34、41个GET。每次比较旧全框和目录、唯一后继全部七响应及本轮前题原生正文；不重存旧5题，也不重复它们的显示实测。

允许的旧数据变化仅为唯一后继的序号及其框/info上严格单调、位于实际发送窗口的原生更新时间（固定北京时间，秒级量化最多1秒）。其余字段、数组、对象键序和内容保持严格。新节点仅接受已观察到的两种键序；新OCR区仅接受两种已观察到的直接data键序，字段/类型/完整值必须相等。完整实际比较、原始严格证据和限定元数据变化逐项保留。新结果不写旧existing-update的标准accepted marker，不充当revision前驱。

## 准备检查与限制

四个真实固定候选的 `--preflight-only` 已通过，0浏览器/平台写入。最终六文件绑定下新增40项检查全部通过（2.165秒），包含19纯合同和21批处理/发送/释放检查，未跑历史套件；最终固定提交/原件清单由 `fixed-delivery.json` 指向。首次本地configure因未创建输出目录 `PATH_MISSING` 在启动前拒绝，0浏览器/请求；保留原脚本和失败事实，再补齐本地目录。新增检查初跑18通过/1旧ledger前缀夹具失败保留，按当前确切ledger_key修正后通过。准备阶段工具/夹具错误保持在私有检查原件中，不擦写成PASS。

私有阶段：`D:/1800/.local/stages/a28-complete-lesson-production-20261023`。当前新增平台保存和完整课时交付尚待本次固定代码独立接受后执行；原生导出沿用A26机制。授权仅此书此课时，不含整书送审、其他书、登录/凭证配置、profile替换、清锁或外发。
# R1: known old identity exclusion

The initial `48cbd114` code review found that a synthetic new Q6 readback could
reuse accepted Q5's `info_id` and still pass. That fixed review and its failed
counterexample remain unchanged; the original code is not eligible for live use.

The revised comparator excludes eight explicitly known old info identities:
native orders 1, 7, and 18–23. Six are bound to existing native info response
bytes, Q1 to its accepted public proof, and Q7 to the accepted code binding.
The writer and batch preflight reopen these sources and verify their hashes and
values against the finite exclusion table. The plan includes the evidence
reference and coverage. The other 15 old info originals are unavailable locally;
this revision does not claim full-book info identity acquisition. Prior-new-ID
uniqueness, all existing frame and directory checks, and old-tail content
preservation continue unchanged.

Eight distinct new R1 controls passed, including actual pure-comparator calls for
all eight aliases and a normal four-question chain. A local evidence fixture
initially omitted the native `message` field; its original failures are retained,
and only the three affected tests were rerun after correction. The actual four
candidates also passed the revised preflight without a browser. The prior 40
checks remain historical evidence for `48cbd114`, not a fresh R1 suite run.
