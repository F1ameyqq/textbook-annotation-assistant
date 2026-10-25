# A30 新恢复/采纳实际与阶段包验收合同

协调 `01a171f5-e73e-7452-982b-1885115e96ff`；唯一预定执行者 `01a171f9-3a3f-7832-9a94-70bee44d9510`；独立验收 `01a171f9-b65a-72d2-8d8d-f23107cd00dd`。此文是后续审查准备，不是实际激活。精确输入 manifest、authority、实际目录须由协调另行绑定。

## 先决条件与范围

新产品、普通客户恢复入口与冻结 launcher 已正式独立接受并由协调核验后，才可创建一条新唯一实际 authority。执行者在 launch intent 存在后不得再次启动；任何失败保留原件，后继 NOT_RUN。全部旧 authority 保持 spent1/remaining0，不改写旧失败或 UNKNOWN。

固定实际顺序：Q12 retained恢复（0平台调用）→核验恢复结果与历史链接→produce 对既有 Q13—16 作 ADOPT_EXISTING_MATCH（0保存POST）→核验16项接受→一次原生导出/一次本地显示→自身释放。精确限额沿统一补充合同，1800秒业务窗口+60秒释放。

本课1—11接受不可重放；旧九题另行保留。13—16来源归因继续 UNKNOWN，只能宣称采纳平台现存匹配记录。Q12仅能宣称通过原回执及保留读回恢复，不能声称本轮重新保存或新鲜读回。

## 实际独立验收

先核执行者固定 manifest 的全体 raw 原件、sha/bytes、来源副本对应及产品/launcher/authority 链。不得用 stdout exit0 或作者摘要代替业务和释放证明；不执行实际，不读 profile 内容，不改真实工作区。

1. 新 authority 的身份、head/settings/操作表、源码/入口/计划、预算与启动/截止窗口精确匹配；一次 intent，spent1/remaining0；没有未经授权重试。
2. Q12 新 reconcile-retained 唯一操作、原 save 当前受控转 COMPLETE、新接受 blob 的 previous_state/output、原失败 reconcile key/state/output、原发送/UNKNOWN/失败/capture 原件逐字节保存；provenance 平台调用0。不能根据最终状态抹掉历史。
3. Q13—16逐题接受 schema 为 CustomerCurrentExistingRead/v1，existing_record_only=true、new_save_performed=false、REUSED_CURRENT_EXISTING；node/info/order/created_at/rect_ids/全文/几何等与固定绑定一致；没有新 save intent/POST、覆盖或删除。来源仍 UNKNOWN。
4. 全16 candidate→原生输出映射完整唯一，无漏题/串题；映射及正文、题图、公式记录按实际固定证据核对。保留导出原文件、展示 HTML、DOM/图片解码/公式渲染结果与截图。若仅自动显示验证而无人目视，必须准确标记，不冒充客户目视验收。
5. 原保存11条与旧九题的接受 blob 保留；settings不变；真实工作区允许的差量仅是受控恢复、采纳、导出/展示记录。任何额外动作如实列出。
6. 逐项账实核对 HTTP/GET/POST、contexts、bound crops、export/display、OCR/模型/登录/签名上传为0项目、执行耗时；所有计数从原始日志证明，不从预算倒推。
7. 自身释放用启动时绑定的 PID/creation identity、wait/exit、Job/句柄证据；不能以历史释放、进程不存在或 wrapper exit0替代。原实际02释放失败历史单列保留。
8. 各未跑、未知、跳过项目明确标 NOT_RUN/UNKNOWN，不推断原因。任何错误立即给具体 REWORK 或固定失败接受范围，不扩大诊断或重跑。

输出新私有固定目录的 REVIEW.md、decision.json、manifest.json（除自身外全成员）、raw/；公开版仅有限脱敏事实。decision须包含 actual_run_authorized=false、独立性限制、实测范围、未证事项；协调接受前 customer_ready=false。

## 阶段包独立验收

新 ZIP 必须含正式接受的修复源码与普通客户入口，旧 ZIP 原样。检查 ZIP 路径安全/重复/大小写冲突/符号链接、每成员sha、无未声明代码、源码manifest与发布树一致；只在新私有空目录解压验证。

核对 START_CUSTOMER/START_HERE/运行引用/默认设置。客户使用步骤限选择书/范围、正常内容审校、执行及查看结果；恢复由正常入口处理，不要求技术 JSON、逐课工程预处理或外部 agent。默认启动不自动登录/写平台/调用OCR或模型，不默认忽略证书，不触动真实业务状态。

不得打包凭据、profile内容、私人raw、authority、workspace数据库/blob、未声明二进制。本机运行引用可明确保留，但必须写明这是本机阶段包及依赖条件，跨机器/任意书范围未验证。

包内状态保持构建时诚实快照；实际接受后用外置 sidecar 绑定 ZIP hash、实际结果、最终范围与限制。不能为了更新结果而无记录改旧包。

说明与成果明确记录：本课16项分别为保存/恢复/采纳、全16导出/显示实测层级、题图公式验证、真实时间与介入口径。61次历史AGENT_UI_TEST_OPERATOR审校不是客户人工数，97.87分钟服务区间不是客户工时；客户总耗时/人工未测则 NOT_MEASURED。不得宣称整章/整书完成。

有限离线包检查不授权启动真实业务。实际客户启动的验证方式须由协调在接受产品后绑定；已有字节相同的启动机制证据可以复用并明确范围，不能把历史启动当作本次新包实际启动。
