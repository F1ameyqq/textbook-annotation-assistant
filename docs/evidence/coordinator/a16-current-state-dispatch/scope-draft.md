# A16 当前书/source/target与普通单选首题准备：合并只读阶段草案

2026-10-20。仅供主调度收敛下一阶段范围；不是正式任务、派发、activation或平台许可。本次辅助只读公开源码、固定旧证据及 next-readonly-inventory.md，只新增本文件，未运行产品、旧程序、suite、浏览器、网络、profile或进程扫描。没有新建或联系任何对话。

只设一个执行阶段与一个独立验收阶段，不把认证书籍、source、target、接口观察、候选题分别拆成新阶段。A15仍只承担它已批准的一次context观察；A15的证书例外、次数、activation和结果均不转移给A16。以下新阶段访问预算、TLS处理、代码与输出白名单须由调度最终明确后派发。

## 1. 最小目标与立即可准备内容

一次新的有界只读采集，交付：(1)当前认证书46007447身份；(2)当前完整目录、题身份/全书题序及现有题框；(3)两张目标原图及viewer/resource/尺寸/摘要/可见几何绑定；(4)当前文字、题型、W/choice和框读取schema，以及当前前端保存构造代码的只读证据；(5)恰好一道普通单选的完整候选资料与缺口表。

目标不是在只读轮中证明保存成功。题级保存、上传裁片、非空文字实际持久化、保存后的刷新/关闭重开读回均留待下一次明确的单题写入边界。任何“读取成功/代码已看见”不得变成这些能力的VERIFIED。

在等待A15正式收口时可并行做的工程准备，均留在同一A16执行/验收对话内：

- 执行准备：固定原始依赖/接口白名单，写新的受限读取驱动与脱敏decoder；从旧原图形成下面唯一候选的文字和六框草图；整理当前取证所需字段，不启动真实资源。
- 独立准备：从任务规则、原图和公共角色规则形成核对表，静态审当前GET边界；作者固定准备包后核其原始字节。不得读活动目录或并行占用profile。
- 原A10/A05队列、旧成功suite和A15原命令一律不运行。当前草案也不运行上述准备代码或任何检查suite；新代码必要的有限离线差量与次数由正式派发一并固定，不再为每个字段拆阶段。

## 2. 一个具体的候选，不依赖B复杂题

候选临时身份：`A16-46007447-source13-section2-printed1`。身份以本书、原图资源、节标题和内容绑定，不以印刷“1”作为跨章节唯一键；它不同于第一课时原A07/Q1身份。当前平台题身份、新题序和“尚未录入”结论均为UNKNOWN。

来源：历史viewer14/resource13，印刷第6页，“2 一定是直角三角形吗 / 基础题 / 知识点1 直角三角形的判定”，印刷第1题。历史参考答案在viewer173/resource172，同名节“2 一定是直角三角形吗 / 基础题”，明确“1. C”。本次已直接看过这两张归档图片，仅作准备，不是当前来源验证或新业务批准。

- 题干：`（2025·青岛城阳区期中）下列四组数能作为直角三角形的三边长的是（ ）。`
- A：`1，2，3`；B：`2，3，4`；C：`3，4，5`；D：`4，5，6`。
- 答案：`C`。六个独立语义区域为Q/W/W/W/W/A，四选项顺序A→D，不含附图、共享材料、解析、复杂公式或跨页题干。答案来源在另一页，明确单独绑定。
- 当前精确六框bbox、末级目录、源页映射及正文标点仍须从本轮原图确定；以上是转录草稿，不能直接作为执行payload。不得借相同印刷题号沿用A07或其他旧批准。
- 只核这一个候选。若当前图已变化、目录无法对应、现有题/框表明它已录入、答案区不清或无法证明新题身份，则保留候选HOLD和具体缺项，不在同轮自动换题、扫全章或扩大viewer。

归档原图原始字节：

