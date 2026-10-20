# A16 R01–R04 修订版正式独立复核

**task=A16；result=REWORK**。新候选 `071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc`。R01、R03、R04在本候选的有限纯离线范围已核定修正；R02新增反例仍违反“不支持形态UNKNOWN、零样题请求”的门槛。本报告不给ACCEPTED_OFFLINE_ONLY、TLS批准或live资格。

产品 `cb26282a2340d2136c4db103a07391e593730cf9`；final `8ab0944116b5230b8e69c2f129b635435c243d55`；派发workflow `ed182f685db56be8b98d3d97782ee44ee71c0981`；产品授权workflow `f04c1579353de3fd2006b533d5c792c80190f5b8`。原final `4fe417d5`和原独立REWORK仍按原字节保留。

## 已确认的结果

| 检查 | 实际结果 |
|---|---|
| 输入/依赖 | 111raw逐一等于新final Git blob；候选19成员、交付104成员摘要相符；73byte父包初始化已包含 |
| 保全 | 31,259基线成员mode/type/blob保持；原39份A16证据保持；本修订100新增/5修改/0删除 |
| 新修订suite | **75/75 PASS，2484ms，shell exit0**；62个collect记录、23个补充记录；只发现test_*revision.py |
| 默认静态launcher | 自有子进程wait完成、exit0、stderr空；候选校验/严格TLS默认，无live参数 |
| 自编独立控制 | **12 PASS / 1 FAIL，219ms，shell exit1**；首个意外失败在最后一项，之后没有产品修正或重跑 |
| JS语法参照 | 两份新配对源码仅 `node --check`；有效文件exit0，reserved getter文件exit1；没有执行JS源码 |

证据：[preflight-result.json](preflight-result.json)、[revision-command-results.json](revision-command-results.json)、[revision-suite-raw/result.json](revision-suite-raw/result.json)、[revision-suite-raw/unittest.txt](revision-suite-raw/unittest.txt)、[independent-input-freeze.json](independent-input-freeze.json)、[independent-command-results.json](independent-command-results.json)、[independent-controls-result.json](independent-controls-result.json)。独立脚本和两份JS输入在运行前固定摘要；没有运行旧33项、旧候选独立反例、A15或更早suite，也未运行嵌套raw-checkout。

## 新发现：A16-R1-R02-01（P2，已复现）

定位 [js_wire.py第112行](../../../../src/annotation/source/usense/current_readonly/js_wire.py) 至119行，及第235行。lexer把所有符合字符形状的单词都标为`id`；function名、参数/局部绑定和调用名接受此kind，却未排除JS保留字。因而不属于声明型JS子集、根本无法解析的源码，也能得到具体getter/调用链“证明”。

配对输入 [native-fetch-valid.js](native-fetch-valid.js) 为新的字符串拼接URL、不同局部名称、不同zone调用顺序的native-fetch形态，实际collect正例通过，字段range及摘要逐一回到同一源码。反例 [reserved-getter-invalid.js](reserved-getter-invalid.js) 仅将frames getter及其调用名改为保留字`if`：

```javascript
async function if(b,n) { /* exact scoped GET/JSON body */ }
// corresponding caller uses: const fs = await if(b,n);
```

Node语法检查明确返回 `SyntaxError: Unexpected token 'if'`，见 [原始stderr](invalid-js-syntax.stderr.raw.txt)。该检查只解析，没有执行JS。

新产品的真实current_code→analyze_asset→functions/getter/call_chain→register_sample→collect→frame/content绑定路径却产生：

- `wire.status=CURRENT_CODE_CONFIRMED`、binding proof完整；
- 登记样题3，共11个合成业务GET，包括五个样题接口；
- question/choice/answer正文全部AVAILABLE；
- `outcome=READONLY_REVIEW`。

实际结果见 [reserved-getter-counterexample.actual.json](reserved-getter-counterexample.actual.json) 和独立`R2_RESERVED_GETTER_SYNTAX`。预期是不支持/无效源码保持UNKNOWN，只做六个原固定GET，不登记或请求样题，不产出AVAILABLE/KNOWN_EMPTY。

