# A30 v1.1.3 普通 START 实际有限独立审查

结论：**ACCEPTED_FIXED_V113_ORDINARY_START_ORIGINAL_TASK_VISIBILITY_PRESERVATION_AND_OWN_RELEASE_ONLY**。

固定包根 START 已成功启动普通“教辅 · 材料准备与生产”窗口，原任务列表可见，正常退出与受管进程释放成立。结论覆盖这些已观察事实，以及首轮cmd失败、有限合成定位和原workspace保全；不扩展为完整GUI交付、审校页内容、旧四题新可视复查、认证或全16生产成功。

输入manifest `10b858cf1c8e9f70aeeae818f01d61ada16e179d8937c11e8749f937637bb87f`，summary `c27d58285bac67322b2d672fd1269221ed00378ee0ecf2f1a9169ca1212cd5a9`。独立复制26 raw+3元数据，并按内嵌首错manifest追加14个原固定成员，共43件，全部hash/字节数接收与最终复核通过。审查没有运行产品、START、合成cmd、浏览器、网络、模型或现行profile/workspace。

五组固定证据检查PASS：

1. **普通入口身份。** raw START、release-manifest、customer.py、owned_process.py 与已接受v1.1.3独立副本精确相同；两轮START之间亦不变。START hash `be75a164e27ea3feb7380625cc2c424e5a188fe8c11bc08036aff07138b43a11`，release-manifest `95ece106ff41ad6752e6d7d0c23b57bbf9e800e24d8e8cc88182d5ddd0690a43`；执行记录直接是顶层 `cmd.exe /d /c .../START_CUSTOMER.cmd`，不是替代Python GUI入口。绑定的包独立manifest `20aab5c84b1fd5f0e1739d47b4eed519d1ac4c0b69922faca2283c98dc597199` 精确匹配。
2. **首错保留与有限修正。** 原轮01 cmd exit1，只观察到一个cmd进程，raw stderr以cp936解码为“命令语法不正确。”，GUI未观察、后继未做。两份固定echo+exit合成结果：相同holder和命令参数，仅argv0斜杠不同，前斜杠exit1/相同stderr，Windows反斜杠exit0/精确echo标记；各自释放原件通过。两版observer比较仅cmd路径规范化及独立OUT02变化，原包/START没有修复或覆盖。有限证据足以归属本次观察器命令形式问题，不推广为所有Windows shell行为或底层cmd解析根因证明；原失败不删除。
3. **窗口与任务可见。** reviewer直接查看固定截图 `01-customer-start.png`（SHA `0450f442f4b33e3d9d9575618e9640db3fa7b6fdc4aa6d4b525ea48ce0764300`），确认窗口标题、书46007447、课时“2 一定是直角三角形吗”、原第一行 PREPARED_OFFLINE / BLOCKED_BEFORE_SEND，以及第二行 NEEDS_REVIEW / NOT_RUN。选择第一行、点击异常审校和关闭标题栏是固定operator记录；截图本身没有展示审校页内容。点击后既有个人Edge标题/标签变化也只作为操作记录，不提升为页面内容接受。
4. **保全与自身释放。** 两轮各自before/after清单除at外相同，3831项路径/长度/hash与launch04独立冻结原字节逐项对应，77操作和84事件相同，settings/head不变，无新增/缺失/改变文件。实际before/after由固定清单hash表示，本审查没有重开现行workspace。成功轮北京时间2026-10-24 21:08:17启动、21:10:20退出；cmd、conhost、两个Python、两个短命Edge共6个不同受管身份exit0，所有观察句柄关闭、Job active_after0、thread/process/job句柄关闭，stdout/stderr均空且hash匹配。close路径的原代码关闭并释放local server后destroy；Python正常退出记录支持本地server已退出。这里确认的是自身受管进程，不宣称既有个人浏览器全部关闭。
5. **工具限制与范围保留。** 固定operator记录浏览器工具返回 `Local browser use is disabled in Work settings`，随后没有改设置、绕过或换API继续操作。该错误是固定操作说明，原工具返回并未作为独立raw附件包含；不把其存在扩大为额外软件故障。审校页内容/旧4新可视复查本轮NOT_RUN；个人Edge里本地审校标签仍留着，server已退出，不冒称标签已关。原旧4显示接受不重做，也不因此新增launch04业务门槛。

绑定profile-release/workspace04回执hash `e8f57b66cdce358ef897b0cd28e08850be3504c2a8e6cea7ad2fd6c0e0c507fb` 匹配；记录original profile owner0、用户确认登录并正常关闭、workspace匹配04。该包没有附Win32_Process原始枚举行，本reviewer将owner0限于固定元数据回执，不冒充独立认证验证或新进程枚举。本地操作记录业务/保存/导出/OCR/model动作0且无新workspace operations；未提供独立网络抓包，不声称全面网络审计。

本次证明可启动包、原任务列表、保全与自身释放；完整GUI handoff仍未证明，CUSTOMER_READY=false，1800-a PAUSED。旧四题/旧九题成功及f450 HTTP401/耗尽轮次原状保留。本轮workspace仍与已接受launch04逐字节一致，有限启动结论不要求重做内容、模型或旧显示，也不重开START补齐工具禁止的检查。平台12新轮由唯一作者/新root授权单独负责，其实际结果另审。
