# A22 固定原会话复用独立预检报告

结论：ACCEPTED_OFFLINE_ONLY / BOUNDED_READONLY_PREFLIGHT，仅限冻结候选及本次有限离线差量。没有发现影响不误写、不越界、有界停止或事实表述的产品阻断缺口。当前不激活 live，不证明真实认证、profile 持久化、书源或首题保存读回。

独立对话 01a15cad-c63a-7062-8fe6-2fc4add9e9a5；执行对话 01a15cad-c139-76e2-88f8-705093575a7e，作者已释放。本次续派 workflow 为 05beddb52aed9e4380da99325f3fdeab1b1c6376；产品 workflow 保持 68279e400143c5681338530db409060a39760c0a。

- 基线：29a243227893cdbd8e7d235a8c787b4d721ed8e2。
- 产品：41fda0d1ff7f548e1bc8ec6b5b4d653109736532；final：1acc8d00dfef5808561139a99ba6f028d7bfd7a1。
- 候选 SHA256：264e7fd8120efc8dd8f95f6c66b28693104d82f47e3d68e3a91fd0c422b38141。
- 交付清单 SHA256：dd8ff91275f46b35f0551cf1dfb17971cce0352c1606bbca8d6e3af8c6dfaeb0。
- 根输入清单 SHA256：0e24aa2356ca87bfe925481d4ab411970568b0874f4804438ce6eda26be401b2。
- 续派任务 SHA256：86bfef90b1a1d31d8db1bbc9067739d6ec3ff3a013874745ab38004d37caaa4e。

只读取 D:/1800-worktrees/a22-independent-fixed 的冻结产品，以及根指定任务和输入清单；未读活动作者目录。导入前独立核全部 94 份输入的大小、SHA256、Git blob SHA1，后核候选 28 依赖、交付 82 成员及清单自身的去重闭合恰为 94。具体见 input-audit.json、static-evidence-audit.json。31967 旧成员仅 5 个获准修改、30726 旧证据 mode/type/blob 保全、78 新增/0删除及两条父链是根已核事实，本次不重新扫描 Git 仓库或活动 worktree。

静态检查 auth/policy/gate/probe/launcher 的实际入口：凭据解析/读取、known_form、authenticate、arm_submit、reserve_login 全部在 I/O/表单动作/预留前硬拒绝，无恢复开关；A22 policy 不准 POST、其他写方法及 LOGIN Document。auth 从 VIEWER 未证明状态开始，唯一 TARGET 导航，两层各 1 次预留。CurrentGuard 结合原页/原框、精确页、可见容器、无登录/密码框及本轮双层 session 预留/有限投影后才准入；业务 GET 在 authenticated 前拒绝。书籍首 GET 核 46007447 后继续其余书源读取。

冻结 SESSION 的实际三路径为 /qieti/api/user_login/profile、/qieti/api/user_login/config/permissions、/qieti/api/user_login/config/teams；VIEWER 每路径各 1、总至多 3。无需另发 profile 诊断；权限响应可贡献当前组合证据，账户字段可用性另报。旧 receipt、URL/HTTP200、本地 token 本身都不能单独准入。既有 GET_JSON 在受保护页内使用既有 token 发获准 GET，不把 token 返回 Python、写日志/文件或注入其他会话。

静态及 fake 检查保持两层来源/主框/逐跳/方法/WS/未知 API、固定原图注册、窄 assets 图片、version1/共享排除16、await 前预留和晚到 fatal/未结清停止。样题、上传、OCR、业务写入、书级提交保持 0；其他三例 HOLD，Q22 不导航/重放。900 秒总期限含释放及 OS 资源监督代码未新增行为；这些真实平台/OS 效果未在本次执行。

新 25 项 suite 以独立 runner 在隔离输入上运行一次：25/25，0 failures/errors，1000 ms（unittest 日志 0.991s）。成功 fake 贯穿真实 collect/get_once/original_once/visible_mapping 的同 context 六 GET、两图全解码/映射；凭据读/fill/登录 click/POST 为 0。另覆盖三路径/单阶段/单导航、历史 receipt 拒绝、401/403/登录/缺证/错误书籍停止、两层 POST/旧许可拒绝及 late fatal。完整 50 项 scope 在三份权威文档共 150 个逐字段变体均拒绝；模板及候选的同类型同值另有静态核证。

独立补充控制原始结果是 4 项已执行、3 PASS/1 FAIL，219 ms，后继 1 项 NOT_RUN，原 runner exit1，未重跑 suite 或任何已执行控制：

1. 无 native networkId/错误响应框，停止且不准入，通过。
2. viewer DOM await 中到达首错，认证仍 false、业务 GET 0，通过。
3. 未结清回调进入 NETWORK_GUARD_TASKS_PENDING，合成任务取消且无 waiter 保留，通过。
4. 固定候选/模板/片段控制在源码片段 hash 处失败：独立辅助代码以 splitlines(keepends=True) 多取一个尾 LF，和冻结方法 ast.get_source_segment 不同。失败发生前该控制已核候选、50 scope、三个模板、非执行状态和原 profile 指纹；失败原件在 controls/stderr.txt、result.json。
5. 缺失 scope 字段与同值 float 补充控制因 failfast 保持 NOT_RUN，不恢复。

静态证据 helper 仅修正元数据核对：精确证明多出的唯一尾 LF，按冻结 AST 方法复核 11 个当前片段 digest，全部匹配；同时复核 28/82/94 闭合及 3 模板/50 scope。该 helper 不导入产品、不运行测试，exit0；没有修改产品、作者原件或失败控制，也未重跑测试。辅助核对失败不构成产品反例；依据本阶段“正确停止且原件完整的细节列限制”要求，不为此返工产品。其完整证据见 static-evidence-audit.json。

decode/js_wire/native/reference 及未改片段只引用固定原 bytes/根保全与作者基线比较的有限证据。独立核当前 11 个片段与冻结 digest 同一性，没有重新取基线源或重跑任何旧 suite；不将此称为全回归。保留作者 run01/run02 的导入失败、run03 的断言失败及各 preparation helper 转录，后者不冒充本地 raw stdout。最终机器报告按冻结模板保留完整 50 项 scope，仅将 result 改为 ACCEPTED_OFFLINE_ONLY。

本次 runner 在 import 前阻断网络/Popen，阻断 .local 与活动作者路径访问、独立目录外写入；以不创建自连接 socket 的内存 event loop 运行。产品 load_native/profile_binding/occupancy/open_owned/supervise 均被阻断，fake 需要的入口仅由测试局部替换。forbidden_resource_attempts=[]；0 真实浏览器/网络/profile/本机配置/native/占用/产品或 launcher 子进程/login/live，0 decision/activation，未保留进程等待。普通离线测试/helper 命令的完成退出不等于持有 Windows OS 创建身份；该身份未收集。

唯一后继是根核证本固定独立交付，再把已有 A17 同类只读 TLS 许可绑定 A22 自己的候选、完整范围、机器报告、原 profile、唯一新额度及 900 秒窗口；本独立不激活，不借 A21 已耗登录许可，不重复问同类 TLS。A21、旧失败、UNKNOWN、耗尽额度和首题 HOLD 保持。
