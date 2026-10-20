# A16 待激活的合并只读方案

本包状态为 **REVIEW / OFFLINE_ONLY**。当前 live 未激活，未读取 profile、凭据或真实进程占用；没有浏览器、平台请求、登录、业务保存、上传、OCR、送审或 B 消息。作者不作独立验收或调度激活。

固定书为 46007447，viewer 仅 14、173；专用 context 最多 1，主导航最多 1，整轮及释放总上限 900 秒。launcher、product、worker 各自使用自身 monotonic 时钟，不跨进程比较 monotonic 值。绝对 UTC 激活期限在每层重核，各层把当时剩余时间转换到自己的 monotonic 截止；到期只清理自有 Job/持有句柄，不清锁、不扫描或终止其他浏览器。

## 激活前提及 TLS 决定

1. 固定本包 candidate-manifest 的 SHA256、独立报告 raw SHA256 与确切执行对话。独立报告须给出 `task=A16`、同一 `candidate_manifest_sha256` 和 `result=ACCEPTED_OFFLINE_ONLY`。
2. 由调度落实 A16 的具体决定文件：`task=A16`、本包 `run_id`、`live_authorized=true`、`tls_mode=STRICT` 及 `certificate_exception_authorized=false`。严格 TLS 为默认；若需要本次 context 例外，应先取得明确覆盖本次 A16 的用户决定，文件改为 `CONTEXT_EXCEPTION/true`，CLI 必须同时显式给出 `--certificate-exception`。代码不创建、推断或复用这份决定。
3. 新 activation 绑定上述两份文件的原字节摘要、本包摘要、workflow、executor/coordinator、run_id、书、页、目标、原专用 profile 指纹、唯一新输出及不超过 15 分钟的有效期。A15 的 schema、decision、候选、run_id、输出与标记均不匹配。示意模板故意含 null，不是 activation。
4. 只有获准后才核实际专用 profile 元数据与既有指纹，执行一次有界占用检查。profile 锁存在或身份不符即停止，不清锁或替换 profile。原 profile 内容不导出。正式 activation 固定位置为 `D:/1800/.local/stages/a16-current-readonly-activation.json`，唯一输出为 `D:/1800/.local/stages/a16-current-readonly-live`，排他创建的任何标记均消耗该轮，失败不能重发或改目录。

## 读取顺序与白名单

主导航只允许 `https://www.usense.com/qieti/annotateUnified`；第二次主导航、主文档重定向、子 target、WS、写方法、未知 API/跨域请求或守卫异常均停止。service worker 禁用。保留当前 session 的三项同源 GET（profile、permissions、teams），响应中的账号及认证值不输出。

`policy.FIXED` 固定六个业务 GET：书列表中的 id=46007447；该书完整目录；该书全量手工框；该书 source 元数据；viewer14、173 各一个 pre_annotation。每个规范化 URL 至多发送一次。查询参数换序、重复键或另一页/书不能增加额度。若 UI 已发送获准 GET，采集器等其首次响应，超时停止；不会再取一次。

源图只能由该书当前单页响应注册。读取原响应中的 page_index，不能计算 viewer-1。URL 仅允许已固定同源或 OSS 的 `/upload_images/46007447/` 路径，不能含查询、凭据或重定向。两个原图各一次，通过同一页面/native guard 取字节，核真实尺寸与 SHA256。仅使用 `.section-title input` 跳至规定页，并核 Vue 资源 props、canvas 绘制及当前书。UI 复用精确已捕获的响应时由 context 或 Fetch 直接返回相同内存字节，记录 `LOCAL_CAPTURE_REUSE/NO_NETWORK_*`，不再发网络 GET；不合成正文或图像。仅沿用原响应的安全 CORS 头，不添加原响应没有的权限。

