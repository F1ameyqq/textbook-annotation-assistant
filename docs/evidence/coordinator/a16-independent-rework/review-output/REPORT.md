# A16 固定离线交付正式独立验收

**result=REWORK**。`task=A16`，`candidate_manifest_sha256=2579b043d65e665263796d0922f080ad101f4d20c1e9ea500fd7894ba41d966c`。独立反例证明样题单题框角色/顺序改变后仍被接受为正常只读结果；作者33项通过没有覆盖这个缺口。本包不给 ACCEPTED_OFFLINE_ONLY、TLS批准或live激活。

独立对话 `01a15841-0d44-7272-9740-40d013839869`；审查工作流 `7409a94d9e94eb1b5a7414a7cbb701b320a9f329`；作者产品 `2a604c2d0b0f7781ec0d7ca4b5925ae9ff53b595`；final `4fe417d5246f20fbbbedc577495c7ca400d4ded8`；base `7432122b9fd5602785ebfb2b3f24e407fdf76eda`。执行任务与初次准备工作流仍为原386353f9，不把两者混为一个版本。

## 实际结果

| 项目 | 结果 / 证据 |
|---|---|
| 固定输入 | 49raw均与final Git blob相等；47新增路径；31,259旧成员mode/type/blob零差异；A15 native引用原bytes相等 |
| 准备包 | 原37成员及manifest SHA256全部复核保全；沿用v002的48项标准，不改准备包 |
| 初次作者suite | independent-01导入 `annotation.source` 失败，loader记1 error，33项产品测试未运行；PID70728，wait完成、exit1，原始输出保留 |
| 调度补件 | 同一final新增固定 `src/annotation/__init__.py`，73bytes、SHA a11279a7897a17523423f81c888a410edfb53c74d36435f7ab7c7cfacc67ca2d；原49成员相等，产品/候选未变 |
| 补件后作者suite | 新目录 independent-02 **33/33 PASS，500ms，shell exit0**，PID53424且wait完成；原bytes另复制入本报告目录 |
| 独立控制 | **12 PASS / 1 FAIL / 3 NOT_RUN，94ms**。首个语义反例后停止产品探测；后3项不补跑 |
| 默认静态路径 | 独立C01实际 `probe.main([])` 校验固定候选并返回0，严格TLS、无native/profile/Popen；首次命令组的独立launcher子进程因前序导入失败未运行，不冒称它已复现 |

原始依据分别见 [raw-preflight-result.json](raw-preflight-result.json)、[input-raw-manifest.json](input-raw-manifest.json)、[fixed-command-results.json](fixed-command-results.json)、[initial-suite-raw/unittest.txt](initial-suite-raw/unittest.txt)、[supplemented-input-preflight.json](supplemented-input-preflight.json)、[supplemented-suite-raw/unittest.txt](supplemented-suite-raw/unittest.txt)、[supplemented-suite-command-result.json](supplemented-suite-command-result.json)、[independent-controls-result.json](independent-controls-result.json)。

首次导入错误来自调度49raw隔离包缺父包初始化文件，不作为作者产品回归。补件经同一final原始blob校验后，只在新50raw目录复现一次；首次失败和NOT_RUN保持。独立控制采用仅绑定冻结模块的内存package bridge，绕过缺失父包导致的环境同名包解析；没有修改产品或运行未冻结源码。

## A16-R01：样题框身份检查遗漏语义字段（P1，已复现）

定位 [probe.py第512行](../../../../tools/a16_current_state_probe.py) 至514行。该分支只比较rect_id集合、file_id和order_in_level，未核样题当前角色、zone索引、目录、页、bbox、父框和内容类型。第497行从初始库存取得的expected_frames随后继续用于正文，而单题读取实际返回的框被丢弃。

独立基线的全量库存含题3、22，样题3是正常Q/W/W/W/W/A、W索引0..3，运行真实collect到decoder/selector/schema/register_sample/content链，得到READONLY_REVIEW、FULL库存/PARTIAL正文。反例只改变后来单题框响应：

