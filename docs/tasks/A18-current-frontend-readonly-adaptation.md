# A18 当前前端与书源读取适配

调度依据用户“不要太保守”“尽快推进”“先真实验证再调整”以及TLS“一直批准”的持续许可，安排新的必要只读适配。此阶段分别新建正式执行和独立验收对话，xhigh/model沿用；A17及所有旧额度不恢复。不是再次修改A17或重放旧驱动。

基线为已释放的A17实际交付5aec24575a0e1621f4f22680da3beba581e6cec2。A17在一次CDN预期拒绝后，被同源GET XHR PATH_BLOCKED停止，实际六GET/两原图均0；其失败、未知路径和已证释放原件保留。当前有一份真实同源前端Script，仅在受控.local；SHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41，3065996字节。不能把候选端点当作本次被拒绝路径。

## 最小工程范围

复用现有gate/policy/probe/launcher与精确自有释放，不另造浏览器业务系统。完成以下集中适配，不继续造通用JavaScript解析器：

1. 将已观察的同源GET XHR路径拒绝，在明确条件下作为可继续的预期拒绝：仅原主框、无重定向、严格规范化的原站HTTPS、GET、XHR或Fetch，且原规则仅因PATH_BLOCKED拒绝。HTTP仍拒绝发送，不放行未知URL或宣称它非必要。API_BLOCKED、已知六GET路径参数/书ID不符、样题、login/logout/signin/user_login等受保护路径、导航、其他origin、方法、WS、身份缺失、歧义URL仍硬停止。处理顺序必须让硬停止优先。不得将所有PATH_BLOCKED无条件降级。
2. 与既有CDN预期拒绝共用全轮16次排除事件额度，await前记账，双层重复保守计两次；第17个仍拒绝并fatal。不单独额外增16次。拒绝异常、原本应拒请求出现响应、晚到fatal、context/native回调未结清必须进入最终ERROR/UNKNOWN。保留真实原始首因，报告细微归因残留可按已通过的实践处置保留限制。
3. 本轮新拒绝诊断保留可用的脱敏端点证据，不能只保留host再丢失路径。仅保留经过明确安全规则的路径模板/不可逆路径hash、已知路由名、query参数名（值全部省略）、方法/资源类型/层/拒绝原因；含疑似凭据或不可信动态段则模板化或只留hash。禁止输出完整URL、query值、headers、cookie、token或profile。不建立新的网络探测程序。
4. 只读核已捕获前端Script的实际调用关系，记录与六固定业务GET、当前目录/框库存/页映射相关的接口证据与bytes offset。素材不执行、不重新请求、不复制Git。参考辅助分析但独立核对有影响的具体片段。发现现有六GET必须修正的当前前端参数时，须具体列出endpoint/参数关系与已捕获源码依据，并在冻结方案中由独立核实；不顺手放行新API。正文读取/保存函数可以做首题接线准备，但本轮sample0、0发送/业务不变。
5. 已捕获源码证明启动版本检查：mount后fEt→ED({initialize:true})→uEt，GET `/qieti/version.json`、唯一query键`t`由Date.now()生成、cache=no-store、只读JSON。端点常量bytes offset3064125、fetch3064330。本阶段可具体准入该静态版本GET一次，严格限制原站/原主框/非重定向/Fetch或XHR、精确路径和唯一数值时间戳参数；不得泛化JSON路径或允许额外参数。重复版本检查继续拒绝，并计入同一个16事件排除预算。版本变化可能触发location.reload，仍必须阻止第二次主导航。本次XHR阻断路径未知，不能把version.json冒充已证首错路径。正文GET包装wy和统一保存E6e仅作为后续接线线索，不授权调用。

允许必要的新离线开发与针对改动的纯内存fake transport测试，失败保留；不人为套一候选/一次开发测试上限，也不重跑旧30/34/11/其他旧suite。独立只核实际安全边界和正确事实，不为历史NOT_RUN刷分。补充负例要能覆盖上述硬停止与双层计数/晚到fatal，避免大规模无关回归。

## 新真实轮的具体范围