| 文件 | 尺寸 | SHA256 |
|---|---|---|
| `D:/1800/docs/evidence/A05/execution/source-viewer14.jpg` | 1218×1694 | `4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9` |
| `D:/1800/docs/evidence/A05/execution/source-viewer173.jpg` | 1148×1621 | `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be` |

历史摘要只能用于比较，不要求当前文件为了匹配旧摘要而被替换。B复杂题、其他三例和全章不进入本阶段关键路径；Q22不重放，也不把它作为内容接口探测样题。

## 3. 执行阶段：一次采集完成五项工作

建议访问上限供调度确定：本书、1次新只读轮、1个专用context、首次平台操作起总15分钟；复用既有认证，0登录提交/账号密码或登录配置读取/认证值导出、0业务写入/上传/OCR、0刷新重开试验；首意外失败或LOGIN_REQUIRED停止，后继NOT_RUN，不换profile/清锁/重试。业务GET所需既有认证值仅由受保护页面内部消费。只取viewer14和173；viewer10、15不进入此最小范围。所有API只有事先固定的GET，业务POST/PUT/PATCH/DELETE及未知路径默认拒绝，继承逐跳、WS、子target、service worker、最终DOM守卫和精确自有释放约束。

live前唯一需要明确的外部边界：A15正式结果与释放；新A16授权范围/次数/owner/输出；TLS模式。默认严格校验；若新context仍需要证书例外，须有明确覆盖A16的新决定，不能引用A05或A15旧例外，不重复索要已经存在的平台连接许可。

执行顺序不增设子阶段：

1. **当前认证与书身份。** 按当前受保护DOM、最终守卫和书ID联合核身份；UI只选择书46007447，读取书列表中唯一目标，记录标题、状态、题数、更新时间及当前前端资产版本。页面显示或HTTP200单独不足。书列表账户筛选和认证值只在原页面内部消费，证据不含账号/token/cookie。
2. **当前完整目录与题/框。** 各取一次目录和全量框，保留平台题身份、全书题序、目录映射、框身份/角色/类型/页号/bbox/父框/zone顺序。用实际目录和全量框互核题数、唯一身份、全书最大题序及完整性，不用历史22题68框作预期，不从目录局部max推导全书追加。Q22若出现在正常全量快照中仅保留原记录，不导航或重放它。
3. **两页source。** 元数据一次、viewer14及173各一次页响应；从响应读取资源标识和原图URL，校本书与单页身份，再按来源绑定GET两张原图，记录实际尺寸/SHA。各页一次可见跳转，核viewer/resource/canvas与原图一致。不能按“viewer减1”猜映射，也不把旧resource13/172常量当本次观测。
4. **同轮取当前接口证据。** 保存本轮页面真实加载的同源脚本路径与bytes/hash，静态跟踪“提交修改”构造和已存在题的读取代码，不调用组件保存方法、不填编辑器、不生成待保存草稿、不点保存、不取上传签名。由当前全量框中确定至多一个非Q22、四choice框的现存样题（按明确平台题序排序后首个；若无合适样题如实缺证），只读它的单题框、题型以及经当前脚本证实的question/choice/answer内容查询。每个已确认GET至多一次；只观察返回schema和rect_ids/zone/text对应，不把样题结构预先当普通单选事实。路径或参数未被当前证据确认则UNKNOWN，不能猜接口试探。
5. **释放后离线形成唯一候选与接线表。** 基于本轮原图重核第2节印刷第1题和答案C，确定六框/全文/目录/原图refs；对当前题/框做候选重叠与题身份排除，不能只以“没有旧内部ID”证明新题。把当前schema转换规则及每个缺失字段写清；不在活动会话中边修驱动边再取一次。最终仅交REVIEW/HOLD及原始结果、清单和释放。

这里的“完整target”分开报告：目录/题身份/题序/框可完整；既有全文仅观察一个样题时必须标`content_coverage=PARTIAL`。不逐题扫描旧内容以制造本轮写前快照；真正单题写入前仍须取得足够新鲜的完整保全基线，不能将本次接口取证结果冒充后续写前状态。

