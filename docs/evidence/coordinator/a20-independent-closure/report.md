# A20 有限独立离线预检

结论：**ACCEPTED_OFFLINE_ONLY**，仅接受固定候选的有界登录恢复与同 context 书源读取离线预检。未发现需要阻断本候选的保密、重复提交、业务误写、越界、停止或事实问题。真实认证、书源与首题保存读回均未证明；本结论不授予登录、凭据发送或 live 激活权。

独立聊天 `01a159ab-01ba-7093-89a6-69e7ce572c38`；派发 workflow `8619a58874563b6b20ef435a0796355638d25f8b`。基线 `38e86a1c153eb0ad68ebd22d4403602ffaa6852b`，冻结产品 `28203196b4f2dae27b1de4213b27da9a41ae3139`，final `b41e88d7756fde9d7f1b348ce5a300d1104e765b`，产品 workflow `52be34a72c43a7331976aba4b286138b9183856b`，候选 SHA `91db377e44b5b864208cc27a078d25266b3375bba2fdee18b9c648f37b572a7b`。

新 suite **35/35，2250ms**；独立控制 **5/5，641ms**，均为 runner 实际记录的墙钟耗时。只运行本 A20 新测试和五项控制，各一次，无旧 suite/失败重放。原 runner 保留相同私有路径 audit、内存事件循环及网络/Popen/native/profile/占用阻断，只改变 ROOT、输出位置与测试入口；差异见 runner-transformation.json。独立控制覆盖两种守卫顺序与并发重复 POST、跨阶段迟到响应、填写期间来源变化、过期决定前置拒绝、意图持久化失败不点击及异常脱敏。

114 输入成员已先核 SHA256/Git blob/长度/声明 mode/type，末尾再次核证原 bytes 全保持；27 候选依赖及父包闭包全匹配。30522 旧证据及 31754 基线成员全树保全引用调度固定核证，本隔离没有重复全树核验，亦不修复/读取作者活动目录。

静态核读唯一获准 Script 原件：3,065,996 bytes，SHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41，与 A19 已捕获元数据一致。独立检查 15 个静态位置、三条精确 session GET 和两个登录跳转位置，确认登录 POST/两键/Hn 数值成功规则、UI 调用、SPA push、401 刷新与原请求重发；原件未执行/复制，sidecar 未读，A19 触发原因保持 UNKNOWN。

| 组 | 结论 | 证据范围 |
|---|---|---|
| P01 | PASS | 114 input raw members and 27 candidate dependencies; raw no-Git export; both regular initializers and intentional namespace packages checked |
| P02 | PASS_STATIC_ONLY | Authorized original Script SHA/size matches A19; 15 static needles, three exact session GETs and two fixed login redirect offsets verified independently |
| P03 | PASS | Frozen gate/template full scope and direct A20 credential/TLS decision requirements; missing and changed scope fields rejected by new suite |
| P04 | PASS_OFFLINE_ONLY | Fixed ordered two-Document reservations and original frame/origin checks; fake duplicate navigation refusal; outer 900s limits inspected without OS execution |
| P05 | PASS_OFFLINE_ONLY | Root configuration only after live approval plus known form; required original profile fingerprint and username-derived directory; fake origin-change and expired approval controls |
| P06 | PASS_OFFLINE_ONLY | Durable intent before click, native/context each reserve once, exact two-key payload, no second actual POST; both observation orders and concurrent duplicates checked |
| P07 | PASS_OFFLINE_ONLY | Refresh/automatic resend/other API writes refused; three fixed session GETs per phase; existing six GET/two original/version1/shared16/sample0 limits retained |
| P08 | PASS_ORCHESTRATION_ONLY | Login response, SPA transition, protected viewer/current session and book identity remain distinct; fake same-page/guard collect six GETs/two originals/two mappings, unchanged readers mocked in this orchestration test |
| P09 | PASS_OFFLINE_ONLY | Finite response projections and safe exceptions; fake secret canary absent from runtime outputs; current-session HTTP failure interrupts readiness; prior-phase late response refused |
| P10 | PASS_OFFLINE_ONLY | First error/UNKNOWN stop/NOT_RUN and fake release controls; fixed native resource-close code inspected, no real OS resource release or platform proof claimed |

实际门禁严格取冻结 template 的完整 **39 项 scope 字段**，包括两导航顺序、精确登录 POST/两键、原配置与 profile 指纹、session 每路径每阶段一次/两阶段、refresh 与重发零、直接 A20 凭据决定要求。机器结果的 report_path 保留 gate 要求的根接收路径；本次实际文件位于本独立目录，由调度核证后接收，独立未写根协调文件。

限制：

- Independent report-sealing attempt first failed source decoding before execution. Original helper and exact tool stderr are preserved in report-packaging/run01; the current observed helper bytes decode as UTF-8, initial decoding cause UNKNOWN. A new ASCII-source sealing helper was used, also correcting its own external candidate-digest comparison before execution; no product code or passed tests changed or reran.

- No real browser/network/profile/config/native API/occupancy or product/launcher child process was used. Fixed native Python reference is imported inertly by the offline tests.

- Actual current DOM, CDP complete postData, frontend request order, service responses, authenticated reuse display and protected session behavior remain untested. Any deviation must stop without resend or scope expansion.

- The full successful collect test exercises authenticate, real guard methods and collection orchestration with fake page/credentials. get_once/original_once/visible_mapping are fake in that test; it is not new image/geometry/platform acceptance.

- Unchanged decode/js_wire/native dependencies are byte-bound. Earlier finite evidence is retained within its prior scope; no old suite was rerun and no historical NOT_RUN was changed.

- Baseline 31754 members, four permitted modifications and 30522 old evidence preservation are supplied coordinator fixed verification facts. This independent final comparison covers the supplied 114-file raw export and all 27 candidate dependencies.

- Author first fake-clock run failure/error and first packaging failure/partial raw remain byte-identical; this review did not replay them.

- A19 actual 401/expiry cause and launcher own OS exit identity remain UNKNOWN; this offline review does not close them.

- Authentication, current book source inventory, current mapping and first question save/readback are NOT_PROVEN/NOT_RUN. R02 remains unfixed and disabled; body/schema UNKNOWN; write_eligible=false.

- A17 standing readonly TLS permission does not authorize this credential transmission. Coordinator must obtain the concrete A20 direct decision after this preflight, then separately bind/activate its one live round.

本轮 0 真实凭据/profile/browser/network/native API/占用/产品子进程，0 登录/业务写入/decision/activation/live。只导入固定 Python 参考代码作内存测试，不代表执行原 native 工具。作者失败、首次包装/部分 raw 和旧证据均保留。无待持有资源和等待进程，释放见 release.json。下一步由根落实本次具体凭据/TLS 直接决定，不借用 A17 只读许可；其他三例 HOLD，Q22 不导航/样题/重放，0 B 消息、无书级送交，2026-10-22 晚截止保持。
