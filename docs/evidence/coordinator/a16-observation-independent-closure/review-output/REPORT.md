# A16 只读观测版正式独立验收

**result=ACCEPTED_OFFLINE_ONLY**；有限范围标签 **ACCEPTED_OFFLINE_OBSERVATION_ONLY**。

`task=A16`，候选 `e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f`，scope `CURRENT_BOOK_SOURCE_INVENTORY_STATIC_OBSERVATION_ONLY`，sample_limit=0、automatic_schema_confirmation=false、固定业务GET6、原图GET2。机器结果按调度补充口径与固定gate/template使用相同枚举，全部有限scope字段共同绑定；这不是一般A16/schema/平台接受。

产品 `dd22193a30e969aaf90043365f31f84a5a50df59`，final `2453c71c070c153a22a49b772bb2696b3858f5d4`；派发workflow `988a72998b4b6d8f293f21a96056db1343ceecb8`，产品范围workflow `afed9807c77f33d5363d706d5341acb1fd172baf`。

## 实际证据

| 项目 | 结果 |
|---|---|
| 固定输入 | 59raw逐一与final Git blob一致；候选16依赖、交付50成员摘要匹配；父包初始化原始73bytes已含 |
| 保全 | 31,259前A16基线成员、136份旧A16证据mode/type/blob保持；48新增/3修改/0删除，三处仅gate/policy/probe |
| 新suite | **18/18 PASS，500ms，shell exit0**，8份新case记录；仅发现test_observation_only.py |
| 独立控制 | **9组全通过，250ms，shell exit0**；首意外失败null，真实资源尝试表、解析/资格调用表均为空 |
| 默认launcher | STATIC_ONLY，新候选摘要匹配，ignore_https_errors=false，resources_created=false；自有子进程wait完成、exit0、stderr空 |

原始证据：[preflight-result.json](preflight-result.json)、[input-raw-manifest.independent.json](input-raw-manifest.independent.json)、[fixed-command-results.json](fixed-command-results.json)、[suite-raw/result.json](suite-raw/result.json)、[suite-raw/unittest.txt](suite-raw/unittest.txt)、[independent-input-freeze.json](independent-input-freeze.json)、[controls-command-result.json](controls-command-result.json)、[independent-controls-result.json](independent-controls-result.json)。只运行这个新18项suite和直接相关新控制，未执行嵌套raw-checkout、旧33/75、旧独立反例或A15及以前suite。

## 集中核定

**样题确实关闭。** register_sample对bool、伪造完整proof、CURRENT_CODE_CONFIRMED、scope/sample1标志等无条件拒绝，登记状态不变。五个请求在三个路径族中硬拒绝，发生在business/original映射之前。独立在q3/q22各路径同时伪造business登记、original映射和成功cache，get_once仍先经过实际policy拒绝，page.evaluate零调用。native paused和context route也分别验证发送前fail/abort，sent为空，不continue、不fulfill；没有可用启用开关。

**实际collect不再资格判定。** 三组新合成资产（无效/任意bytes、普通函数、词汇诱饵），额外伪造schema/proof/sample1元数据，都只产生原六固定GET、viewer14/173原图各一步和相应映射。解析器、evidenced_paths、样题选择/登记均装拒绝桩，未触发。Q22自然保留在完整合成库存，不选择/导航/重放；样题步骤全NOT_RUN，正文/schema UNKNOWN，production_ready/write_eligible和写前保全基线均false。这里的FULL仅限完整合成库存，不是当前平台事实。

**受限请求未扩大。** 实际CurrentGuard.capture捕获六份固定业务响应原bytes，get_once从缓存逐项取得对应body，未再evaluate或重发；错书、viewer15、未知API、写方法拒绝。scope仍是书46007447、viewer14/173、单context/主导航/900秒的既定候选。原同源session/static辅助资源范围未扩大；“六个业务GET+两原图”不表示全部HTTP最多8次。逐跳、WS/子target、占用、登录、源身份/时限及原图/释放方法未变部分已逐段核源码一致，准确沿用原有限结论，没有重跑旧suite或冒称live通过。