## 4. 可直接复用的代码与确定的入口

| 功能 | 路径/位置 | 有效复用边界 |
|---|---|---|
| 有限业务GET及书/目录/框/source顺序 | `D:/1800/docs/evidence/A10/execution/preflight.py:202–250` | 可抽取公开读取/身份规则；不运行原driver，不沿用旧一次性标记。原A10这些业务步骤是NOT_RUN。 |
| 请求白名单、业务码和无令牌导出GET | `D:/1800/docs/evidence/A04/review/coordinate-R3-raw-bytes/inputs/raw product with spaces/src/annotation/source/usense/collector.py:26–72` | GET前guard；401/403→LOGIN_REQUIRED；其他非200/code非0拒绝。旧session含登录回退，不能整个照搬给无登录新轮。 |
| 目录/框字段decoder | 同上 `collector.py:91–133` | `_book/_directory/_annotations`可作起点；`_annotations`没有正文文本，必须保留这一缺口，不能直接构造全文完整target。 |
| 已保存单题框、题型和内容读取线索 | `D:/1800/docs/evidence/A05/review/independent_readback.py:174–190` | 公开脚本固定了Q22和当轮例外，只取函数/路径知识，绝不运行原脚本或复制其固定题序/宽泛GET/凭据逻辑。 |
| 普通单选语义/比较 | `D:/1800/src/annotation/quality/live_pilot.py:58–98,187–232,236–299` | 可复用纯判定原则：显式单选、一个A–D答案、四W顺序、严格内容/保全。生产facts注册表仍拒绝，`check_target`要求FAKE_BACKEND_READ+offline，不能改标签当live。 |
| 计划、日志与一次发送内核 | `D:/1800/src/annotation/delivery/live_pilot/plan.py`、`D:/1800/src/annotation/runtime/live_pilot/journal.py`、`runner.py` | 已有离线实现可在后续真实接线时复用结构；本阶段不调用apply/send/reconcile，不再重写一套内核。 |
| 真实Usense适配器 | `D:/1800/src/annotation/delivery/live_pilot/usense.py:14–34` | 当前`observe`、`build_commit`、`send_once`明确拒绝；没有可直接运行的已验证文字保存适配器。A05执行代码只在私有stage，固定报告明确不是共享应用，本草案未读它们。 |

已有路径（仅作为新guard的精确候选，当前有效性待本轮响应；未知参数不试探）：

- `GET /qieti/api/claim_book/books?page=1&pageSize=10&id=46007447`
- `GET /qieti/api/annotate_ocr/directory/get?file_id=46007447`
- `GET /qieti/api/annotate_pic/get_manual_annotations_unified/46007447`
- `GET /qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre`
- `GET /qieti/api/annotate_pic/pre_annotation/46007447?pageNum={14或173}&annotationType=mr_pre`
- `GET /qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/{固定现存非22题序}`
- `GET /qieti/api/annotate_pic/get_question_info/46007447/{同一题序}`
- `GET /qieti/api/verify_annotation/get-ocr-annotation?file_id=46007447&question_order={同一题序}&zone={经当前脚本确认的zone}`。旧代码还支持可选`image_order_in_annotation_zone`；是否需要以及取值只能从当前实现/返回推导，不额外枚举。

## 5. 保存与文字：已有静态字段、真实缺口

