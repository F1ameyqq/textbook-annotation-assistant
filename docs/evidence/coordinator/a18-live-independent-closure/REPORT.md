# A18 唯一真实轮固定结果独立核证

结论 **ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**。只接受本次固定失败归档、记录内有界计数及已证自有释放；不接受平台访问、认证/书籍/库存、原图、首题或写入资格通过。A18实际轮已耗1、余0；不重启、延期、补探或重放。

## 固定身份与输入

产品`45174e312ad23af349b3345be23eadb7f6a5e498`，离线final`a1dae2efb49f39700194f912bf4ce8404950699b`，实际final`35ad2ef50088373435f48f530efe32b59824da8e`。正式执行`01a15954-3ca1-76a3-a984-13229a985976`，正式独立`01a15954-997c-7af2-9645-a4e2c2b25e76`。

产品workflow`bb163ba162f32857202b6a068e9fc050ed4ad9f4`，实际派发workflow`101ce7f1043a64df6e318775e3820b369fc6e60d`，本核证派发workflow`6c1bed640734c3cdf83743002b0021455a75ef7e`；核证任务SHA256`11a5148dbc69f07206697ff778bc4ecbc15013397291e52662864da3dbb231e9`。

只用`D:/1800-worktrees/a18-live-review`的45份固定raw。输入清单SHA256`116c65b8ec1497d1e05a65a8c88139f76252162c08360239e163d36c407708fd`；45成员长度/hash全部通过，作者21交付成员及其清单、候选22依赖分别通过。作者清单SHA256`0fe6579613308291a5da6c7b2ae9863ee4b7a45a92ff4e168e608df34bb6f5fb`，候选SHA256`c0f7ea30ee5a3484544524b5e8c609125113a474d901bd24fc600529509ae8e8`。

四个独占阶段标记相等，A18 run_id/scope/workflow/candidate/activation/profile指纹一致，原始10份复制结果与bindings记录的长度/hash一致。activation SHA引用`2401b8aa6c57f09fbdfa1aefb61d3c3663d362ca99e095f5a3339164498717e8`，决定、既有正式离线报告和持续许可的digest引用与派发一致。本包未含这些原始文件，本次不读原.local/live或重新打开activation/决定；接受的是固定记录的引用一致性，不冒称重做原文件门禁。

31655旧成员全保全、22新增/0改删及实际final直接父为离线final，引用调度本次原mode/type/blob核证和固定保全记录；本验收没有重复全历史Git扫描。

## 实际失败、计数和时间

原始`current-state.json`为`outcome=ERROR`、`exception_type=Error`、`codes=[UNKNOWN]`。navigation FAILED，其余15步全部NOT_RUN。pre-shutdown guard未停止且failure=null，最终stopped来自shutdown、terminal_stopped=false，pending_tasks/pending_callbacks均0。没有记录到守卫拒绝首因，不能把本次错误归为旧CDN、PATH_BLOCKED、version、TLS或45秒timeout。

| 项目 | 固定记录支持的事实 |
|---|---|
| 启动/context/导航尝试 | 记录各1；四阶段标记为同一链，工具retries=0。 |
| 网络审计 | 2条GET Document ALLOW，分别FETCH_REQUEST_STAGE和CONTEXT_FIRST_REQUEST；同一导航path hash、无redirect。是双层同一导航记录，不等于2次HTTP。 |
| 六业务GET/两原图 | 后继NOT_RUN，执行/审计0。 |
| version | native/context预留均0；HTTP成功UNKNOWN。 |
| 共享排除/拒绝完成 | 0/0，本次没有实际触发新排除分支。 |
| 新Script/页图/映射 | 捕获0，页图及映射NOT_RUN；未读/执行/复制原.local素材或sidecar。 |
| HTTP发送总数、辅助发送、导航HTTP状态 | 均UNKNOWN。 |
| 认证/书籍/目录/全框库存 | 未证明；目录/框availability与coverage均UNKNOWN，不标KNOWN_EMPTY或FULL。 |

窗口UTC`13:10:22.192251—13:25:22.192251`（北京时间`21:10:22.192251—21:25:22.192251`），900秒。launcher记录UTC`13:11:02.359728—13:11:17.120790`，观测`13:11:04.012670—13:11:17.022318`，worker记录亦在窗口内；两个deadline_exceeded均false。

launcher UTC起止差14.761062秒，记录单调耗时14844ms，相差82.938ms；worker UTC差14.188093秒、记录14188ms，相差-0.093ms。只做原记录算术，精确组成仍UNKNOWN，不以猜测或新探测解释。记录明显未等待45秒，不据此给底层错误定性。

工具完成状态exit1，与工具文字中的product_exit_code=2、持有身份的product/worker exit2分别保留。`errors=false`及释放记录`errors=[]`不等于业务观测成功；launcher自身OS创建/退出身份与OS退出码保持UNKNOWN。

## 已证自有释放

| 自有进程 | PID | 前后相同created_filetime | 已观察退出 | 句柄 |
|---|---|---|---|---|
| 占用检查子进程 | 87100 | 134369754634475169 | exit0 | closed=true |
| worker | 72112 | 134369754628923432 | exit2 | worker_handle_closed=true |
| product | 54220 | 134369754623709515 | exit2 | product_handle_closed=true |

逐项核了前后PID/创建时间相等、有效正整数、exit_observed=true及exited_filetime不早于创建时间。worker另有creation_identity_match=true；两个Job均assigned、active_final=0、closed=true且errors=[]。context_created/context_close_attempted/context_closed/runtime_stop_attempted/runtime_stopped均true、state=RELEASED、errors=[]；投影与原件相等。

只接受这些持有身份的原始释放记录。未重新扫描、终止进程或检查占用；不把工具完成、自报或文件存在升级为launcher自身OS身份，也不声称日常Edge/profile完整字节未变。

## 结论边界及本验收释放

正文/schema UNKNOWN、sample0/NOT_RUN、自动schema=false、production_ready/write_eligible=false，原R02未修保持。首题是否未录入、目录/bbox、保存及内容/题框刷新重开独立读回均未证明。其他三例HOLD、Q22不导航/样题/重放、0B消息，无书级提交。

检查索引`checks.json`；原始字节、计数、身份和时间算术见`input-evidence-audit.json`；机器结论`independent-result.json`。本验收只静态读取固定文件并写新报告，0产品导入/运行/suite、0browser/network/profile/credentials/native/占用/登录/业务，未读作者目录或原.live/.local、未改根JSON/标记/activation/产品。

本验收已释放，无等待进程或自有live资源。原固定输入在封存前再次核hash，所有新增输出仅本目录；raw清单`sha256-manifest.json`仅排除其自身。后继交调度按实际失败与未知项处置，A18旧轮不重启或恢复额度。