**静态脚本仅作为素材。** 独立两份不同同源Script响应含CRLF、非UTF8、NUL和敏感合成哨兵，真实capture写出的.bin与输入exact bytes相等，SHA/长度相符；来源sidecar的原URL及URL SHA相符。重复捕获不增加同一URL资产。公共public_assets/events只带引用、摘要、长度和脱敏来源，未包含bytes、完整URL、set-cookie或哨兵；采集器未evaluate、执行或解析资产。独立同时验证未知跨域、带query、API/profile、非Script、POST和样题响应不读body、不入cache或scripts，401静态响应在读body前停止。

真实资产保存位置仍被代码约束到固定本轮 `.local` 输出，私有原URL sidecar不进入公共事件；本次没有访问真实该目录。离线验证只把LIVE_OUT替换到本报告目录的明确合成子目录；本包所有.bin均为合成数据，没有真实平台代码。正常页面加载允许脚本的行为，与采集器执行所保存数据区分。本接受也不证明素材覆盖全部前端或其schema适用性。

**失败边界保持。** 固定source读取失败后页/原图/映射/样题后继NOT_RUN，已观察库存可保留；晚到最终guard错误将观测判为ERROR，样题仍NOT_RUN，schema/body和写入资格不被升级。18项及独立控制通过，不代表首题内容、目录、几何、payload或保存可执行。

**门禁和模板绑定新的有限能力。** 三份非执行模板逐项匹配task/run/workflow/candidate/scope/sample0/auto=false/count6+2。内存合成严格TLS正例通过；对activation、decision、report逐一篡改旧scope、workflow、候选、sample1、自动schema或扩大count均拒绝，另覆盖缺scope、False冒充整数0、无live批准、未覆盖TLS例外及有效期边界。这里只操作内存值，不创建/读取真实activation、decision、once标记、profile或live输出。正式 [review-result.json](review-result.json)保留模板所需的ACCEPTED_OFFLINE_ONLY，并明确有限scope；它只是离线预检报告，不是TLS决定或可执行activation。

逐项检查、实际证据和边界见 [scope-checks.json](scope-checks.json)。没有发现本次缩减范围内的新阻断缺口。

## 原结论与接受边界

**原R02仍REWORK，未重标为修复。** 自研解析器源码保留但本collect不调用，它的先前误判没有被本次测试“修好”。原R01/R03/R04只保留前版已核定的有限离线控制：本次未变的完整像素解码、精确身份释放等经固定源码一致性复核后引用，不延伸为真实原图、浏览器或OS证明。

原报告manifest `4f7d35c3…1735795`、REPORT `0779d603…5d59d92`已按任务给定固定归档核hash。所有前轮REWORK、原C14–C16 NOT_RUN、Windows glob/编码打包/导入失败与早期pending记录保持原时点；未将摘要写成原始traceback、未把历史失败改PASS。

书/source/target/当前认证/实际前端适用性仍未观测；正文/schema UNKNOWN，新题当前未录入证明、末级目录和六框批准尚缺。首题真实保存、内容及题框刷新重开读回均 **NOT_RUN**；其他三例HOLD、Q22不重放。

## 交付及释放

本次0真实browser/network/profile/凭据/nativeAPI/占用扫描/登录/上传/OCR/业务/B或其他聊天消息。只有正常本地Python/Git工具和自有三个验证子进程；wait/exit结果明确，没有持有OS创建身份，不声称观测自身OS退出或全机无进程。无真实会话、Job或native句柄待释放。

59raw在交付前再核原bytes。没有修产品、改根任务/JSON、读作者或其他活动验收目录；只新增本报告目录及获准的新suite输出。报告中的实证素材、case和声明范围固定后交付，不继续增加无关测试。

结论 [review-result.json](review-result.json)，释放 [release.json](release.json)，保全 [final-preservation.json](final-preservation.json)，原字节清单 [raw-manifest.json](raw-manifest.json)，边界保留 [retained-boundaries.json](retained-boundaries.json)。状态 **ACCEPTED_OFFLINE_OBSERVATION_ONLY_RELEASED**。

下一依赖：调度核固定报告/清单/释放后落实本次具体TLS决定，再独立绑定新候选和一次真实观测。A15例外不转移，本轮没有A16 TLS批准、live activation或业务写入批准。
