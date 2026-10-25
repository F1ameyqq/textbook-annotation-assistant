# A30 修复阶段包与普通启动验证

此任务延续用户的本机可运行交付目标，由已登记开发对话制作、已登记独立验收对话评审；协调核验后接收。现在只准备。新产品/launcher独立接受后，协调明确派发打包；包离线接受后，再对这个新包作一次有限普通启动观察。本文不激活平台实际。

## 制作

复用 v1.1.4 的包装机制和本机 runtime、Edge、profile、workspace 引用；源码须精确来自本轮已独立接受的冻结产品 manifest。新版本/目录/ZIP唯一，旧包不改。START_CUSTOMER.cmd及正常 GUI/CLI 恢复路径均应来自已接受源码，禁止将专用 actual launcher 变成客户必须使用的入口。

一页说明写明普通START、选择书/范围、正常内容审校、执行/查看结果和未知保存时普通对账入口；客户不填技术JSON/IDs、无需外部agent逐课准备。写清本机依赖、当前有限已验证范围和客户总工时/人工 NOT_MEASURED。构建时保留当时真实业务状态；actual接受后使用绑定 ZIP hash 的外置最终sidecar更新成果，不能原位改旧ZIP。

冻结交付源manifest、包manifest、ZIP hash/bytes、安全成员清单、入口/运行引用、说明、打包命令及原输出，送独立验收。私有原件、workspace数据库/blob、profile内容、credentials/token、实际authority不入ZIP或Git。

## 新包第一次普通启动（仅在协调确认包离线接受后）

由单一已登记开发对话用新包原有 START_CUSTOMER.cmd 启动一次，限本机UI就绪观察，最多180秒+60秒自身释放。复用已有owned-process身份/退出与窗口观察机制，保留精确包hash、入口命令、开始/结束、pid/creation identity、窗口就绪事实和退出证据；只处理本次自有进程。

不点击生产、下载源、OCR、公式、登录或再次对账，不重复旧61次内容审校，不运行专用actual launcher。正常UI默认启动不能自动产生这些动作。只看新包装配和普通入口能否就绪，关闭本次自有窗口。无Edge/profile内容读取，无平台请求。

验证前后现有job head、operations、events、settings及既有接受引用一致；若启动实现必然产生本机非业务元数据，逐项如实说明。出现异常立即保留输出并停止，不重启同一尝试、不强杀其他进程。缺失或无法观察项保留UNKNOWN/NOT_RUN，不把窗口存在当业务完成。

固定启动证据另送同一独立验收，只审原件、不再次启动。业务结果由唯一0POST actual及其独立接受证明；这个启动观察只补新阶段包能从普通入口就绪的证据，不扩大书/平台范围。1800-a仍PAUSED，书级送审及对外发布不在范围。