- `r-3-1` 保留同一ID/书/题序，将 `type=choice` 改为 `answer`。
- `r-3-2` 保留ID，将 `image_order_in_annotation_zone=1` 改为3，与另一choice索引冲突。

实际没有抛错，sample_frames和后续sample_info、question/choice/answer步骤全部DONE，仍返回 **READONLY_REVIEW**；choice正文仍 **AVAILABLE**，使用原库存的四个choice rect_ids。见 [counterexample-changed-sample.actual.json](counterexample-changed-sample.actual.json) 和独立C13。该证据使用合成传输、原图/UI证明及文件写入桩；实际执行的是产品collect、inventory、sample_order、current_code、register_sample、bound_content和样题检查分支，不是仅复述作者断言，也不证明真实平台效果。

修正要求：对单题响应与库存按ID逐字段核定保全/身份语义，差异停止后继；正文应绑定已验证的当前单题框及显式zone顺序。为相同ID但角色/索引/目录/页/几何改变增加独立负例。不得通过忽略差异或回填旧框使其通过。

## 其他静态缺口

**A16-R02（P1）：当前schema确认仅依赖词汇共现。** [decode.py第189行](../../../../src/annotation/source/usense/current_readonly/decode.py) 的has_read只在一个宽文本块中找file_id/question_order/zone，在整份脚本找另两个endpoint名字和zone字符串；has_content又只检查整份脚本是否出现ocr_result和success。没有将它们绑定到getter实参或实际响应解码对象。随后 [policy.py第67行](../../../../src/annotation/source/usense/current_readonly/policy.py) 只凭这些bool注册五个写死的GET，collect使用content_schema_confirmed产生AVAILABLE/KNOWN_EMPTY。

仅在相邻注释或不相关函数中出现这些词就可能满足现有条件；这不能证明参数来自当前getter，也不能证明 `data.success/data.ocr_result` 是该响应schema。词汇命中可记录为CURRENT_CODE观察，但适用性须UNKNOWN，直到有具体函数/字段/响应来源绑定；未知参数不登记、不试探。C15专门运行反例在R01后 **NOT_RUN**，本项是静态逻辑发现，未伪造运行输出。

**A16-R03（P2）：原图未完整解码。** [decode.py第162行](../../../../src/annotation/source/usense/current_readonly/decode.py) 只读size/format并verify，没有load完整像素；original_once之后直接保存并返回尺寸和摘要。需对确切同一bytes完整解码，保留“header可读但JPEG残缺”负例。C14在R01后 **NOT_RUN**；本报告只确认实现缺少完整解码步骤，不声称已运行某个残缺图并观察到接受。

**A16-R04（P2，结构化释放口径）：** [probe.py第670行](../../../../tools/a16_current_state_probe.py) 的worker RELEASED条件不含前后created_filetime相等或无身份错误。第641行身份不符会记error，但如果job空、handle关闭且after.exit_observed，状态仍可为RELEASED。父层仍因errors返回失败，因此没有证明live放行绕过；应将身份不符的释放状态保持UNKNOWN。C16 **NOT_RUN**，仅静态发现。

以上问题和精确证据边界汇总于 [findings.json](findings.json)。作者产品未改，任何修正需同阶段新冻结版本和新证据，旧结果不能覆盖。

## 已有限核定的行为及48项覆盖

[requirement-matrix-48.json](requirement-matrix-48.json) 对准备的48项逐项列实际证据与剩余部分。它不是“48项通过”的声明。关键独立正反控制包括：