本次已核旧归档`D:/1800/技术证据/cached-js/index-CU_hexWN.js`为3,065,996 bytes，SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`，与A05 code-version相同。它不是当前页面版本，以下均标`HISTORICAL_CODE_ONLY`：

- 第66行 `E6e` 调用 `POST /qieti/api/annotate_pic/commit_unified_submit`；另有`commit_unified_submit_and_async_ocr`，后者不进入路线。这里只记录调用schema，POST均禁止。
- 第145行构造`annotations_upsert`，含`rect_id,type,belong_to_level,order_in_level,image_order_in_annotation_zone,rect_bbox,page_index,image_path,parent_rect_id,directory_id,content_type,is_pre_annotation,pre_annotations_id`；新题字段为`question_order=null,is_new_question_insertion=true,insert_after_order`，另有`target_directory_id`与删除字段。
- 第145行已看到非空`ocr_submissions`候选元素：`{zone,ocr_result,rect_ids,question_order}`。choice可能是一段聚合文字绑定多个rect_ids，不能假定四W各对应一个独立文字请求；当前选项次序/序列化及读回对应仍待证实。空文字或无clips会影响`ocr_delete_zones`，不得照搬该列表。
- 第141行角色包括`question/choice/answer/analysis/knowledge_point`；第142行题型枚举含`xuanze`与`duoxuan`，未见`danxuan`。正式普通单选字段仍须由当前代码和样题题型响应确认，不能凭字符串替代来源分类。
- 第66行内容GET为`get-ocr-annotation(file_id,question_order,zone,可选image_order_in_annotation_zone)`。实际返回文字字段、空值/未录入表示、rect_ids顺序、格式规范化和刷新/重开来源身份尚缺当前证据。
- 历史A05 commit确有业务成功及框重开，但`ocr_submissions=[]`、Q/A内容未找到，只证明两框；详见`D:/1800/docs/tasks/A05-execution-report.md:37–59`及`commit-preflight.json/commit-receipt.json`，不能升级为普通单选/文字保存通过。

接线的最少真实缺口为：当前前端版本与非空文字/W序列化适用性；完整当前target到A11 observation的decoder（包括空内容事实而非伪AVAILABLE）；真实facts/policy注册与session证据；实际上传/保存及非空文字业务结果；保存后独立刷新重开读回。前三项可由本轮只读取证推动纯离线接线，后两项只能由后续一次明确写入实测证明。

`global_order()`当前要求每个旧题`question_content.status=AVAILABLE`且有题型/parts（live_pilot.py:201–204）；旧A05 Q22曾无文字，本次不能假定它现在已补齐，更不能删除Q22、把真实空内容标AVAILABLE或放宽规则以凑ready。正式接线需把实际可证明的“缺内容/缺证据/已有文字”保全语义明确区分；本阶段如覆盖不全就保留PARTIAL，不为只读采集绕开生产门。

## 6. 一个独立验收阶段及最少交付

独立者使用同一个正式验收对话：准备期核公开规则和新GET范围；作者冻结并释放后只读固定raw，不再开第二平台会话。逐项核：

1. 新轮授权/TLS范围、次数与实际网络审计一致；A15未扩范围；未知请求/首失败/LOGIN_REQUIRED均没有后继。
2. 当前书、目录、题/框、两页source和原图真实绑定；计数、题序、页号、摘要由原始响应推导，完整与PARTIAL分开。
3. 当前脚本哈希、保存schema静态证据、内容实际GET响应和新decoder逐字段相符；不接受计划值冒充读回，不把历史缓存视为当前版本。
4. 从本轮两张原图独立读候选全文、四选项、C答案及目录，核Q/W/W/W/W/A与新题排除证据；若不够则只列实际缺口。
5. 原始失败、旧状态和精确自有释放保持；结论只覆盖当前只读取证和候选准备，不能写真实保存通过或生产READY。

执行最少一个证据包即可：固定代码/授权/网络与释放清单，`current-state.json`（字段带证据refs与覆盖状态）、两原图与映射、`wire-observation.json`（CURRENT_RESPONSE/CURRENT_CODE/HISTORICAL_CODE/UNKNOWN区分）、`first-question-draft.json`（六框/文字/答案/目录/新题排除及尚待批准项）、一份报告。独立交一份固定结论与问题清单；无需为五类事实分别建立正式任务。

调度的实际下一步：先在现有A15等待期间允许上述纯离线准备；A15固定收口后，明确A16新TLS边界和一次只读范围并一次性派发执行/验收。收到本包后就能围绕同一道普通单选做真实适配的有限离线接线与具体写入核准；不等B复杂题、不做全章、不重复网络诊断，也不把任何未知字段留给写入时猜测。
