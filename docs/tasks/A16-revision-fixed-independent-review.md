# A16 R01–R04 修订版固定独立复核

2026-10-20。沿用正式独立对话 `01a15841-0d44-7272-9740-40d013839869`，host local、既有 xhigh/model 保持。本次是 A16 同阶段修订复核，不创建新聊天，不重开旧任务或恢复已耗额度。原执行已冻结并释放。

## 固定输入

- 产品 `cb26282a2340d2136c4db103a07391e593730cf9`；final `8ab0944116b5230b8e69c2f129b635435c243d55`。
- 前版 final `4fe417d5246f20fbbbedc577495c7ca400d4ded8`；基线 `7432122b9fd5602785ebfb2b3f24e407fdf76eda`。原产品/验收结果仍 REWORK。
- 新 raw 隔离目录 `D:/1800-worktrees/a16-r1-review`，由新 final 原始 Git blobs 导出，111 个去重文件。104 个增改清单成员、清单自身及 19 个候选依赖的并集；父包初始化文件已包含。
- 调度输入清单：`D:/1800/docs/evidence/coordinator/a16-revision-delivery/input-raw-manifest.json`，SHA256 `35d82218dd9c39db340b9d78f2dce4801af430db92e5c2e3ca6738f9b9bf4562`。
- 新交付清单 SHA256 `91d126dcd7204f71bedc3e9b3ca64a84421c536da177376b5a92c36a35ed5c59`；候选清单 SHA256 `071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc`；作者报告 SHA256 `4607e8333e552f1a843c3486616871c7f3bb5498be7d03776d3e1ce7f4d77918`。
- 报告/候选/交付清单位于新隔离内 `docs/evidence/A16/current-readonly/revisions/frame-binding-r1/`。原正式报告及反例已在该版本 `authority/independent-fixed/` 按原 bytes 收入。原准备包、前版隔离目录仅作固定只读参考，不在原目录新增输出。

先核以上固定摘要、候选依赖及隔离完整性，再复核修订。可从固定 Git 版本只读核原基线、原证据和改动范围，不读作者活动目录，不自动补取任意依赖或隐式 lazy fetch。Git 先设 `GIT_NO_LAZY_FETCH=1`，每条 `-c core.longpaths=true`。

## 本轮验证重点

沿用原 48 项准备标准及首轮已明确的有限证据，集中验证 R01–R04 和实际受影响的行为，不重新执行旧 33 项 suite、旧独立原候选反例或 A15 及以前 suite。未变行为可以准确引用原有限证据；修改过的候选/门禁不得只靠原 PASS。

1. R01：真实 collect 合成链逐字段绑定当前单题框与完整库存，在后继正文请求前拒绝同 ID 的角色/zone/顺序/目录/页/几何/父框等冲突及缺失、重复；允许仅列表传输顺序改变；正文确实使用本次验证框，晚到守卫失败不得留下可接受正文状态。
2. R02：独立检查具体 getter、调用实参/zone、对应响应对象和字段引用的来源关系；为词汇共现、相邻注释、无关函数、错误实参、错误响应对象、部分接口及不支持形态构造必要反例。不能只重复作者给定的 true/false。未知不得注册或请求样题接口、不得输出 AVAILABLE/KNOWN_EMPTY；支持形态正例也须真实走 collect。明确窄识别器适用范围与实际平台尚未验证，不能以支持合成 native fetch 宣称适用于当前前端。
3. R03：同一确切 bytes 完整像素解码、尺寸/摘要/保存相符；有效图片正例和 header 可读但 JPEG 残缺负例；拒绝发生在保存前，无全局容忍截断或重取。
4. R04：纯桩验证有效且相同的 pid/创建时间才可 RELEASED；缺失、失配或身份检查错误保持 UNKNOWN；父层错误不丢失。明确这不是实际 OS 释放证明。

可在预检通过后复现本新候选的 75 项修订 suite，并执行自编的相关独立控制；不人为限定正常准备中的用例数量。冻结本轮独立测试输入/脚本后再运行，首个意外失败保留并停止依赖后继，不改产品或修后重跑本轮；确有产品缺口交调度安排同阶段新交付。

修订 suite 的固定入口为 `tests/a16_current_readonly/run_offline.py`，其 discovery 仅 `test_*revision.py`。仅允许 `--output` 指向新隔离内 `docs/evidence/A16/current-readonly/revisions/frame-binding-r1/test-runs/independent-r1-01/`，该目录必须此前不存在。若复现默认静态 launcher，仅不带 live 参数，记录 shell 结果与自有子进程 wait；默认静态路径不应触碰真实 native/profile。

## 输出、资源与结论

本独立报告、自编控制和清单仅新增于 `D:/1800-worktrees/a16-r1-review/docs/evidence/A16/independent-r1-review/`；上述 suite 输出另列白名单。其余 111 raw 冻结成员不可修改。直接在新隔离顶层源码运行，不运行作者嵌套 raw-checkout 内的副本。

0 浏览器/网络/profile/凭据/真实 native API/实际占用扫描/登录/上传/OCR/业务/B消息。仅本轮纯离线测试和正常本地工具子进程；精确记录自己创建的子进程 wait/exit，未保留创建身份则如实说明。不能为证明释放扫描全机或声称观测自身 OS 退出。原 stdin 编码打包失败、后续 add、早期 pending 文档及所有新旧失败均保留其真实时点，不冒称无失败。

交固定结论 JSON/报告、逐项依据、原始结果、清单、输入保全和释放。结论限 `ACCEPTED_OFFLINE_ONLY` 或 REWORK，并绑定本候选 SHA；作者 75/75 仅作输入，不能替代独立判断。正常证据充分后直接交付，不以补齐无关材料扩大范围或延后收口。

没有 A16 TLS 批准和 live activation，不运行模板。新模板 workflow 已变为本修订依据 `f04c1579353de3fd2006b533d5c792c80190f5b8`，将来激活须按最终接受的代码重新绑定；旧 TLS 草案不能直接使用。书/源/目标/接口的真实适用性及首题保存、内容/题框刷新重开读回均仍 NOT_RUN。