当前先离线开发/预检，0browser/network/profile/凭据/真实native/占用。冻结且独立有限接受、调度核证后再绑定本阶段activation，最多新增1context/1导航/900秒含释放、六固定业务GET及viewer14/173两原图各最多一次，增加已证版本静态GET至多1次；sample0、0登录提交/业务写入/上传/OCR/送交。除上述精确version.json外原session/static范围不扩大；总HTTP不混称8次。

用户“一直批准”已记录于D:/1800/docs/approvals/A17-excluded-static-user-decision.json，SHA f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46。同类原专用context临时TLS例外可沿用该持续许可，不再向用户重复询问；A18必须创建自己明确的决定引用、scope/run_id/候选/workflow/正式机器报告及activation/输出路径，不能让旧A17激活对象通过。实际新轮未激活前不能启动。一次新真实轮失败不自动再试、延期、换输出或清标记。

原专用profile非敏感指纹b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00保持，保留Edge/profile、不复制凭据/换profile/清锁/批量kill。真实轮只用既有产品的精确自有释放。TLS仅专用context，主站和已批准OSS受影响，不改全局/默认配置、不加新来源。

## 交付与验收

新代码/相关离线证据和候选统一使用A18身份；旧所有成员、冻结证据、失败和原始源码保全。最终交付产品commit、final、原bytes清单、实际新差量结果、计划、适用许可及限制、精确释放。未知项如实UNKNOWN，不补造PASS。固定交付释放后由调度导出新raw隔离给正式独立；验收不读活动作者目录，不改产品，不重跑旧suite。

通过预检后同一执行/独立对话承接已固定的一次真实轮和实际结果核证，不把书/目录/图/接口再拆诊断阶段。目的是取得当前书46007447真实事实；普通单选候选仍第2节《一定是直角三角形吗》基础印刷1、四组数1,2,3/2,3,4/3,4,5/4,5,6，历史答案C、Q/W/W/W/W/A；当前未录入/目录/准确bbox待核，不沿用旧批准或换题。

库存区分AVAILABLE/KNOWN_EMPTY/UNKNOWN与FULL/PARTIAL/UNKNOWN。仅捕获脚本不证明认证或正文/schema；sample0、自动schema停用、write_eligible/production_ready=false、原R02未修保持。自然全量库存保留Q22但不导航/样题/重放。其他三例HOLD、0B/外部联系人消息、无书级提交。当前书源事实一旦取得，集中进入下一正式首题真实接线/具体政策次数及保存、内容/题框刷新重开独立读回，再最多5题，2026-10-22日晚目标不变。


## 正式执行位置与身份

作者工作区 `D:/1800-worktrees/a18-current-frontend`，分支 `codex/a18-current-frontend`，已由调度从固定A17 final建立干净短路径worktree，不重建。根D:/1800只读协调文件，不提交根改动。新产品/证据允许修改现有current_readonly的必要模块和A16命名的复用probe/launcher，新增tests/a18_current_frontend/及docs/evidence/A18/current-frontend/；其余旧成员保全，不迁移/删除旧材料。

scope固定 `CURRENT_BOOK_SOURCE_INVENTORY_CURRENT_FRONTEND_READONLY`，A18 gate全部身份重新绑定。预留输出 `D:/1800/.local/stages/a18-current-frontend-live`、activation `D:/1800/.local/stages/a18-current-frontend-activation.json`，当前不得创建；决定 `D:/1800/docs/approvals/A18-current-frontend-user-decision.json`、独立报告 `D:/1800/docs/evidence/coordinator/a18-independent-closure/independent-result.json` 均由调度在正式交付后固定。任务workflow使用本次正式派发消息给出的提交；executor使用本对话确切threadId，并与根JSON登记核对。不得使用clientThreadId或沿用A17身份。

已释放辅助报告 `.local/stages/coordinator/a17-current-script-analysis/notes.md` 与同目录JSON可作线索；对实际影响准入的源码要自己只读核hash/offset。Script唯一文件为 `D:/1800/.local/stages/a17-excluded-static-live/static-assets/1-d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41.bin`。不读取完整source sidecar或profile，不把真实Script复制进Git。不存在或hash不符则明确报告，不能重新获取。
