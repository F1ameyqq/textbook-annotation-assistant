# A19 唯一真实轮：固定失败与自有释放独立核证

结论：`ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`。接受固定失败归档及记录中已证的自有释放；不接受平台、认证、书籍、库存或保存成功。A19 已耗1轮、剩余0，不重试或恢复额度。

实际 final：`38e86a1c153eb0ad68ebd22d4403602ffaa6852b`；直接父离线 final：`e999f4e753cd5f1e44a19ab55dd776d2fa589389`；产品：`13067ff38ea8c0fbeae1c896d415c79238443b0e`；候选 SHA256：`2e94be09ff3d733bcf65b7fa556187280deb09574134866b110e3575dd233f7f`。本次独立派发 workflow：`d0df8e45bcd4d48139ba477aca14f08998749432`，正式独立 `01a1597d-225a-7902-837a-5d5a2dadffe2`。

仅静态消费 `D:/1800-worktrees/a19-live-review` 的45个固定 raw，逐项核大小、SHA256及Git blob SHA1；20候选依赖、作者23交付成员加清单、10份脱敏输出原件均核证。导航、审计、结果与释放投影逐项对应 raw。31730旧成员保全、24新增且0改删及直接父关系引用正式派发中的调度Git核证，本独立没有重做完整Git树比较。未读原作者目录、原.local live、Script正文或来源sidecar；外置决定/activation/离线报告只核固定派发哈希、bindings和标记对应，不重新打开其原件。

唯一窗口为北京时间21:49:46.731156—22:04:46.731156；记录的launcher实际21:50:21.468739—21:51:10.169697，均在窗口内，未超原总期限。固定意图、argv和四个claim标记的A19身份、候选、activation、profile非敏感指纹一致。记录支持1次launcher、1个context、1次获准原导航，另有1次后续Document被阻断，没有准入第二导航。

| 观测来源 | 核证事实 |
|---|---|
| 原导航被动CDP响应 | 关联 ORIGINAL_MAIN_DOCUMENT_NETWORK_ID；HTTP200，相对2281ms；原始关联ID按设计未落盘 |
| goto/原page事件 | Response返回、HTTP200、DOMContentLoaded观测；goto DONE，15391ms，domcontentloaded/45000ms保持 |
| readiness | FAILED，30172ms，TimeoutError/UNKNOWN；容器30000ms保持；整体outcome ERROR |
| 原导航loadingFailed | 未观察到；不补HTTP0，不据此声称没有网络活动 |
| 最早非排除guard拒绝 | 21:50:39.712394，FETCH_REQUEST_STAGE、GET、Document、NAVIGATION_BLOCKED、redirect_hop=false |
| 后继与书源 | navigation字段保留DONE；15后继全部NOT_RUN，六固定业务GET与两原图均未执行，sources为空 |

`main_navigation=true` 在固定 policy.py:122 仅由 resource_type=Document 得出，单独不能证明主框。本次主框归属另有固定代码分支支持：probe.py:316–326先绑定parentless主框ID；472–476按事件frameId与该ID相等计算owned；346–365在返回策略类别前将任何未持有身份请求覆盖为UNOWNED_TARGET_BLOCKED；511–519才写出FETCH_REQUEST_STAGE审计并进入failRequest分支。因此固定审计中的NAVIGATION_BLOCKED支持“匹配绑定主框”的有限归属。这是固定代码及审计的控制流推断，不能冒称独立比较了未落盘的原frameId，也不能由Document标签推定目的或触发原因。

拒绝路径仅有SHA256 `55d900e6fc7524cac0de130ea2e6c249426846e56af5165e9b0ddbcaed4d746d`。本报告不解猜路径、不采纳未在本隔离证据中核证的login路由匹配，更不推定凭据失效。redirect_hop=false只保留该请求未被分类为CDP重定向的事实，不证明完整HTTP跳转链、reload或应用行为原因。

guard_pre_shutdown与guard_at_serialization均保留Stop/NAVIGATION_BLOCKED，顶层及readiness保留TimeoutError/UNKNOWN。固定实际顺序支持guard拒绝先于最终readiness超时；精确timeout UTC未记录，不能伪造。固定代码在容器wait_for前后检查guard，未在该等待期间立即中断；原first_error选择又保留已经记录的具体TimeoutError，所以顶层错误不是时序最先的guard错误。两层原件完整、业务后继未执行，该报告选择与停止延迟作为限制保留，不改产品、不补跑，也不重标为产品通过。

14条审计不是14次HTTP：原导航两层ALLOW，version两层预留1/1、HTTP成功UNKNOWN，SESSION_PERMISSIONS两层ALLOW且认证响应UNKNOWN。CDN Script排除事件1、完成拒绝调用1，共享上限16。总HTTP、辅助发送总数、拒绝前DNS/TCP/TLS活动、Script必要性保持UNKNOWN。仅核1份获准Script元数据（HTTP200、3065996字节、记录SHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41）；没有读取正文或独立复算该正文哈希。

| 进程时钟 | wall跨度ms | 自身monotonic记录ms | monotonic减wall ms |
|---|---:|---:|---:|
| launcher | 48700.958 | 48765 | 64.042 |
| worker | 48306.919 | 48297 | -9.919 |

两种时钟分别保留，差异原因及精确阶段分解UNKNOWN，不将wall与monotonic混为同一量或推定超时原因。

固定持有句柄记录证明三个PID及创建filetime前后一致、exit_observed=true且句柄关闭：产品87356/exit2，worker39024/exit2，占用子进程56460/exit0。两个自有Job均assigned、active_final=0并closed；context_close_attempted/context_closed、runtime_stop_attempted/runtime_stopped均true，errors为空；最终pending_tasks和记录的pending_callbacks均0。此接受限固定自有资源记录，没有外部进程重扫。工具完成exit1与产品/worker exit2分开；摘要errors=false只说明管理错误数组为空，不能当业务成功。外层launcher自身OS创建/退出身份仍UNKNOWN，session75046结束不替代该身份证据。

首次CRLF普通checkout与raw候选比较导致的AssertionError/exit1完整保留；后续raw校核不修改pin、旧原件或产品，不产生新live。0登录提交/写入/上传/OCR/书级提交；sample0/NOT_RUN、自动schemafalse、正文/schemaUNKNOWN、write_eligible/production_ready=false、旧R02未修。认证、当前书籍、目录/全框可用性与覆盖及原图映射仍未证明；其他三例HOLD、Q22不导航/样题/重放、0B消息。

本次独立只新增本目录的检查、报告、机器结果、输入raw清单和释放。0suite、产品import/运行、launcher/browser/network/profile/凭据/native/占用；未新建decision/activation、未终止进程或改根文件，输入45成员复核未变。独立已释放，无持续等待进程；后续工程由调度另固定范围，本次不启动后继。
