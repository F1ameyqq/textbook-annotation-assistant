# A15：已批准的一次证书例外只读复用

2026-10-20。用户对[固定提案](A15-certificate-exception-observation-proposal.md)明确回复“批准这一新有界只读阶段”。批准记录见 `docs/approvals/A15-certificate-exception-user-decision.json`，提案raw SHA256 `eb6aea7ad9b01ccbcaf7710c9c45d7c5c3a80d6efcef4db857838d204d725656`。这是新A15额度，不恢复A13/A14或任何旧候选/suite。

先完成A14独立有限收口，再正式派发本任务。分别新建执行/独立验收对话，xhigh/model沿用，确切ID/host/cursor以调度JSON为准。**先离线候选与独立预检，后调度固定live激活记录，最后同一执行/验收对话串行处理唯一live及结果。** 任何离线通过都不允许作者自行启动平台。

## 固定起点与写入范围

起点为A12-R1 final `81fab23e3e7e9e32a36d3857a253afc69b5bd3e1`，产品 `d45ed25a98361002ddb28985c1d27687c4421a17`；原工具raw SHA256 `3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9`。

新分支 `codex/a15-cert-reuse`，工作目录 `D:/1800-worktrees/a15-cert-reuse`。仅新增：

- `tools/headless_cert_exception_reuse_probe.py`：有限派生候选，保留R1原文件不变。
- `tools/a15_cert_exception_gate_delta.py`：新批准门禁纯离线差量。
- `tools/a15_observation_launcher.py`：仅供后续固定live的外层精确Popen记录器；本准备阶段不启动。
- `docs/evidence/A15/certificate-exception/`：候选/交付清单、批准及权威任务raw快照、静态差量、唯一离线原始结果、报告和释放。所有其他旧Git成员mode/type/blob必须原样保全。

不得修改主线、R1或其他旧工具、根依赖、浏览器/profile/代理/系统信任；不访问网络或扫描真实进程占用。作者不会因准备任务而得到真实profile读取权限。

## 新候选和批准门禁

最多1冻结候选。派生实现默认保留严格证书校验；仅用户本次批准+调度live激活记录共同匹配时，本轮专用context可启用 `ignore_https_errors=True`。不更改日常Edge、系统、默认参数或域名；不能将证书里的域名作为新目标。

激活记录由主调度在独立预检通过后另行生成，作者准备阶段只有合成样例。记录须绑定：

1. A15任务、固定用户决定SHA、原提案SHA及本轮候选清单SHA；
2. 调度对话ID `01a15768-1e2d-7781-b29f-1f7376270216`、固定run_id；
3. 唯一目标 `https://www.usense.com/qieti/annotateUnified`、显式证书例外true；
4. 原专用profile的非敏感指纹、唯一新输出 `D:/1800/.local/stages/a15-cert-reuse-live`；
5. 至多1次context/导航、0登录提交/业务写入，not_before/expires_at UTC（实际派发窗口15分钟）。

live CLI须显式传证书例外开关、激活文件及其预期SHA；缺失、摘要/字段/目标/额度/时间不匹配均在浏览器/profile/占用/网络前拒绝。旧默认CLI仍不能启动live。激活和一次性领取不得以任意命令行替代字段，不能默认为批准。正式一次性标记仅在获准派发后创建；原A13标记不清除。准备阶段只用合成目录和指纹。

保留R1逐跳/方法/WS/子target守卫、同源静态与session只读允许范围、缓存和service worker限制、profile绑定与占用、错误首因、DOM后最终guard判定、Job与自有资源释放；除明确批准门禁/新路径/本轮证书例外所需差量外不得重构。给出对R1的逐项raw差量及理由，独立据此审查。

## 唯一纯离线差量

冻结候选后作者仅1轮，独立后续仅1轮，0子进程/browser/network/profile/真实占用：

- E1：未批准/未显式启用时拒绝，默认保持严格校验。
- E2：固定清单中的错绑定、过期或额度不符拒绝；具体有限变体和预期在冻结前写入，不临时扩矩阵。
- E3：匹配的合成批准只领取一次合成标记，证书例外仅在该合成授权结果中为true。
- E4：再次领取拒绝，原标记bytes不变。

使用纯函数和新临时合成目录，不调用live入口、Playwright或launcher。测试必须证明拒绝先于任何真实资源动作，不把合成通过称为平台通过。原N1-N3、D1-D8及旧成功任务不重跑；首异常停、后继NOT_RUN；冻结后不得修补重跑或自动第二候选。

作者交付固定产品commit/final commit、raw清单、唯一实际离线结果、旧成员保全、静态差量、精确零资源/释放说明后停止REVIEW。独立固定隔离预检与调度核证后才能另派本次唯一live。

## 后续live仍须另获固定派发

最多1个新context/1次导航，复用原专用登录态，0登录提交、0目标书业务写入。激活绑定后才读取非敏感profile元数据，实际占用仅由固定产品一次检查；冲突/未知即停，不清锁、换profile或结束他人进程。

导航45秒、worker75秒、产品外层85秒、外层观察总90秒内收口；各进程各用自身起点与绝对截止，不比较未经证明的跨进程perf_counter值。外层保留创建身份、退出码与句柄；未证明的wrapper自身退出身份如实UNKNOWN，不扩大释放结论。禁止批量kill或只关句柄却把仍运行进程称作已释放。

结果只列AUTHENTICATED_VIEWER、LOGIN_REQUIRED或首错误，以及源/书/保存尚未证明项。认证状态也必须在DOM异步结束后核guard最终状态；失败后后继NOT_RUN，无第二轮、无换参数重试。作者固定本轮raw与自有释放后，独立只读核该结果，0再访问平台。

本任务不授权首题写入。下一依赖仍是书46007447当前认证源/目标、具体新普通单选题、平台政策和次数；之后首题保存及内容/题框刷新重开独立读回，通过后总量最多5题。其他三例HOLD、Q22不重放、0B消息、无书级送审送交，截止仍2026-10-22日晚。