保存同轮实际加载的同源 Script 响应 bytes/hash。静态 token 及调用上下文定位只构成 `CURRENT_CODE_ONLY`；缺少 GET 参数/zone 证据则不登记样题 API。按当前题序选择首个非22、四个 choice 框且索引 0..3 的现存样题，至多一个。当前代码证实后才登记该题框、题型以及 question/choice/answer 三个内容 GET，合计最多新增五个固定 GET。0 循环枚举、0 保存/上传/签名/异步 OCR 调用。无样题或代码不明时记缺口，不换目标。

已批准 API 或原图的重定向、重复且未完成的 UI 请求、身份冲突及非成功业务响应仍停止。外部未注册 **Image/Font/Media** 在首次请求阶段拒绝、零发送，单独记 `EXPECTED_PASSIVE_DENIAL` 后可继续；不适用于 Document、Script、Stylesheet、XHR、Fetch、WS、重定向或写方法。URL 畸形仍是致命失败。网络审计只留 scheme/hostname/port、资源类型、守卫类别和导航/业务关联；没有 query 值、路径、账号、cookie、token 或 Authorization。公共源图证据只投影已验证的 upload_images/book URL 与源页字段，和网络审计分开保存。

## 结果及首题边界

目录/题身份/全书题序/框只有在完整响应、书计数对账、无孤立或错绑框时才为 FULL，否则 PARTIAL，不能形成追加顺序。Q22 在正常全量库存保留，不导航、不重放、不选作样题。全书正文保持 UNKNOWN；即使一题全部读取，其覆盖也只有 PARTIAL，不能作为后续写前保全基线。

内容只有当前成功字段且 rect_ids 与该 zone 的当前框及顺序相符时才为 AVAILABLE 或 KNOWN_EMPTY。`success=false/未找到`、未读取、字段或来源未知一律 UNKNOWN。choice 聚合文字可以绑定四个 rect_ids；不假定四 W 必须有四段单独响应。

仅准备第2节《一定是直角三角形吗》基础题印刷第1题，角色 Q/W/W/W/W/A，四 W 为 A→D，历史答案 C。`first-question-draft.json` 的图片、转录及 bbox 全是作者查看归档原图后的历史草稿。当前目录、新题身份、来源、正文标点、六框和与现有题的内容/几何重复排除均待本轮之后对当前原图独立复核；不会自动发布 READY。候选重叠或来源不清即 HOLD，不在本轮换题。

首真实异常或 LOGIN_REQUIRED 保留首错，后继 NOT_RUN。释放后交 current-state、源图/映射、script bytes/hash、wire observation、样题读回和精确释放。0 业务发送实现。首题真实保存及内容/题框刷新重开读回仍 NOT_RUN；该门槛通过后才考虑总量最多5题，其他三例 HOLD。

## 离线复现及限制

在本工作树运行：

```powershell
python -B tests/a16_current_readonly/run_offline.py --output docs/evidence/A16/current-readonly/test-runs/reviewer-new
python -B tools/a16_current_state_launcher.py
```

第一条只运行 A16 新的合成 suite，输出必须是新的 A16 证据子目录；第二条只核候选 bytes。没有执行任何旧 suite。live 命令不在离线复现中运行。

当前页面结构、实际 GET 形态、样题正文响应、OSS CORS 与双重路由的真实运行适配均未获 live 证明；差异须停止归档，不在活动轮中修驱动或补取。没有读取实际占用，因此不声称当前 profile 空闲；没有启动真实资源，因此本次无浏览器/Job/native 句柄待释放。测试进程正常退出的 OS 事实由 shell 回执记录，作者不伪称观测自身退出身份。

native 支持从本包 `dependencies/a15_native_reference.py` 导入；该文件逐字节等于基线 A15 工具的 Git blob，导入后只明确重定位模块 ROOT/EVIDENCE，供既有 guard/Job/释放和审定 native 计数器使用。不调用旧 main、candidate、suite 或 live。工作树中旧工具的 CRLF 与 Git LF 差异已保留于 raw-index-finding 和原候选清单；旧路径未修改。独立隔离与未来部署应从 Git raw blobs 导出本包成员，普通 Windows 检出若转换 py 换行将被候选门禁拒绝，不由产品静默归一化。
