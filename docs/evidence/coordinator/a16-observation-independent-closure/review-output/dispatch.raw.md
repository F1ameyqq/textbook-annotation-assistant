# A16 只读观测版固定独立验收

2026-10-20。沿用正式独立对话 `01a15841-0d44-7272-9740-40d013839869`，host local，既有 xhigh/model 保持。这是 A16 同阶段范围缩减后的新固定候选，原作者已冻结释放；不新建重复聊天，不运行旧候选或恢复旧额度。

## 固定输入

- 产品 `dd22193a30e969aaf90043365f31f84a5a50df59`，final `2453c71c070c153a22a49b772bb2696b3858f5d4`，父版 `8ab0944116b5230b8e69c2f129b635435c243d55`。
- 候选 SHA256 `e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f`，范围调整 workflow `afed9807c77f33d5363d706d5341acb1fd172baf`。
- 交付清单 SHA256 `ae37099d56f8462db27145ce755ec5305fceafd9ebc14ead1a1c3cd966ba8622`；作者报告 SHA256 `55c1c75068f52447bb3579887819376cfc3d07ae10d8e0c5fc71307317a0cf92`。
- 新 raw 隔离目录 `D:/1800-worktrees/a16-observation-review`，由 final 原始 Git blobs 导出 59 个去重文件：50 个交付成员、交付清单自身、16 个依赖的并集。全差异为 48 新增、3 修改、0 删除；父包初始化原始 73 bytes 已含入。
- 调度输入清单 `D:/1800/docs/evidence/coordinator/a16-observation-delivery/input-raw-manifest.json`，SHA256 `2d64b70fc893868a517a2e9eafddb267f21fe657af49e3d27e67d9828048bc32`。
- 隔离内候选、计划、模板、作者报告位于 `docs/evidence/A16/current-readonly/revisions/observation-only/`。作者报告新工作树 18/18、468ms，raw 隔离 18/18、406ms；只是作者证据。

原第二次独立报告保持 REWORK，固定归档位于 `D:/1800/docs/evidence/coordinator/a16-revision-rework/review-output/`，manifest SHA256 `4f7d35c301412ea8877bb4ca1db94a74ea201003856b34417e47000a91735795`，REPORT SHA256 `0779d6030752e01824a6b129c1fc805c4822ce004aef0369eca0c47b05d59d92`。R01/R03/R04 仅有限离线控制通过；R02 仍未解决。本候选停用 R02 所在能力，不得把范围缩减重标为解析正确性修复。

## 集中复核范围

先核固定摘要、依赖及输入完整性，再集中检查本次三处产品改动及对应模板/结果。参考 `D:/1800/docs/tasks/A16-real-evidence-first-disposition.md`。0 浏览器、网络、profile、凭据、真实 native/占用、登录、业务或 B 消息。不得读活动作者/其他活动验收目录。

1. 样题能力确实关闭：实际 collect 不调用解析器确认接口；五个样题 GET 均被 policy 拒绝，`register_sample` 无条件拒绝，get_once 不能绕过；伪造确认信息、有效/无效/诱饵脚本都不能发样题请求。sample_limit=0，无启用开关；新题正文/schema UNKNOWN、样题 NOT_RUN、production_ready/write_eligible=false。
2. 当前事实仍可取得：六个固定业务 GET 各一次、两张绑定原图各一次，书46007447与viewer14/173不变；未知API、写方法、来源、WS、主导航/重定向、登录、身份、期限及晚到 guard 错误仍阻断。正常全量库存保留Q22，但不选择、导航或回放它。原同源 session/static 白名单不得扩大，也不混称全部HTTP只有8次。
3. 静态素材：仅保存本轮原获准同源 Script 响应 exact bytes/hash/source，在真实运行时只进入既定 `.local` 输出；不额外请求、不执行保存素材、不读取内联用户配置/storage/cookie/headers/profile。公共事件和结果不得含源码或敏感哨兵。正常页面执行已允许的脚本，与采集器执行保存代码区分。
4. 门禁、非执行模板、报告与 scope `CURRENT_BOOK_SOURCE_INVENTORY_STATIC_OBSERVATION_ONLY`、sample0、新workflow/候选摘要一致；旧scope或篡改字段、未批准TLS/缺失报告或期限均不能激活。本次仅纯桩/本地临时合成验证，不创建/访问真实activation、once标记或live目录。
5. 原31259基线与136旧A16证据保全；未修改的像素解码和释放身份代码准确引用上轮有限结论。依赖改变的行为要核实际新路径；不重跑旧33/75项、旧反例或A15及以前suite，不扩展通用JS解析器。

预检通过后，允许复现本候选新的 18 项 suite 一次，并构造与本次范围/安全变化直接相关的独立控制。正常准备不人为限制用例数；独立脚本和输入冻结后运行，首个意外失败保留并停止依赖后继，不改产品后重跑本轮。明确缺口交调度安排同阶段修订，不能自行补产品或启用样题。

固定命令参考：

`python -B tests/a16_current_readonly/run_observation_only.py --output docs/evidence/A16/current-readonly/revisions/observation-only/test-runs/independent-observation-01`

仅在新隔离顶层执行，不执行嵌套作者 raw-checkout。若检查默认静态 launcher，只能不带 live 参数，记录退出码；不得为释放证明扫描真实系统。

## 输出与结论

只在 `D:/1800-worktrees/a16-observation-review/docs/evidence/A16/independent-observation-review/` 新增独立控制/报告/清单；suite 输出仅限上述新的 `independent-observation-01/`。其余59输入 raw 不变，旧目录和证据不变。Git 先 `GIT_NO_LAZY_FETCH=1`，每条 `-c core.longpaths=true`，禁止隐式取对象。

提交固定报告、结论JSON、逐项依据、原始结果、manifest、输入保全和精确自有子进程wait/exit。未保留OS创建身份则如实说明；不声称观测自身OS退出。原Windows glob诊断及全部前轮失败保留，不把本次相关通过扩展为全面回归或真实平台通过。

结论限 `ACCEPTED_OFFLINE_OBSERVATION_ONLY` 或 REWORK。若有限通过，提供匹配新候选非执行模板的正式预检结果；实际 A16 TLS 决定和 activation 仍由调度在核证后落实，本轮不生成可执行批准。不以无关材料延迟收口。

下一依赖为正式独立固定交付及调度核证，再落实具体本轮 TLS 例外决定与一次真实观测。A15例外不转移；首题真实保存/内容与题框刷新重开读回均未运行。