- 默认静态无资源路径，严格TLS默认；合成严格/本context例外互相隔离；A15 task/run和错误owner/book/viewers/target/candidate/profile/output/次数/类型/期限拒绝。
- 固定6项同源GET的正例；未知API、错误书/页/参数、写方法、活动跨域/重定向拒绝。固定声明的Image/Font/Media被动拒绝后可继续；接着POST即致命，首错保留、后继不调用。
- URL敏感路径、userinfo、query哨兵及任意异常文本未进入脱敏事件。GET_JSON的既有auth只在页面内部消费，实际凭据未读；复杂嵌套响应和所有输出通道未做全覆盖模糊测试。
- 直接调用CurrentGuard.capture捕获响应bytes，再由get_once和native paused的本地fulfill使用同一bytes；第二次不发GET。真实浏览器两层hook顺序、CORS和UI请求形式仍未验证。
- 全书题序按数字而非列表/字符串取最大22；乱序11/22/3选择3；只有22时无样题；Q22保留库存且不导航/重放。FULL库存与PARTIAL/UNKNOWN正文及write_preservation_baseline=false保持分开。
- AVAILABLE/KNOWN_EMPTY/UNKNOWN的纯字段区分与逆序rect_ids拒绝；viewer14的源资源57按响应保留，不强改历史13；六框草稿的四Q替四W、标签交换、数字交换、答案页错误拒绝。
- 晚到守卫错误在模拟close await中发生，真实observe_live终态序列把先前成功改为ERROR。该函数通过内存open/close桩验证，无live资源/会话启动。局部等待用独立假时钟7→28超时，不重发。

逐跳CDP/自动附着子target/service worker阻断、原生Job/held handle释放和每层自身monotonic预算已完整静态读取，未调用真实nativeAPI或进程扫描。worker及launcher分别从自身started和UTC remaining换算；没有把父进程monotonic绝对值传给子进程比较。但这些离线证据不等于真实进程时限或OS释放已经验证。

库存是声明字段投影，虽增加了zone索引，仍不保留image_path等完整旧记录字段；代码明确不构成后续写前保全基线。正文只读一个样题，不能满足旧A11所有旧正文AVAILABLE的入场门；旧A11文件原bytes未变，不靠重标签、删Q22或放宽旧门制造READY。

候选的Q/W/W/W/W/A、A→D四组数和答案C与历史图/任务一致；末尾句号、框几何和当前来源仍是待核草稿。没有本轮新题排除、末级目录或业务批准。当前认证/书籍/source/target/接口适用性都没有live事实，首题真实保存及内容/题框刷新重开独立读回 **NOT_RUN**，其他三例HOLD。

## 失败保全、资源和交付

作者run01/run05在固定包中只有明确标为重构的失败摘要，完整traceback仍在作者聊天，独立未读取该聊天、未把摘要升级为原始现场；run09 exit0来自作者报告补充。原CRLF/LF finding和pre-raw-fix candidate清单不动。作者静态launcher释放只含PID/wait/exit，没有创建身份；本轮两个子进程也只声明wait完成及退出码，不声称持有OS创建身份或观测独立自身退出。

本次所有真实浏览器、网络、profile/凭据、native真实API、实际占用扫描、登录/业务写入、上传/OCR、旧suite、其他聊天/B消息均为0。独立控制资源哨兵尝试表为空；结论限本次明确调用路径和记录，不声称全机资源不存在。没有授权/生成live activation，没有A16 TLS批准，A15一次权限不转移。

原49raw和原37准备成员在交付前再次核字节保全。全部报告/自编工具仅新增于本目录；两次作者suite只分别写获准independent-01及补件目录independent-02，原run01–run09、产品及D:/1800根任务/JSON不修改。补件复现原bytes已复制纳入本包。

机器结论 [review-result.json](review-result.json)，释放 [release.json](release.json)，输出清单 [raw-manifest.json](raw-manifest.json)，最终保全 [final-preservation.json](final-preservation.json)。状态 **REWORK_RELEASED**。下一依赖为调度安排本阶段明确纠正和新固定交付；本独立对话不自行改作者产品、派发外部消息、激活live或给候选业务批准。