这是窄识别器自身的语法边界缺口，不要求把它扩展为通用JS解释器，也不要求支持axios或复杂bundle。需要验证支持位置上的合法绑定标识符/语法，保留字等无效输入应拒绝，并为相关getter/实参关系添加负例。独立不修产品；后续由调度安排本阶段新冻结交付。

复现边界：使用本新候选`CollectHarness`的合成传输、原图/UI与文件边界；实际parser、注册、collect、框和正文decoder被执行。没有调用浏览器、平台、真实GET或保存。当前平台脚本是否含这种形态未观察，不能据此推断真实平台已发生错误。

## R01–R04逐项结论

**R01：有限离线修正已核定。** 新75项涵盖相同ID的角色、zone、顺序、目录、页、bbox、父框、源图引用、缺字段/重复等反例及传输换序正例。额外独立控制确认：轮转单题列表可通过；可选显式zone在库存存在而当前缺失会在sample_frames失败，后续题型/正文NOT_RUN；源URL与附带digest冲突会拒绝；包装实际bound_content观察到三次正文均使用`frame_binding.frames`本次对象，而非初始库存对象。晚到answer守卫失败后，已读question/choice文字全部清为UNKNOWN/text=null，只发布sample-rejected，绝无sample-readback。

**R02：部分关联检查有效，仍REWORK。** 新正例已真正走collect，字段引用与asset/range/hash相符；错误响应字段、调用者shadow、跨资产拼接和顶层alias分别保持UNKNOWN、只有六个GET、无样题登记/正文。新75项另覆盖注释、无关函数、错误实参/response对象、缺接口、未知zone等。上述保留字反例突破了支持形态边界，不能把R02整体记为已关闭。

**R03：有限离线修正已核定。** 同一确切immutable bytes先load完整像素，再取尺寸/摘要和保存；独立31×43 JPEG与PNG正例通过，捕获到的写入bytes与输入完全相同。独立截去31个尾字节的JPEG header仍可读，但新original_once在任何writer调用前拒绝，没有重取，也未打开全局容忍截断。只支持单帧，未据此证明任何当前平台原图或UI映射。

**R04：有限纯桩修正已核定。** 独立8个fake API/held handle/Job/本地时钟控制覆盖：相同正整数pid/创建时间可RELEASED；bool pid、零/缺失/不同创建时间、前/后身份读取异常保持UNKNOWN且parent失败；身份/释放有效但worker输出错误时保留error，worker_succeeded仍false。句柄、stream、Job桩均关闭。这些不是实际OS Job/浏览器释放或自身退出证明。

具体依据与原48项受影响映射见 [revision-dispositions.json](revision-dispositions.json)。未变守卫/受限GET/三态内容等只沿用原有限证据，并逐段核字节未变；修改的关联、解码、释放、门禁由新75项及独立控制核定，未靠旧PASS。没有重标原C14–C16的NOT_RUN，也不宣称48项全部重新通过。

## 保全、资源及释放

原stdin编码打包SyntaxError、后续add记录、早期pending文档、新旧失败及清单均保留真实时点；原39份A16证据按Git原bytes校验。作者旧run01/run05磁盘摘要仍是摘要，完整旧聊天未读取，未将其改写为原始traceback。保全及限制见 [retained-limitations.json](retained-limitations.json)。

本轮0真实browser/network/profile/凭据/nativeAPI/占用扫描/登录/上传/OCR/业务/B消息；独立资源哨兵尝试表为空。Node仅语法检查；正常本地Python/Node工具子进程只记录自身pid、wait/exit，没有持有创建身份，不宣称OS身份退出或全机无进程。所有调用均已返回，没有浏览器、真实Job或native句柄待释放。

111raw未改，产品未修。报告/控制/清单只新增本目录，suite只写获准`independent-r1-01`；未读取作者活动目录、未修改D:/1800根任务或JSON。代码workflow已变，未来激活须绑定最终接受版本；当前没有TLS批准、activation或live。真实书/source/target/前端适用性及首题保存、内容/题框刷新重开读回均NOT_RUN；其他三例HOLD，Q22不重放。

固定机器结论 [review-result.json](review-result.json)，发现 [findings.json](findings.json)，保全 [final-preservation.json](final-preservation.json)，释放 [release.json](release.json)，清单 [raw-manifest.json](raw-manifest.json)。状态 **REWORK_RELEASED**。
