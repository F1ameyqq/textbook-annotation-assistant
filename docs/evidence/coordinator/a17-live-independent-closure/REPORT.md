# A17 唯一live固定失败与自有释放核证

结论 **ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**。仅接受已发生失败的固定归档和有证自有释放；认证、当前书源/库存、首题保存与刷新重开读回仍未证明。本轮live已耗1/余0，不重启、不延期、不清标记或恢复额度。

正式独立 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`；本次派发workflow `0ac9b3a29756b97b4f86de91f115e8e9d0f5f567`。固定final `5aec24575a0e1621f4f22680da3beba581e6cec2`，唯一父 `8bffd88dacc146fc3f061ed0863b299fa5dabd30`；产品 `1168a75eb35f319c3ced270b6c515adbdb38603f` 保持。产品workflow `d137a1bba49550f661b110ee14c9541a1dc4fb19`、实际live派发workflow `3c9487c7db198b8cb88340b52fbc1c1351679ff6` 与本次验收workflow分别登记。

候选SHA256 `4ed38cb1f703c3d0b5e94d601f2f267c05ead871b9a26004e2e44e5d6eeb31dd`；44输入清单SHA256 `2b9a7af24fbf5cdc8858d99e5f12c5171d8460d604a4af72e13806fb269e0a86`；本次核证任务SHA256 `993f888f10be3c046cd4a39b9815b3c59054e5a36a1a6349b0daddc15ddbd0d5`。产品及证据只读根 `D:/1800-worktrees/a17-live-review`，未读原作者活动目录或.local。

## 六项集中核证

| 项目 | 固定证据与核证结果 |
|---|---|
| 一次调用与授权绑定 | tool-execution/dispatch的cwd、完整argv一致，记录一次launcher调用、零重试，tool exit2。candidate、decision、activation、独立报告原bytes SHA互相匹配；4个一次性标记相同，task/run_id/workflow/scope/profile指纹和例外标记匹配。前次独立机器报告SHA8973892d…原样引用，未重跑。 |
| 窗口与时间 | UTC窗口12:19:01.709237—12:34:01.709237；launcher实际UTC12:19:44.770667—12:19:55.513996，即北京时间20:19:44.770667—20:19:55.513996。launcher、worker、current-state始末均在窗口内。报告monotonic10812ms，UTC字段相减10743.329ms，差68.671ms；代码monotonic起点在函数入口，UTC started_at在参数/授权后，起点/时钟不同，精确差额分解UNKNOWN。两者均未越界；不为此重跑。 |
| 预期排除与首错 | 12:19:51.642113 UTC，cdn.bootcdn.net:443 GET Script在native层BLOCK，类别EXPECTED_EXCLUDED_STATIC_DENIAL；合计事件1、完成拒绝1。12:19:54.852433 UTC（北京时间20:19:54.852433）首次非预期fatal为https/www.usense.com:443 GET XHR、FETCH_REQUEST_STAGE、PATH_BLOCKED；之后3条STOPPED/BLOCK。顶层和shutdown前、序列化时首错均PATH_BLOCKED，最终ERROR。路径/query/用途未留在脱敏审计，UNKNOWN，不猜接口。 |
| 次数与下游 | context_created=true及唯一调用/标记支持本轮1context、1主导航尝试；双层NAVIGATION审计2条对应此次尝试，不能算两次导航。navigation FAILED；六固定业务GET、两原图、两映射和所有样题/内容步骤NOT_RUN。sources空不证明空库存，认证未证明、库存可用性/覆盖UNKNOWN。11审计=8 native+3 context，类别2NAVIGATION/4STATIC/1预期排除/1PATH_BLOCKED/3STOPPED；事件数不是HTTP请求数。 |
| 同源Script元数据 | 公开摘要1份，HTTP200、3065996bytes、SHA d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41；executed_by_collector=false。只核元数据，未访问、复制、执行或重算.local原件/完整source sidecar。不能由此得到schema或当前书籍资格；正文/schema UNKNOWN、sample NOT_RUN、自动schema停用、production_ready/write_eligible=false。 |
| 自有释放与保全 | context关闭、runtime停止、release errors空；两个快照pending_tasks0、排除汇总pending_callbacks0。三个进程前后持有PID/created_filetime匹配且已观察退出：product54876/exit2、worker72936/exit2、occupancy46192/exit0；3句柄关闭。2个Job最终active0并关闭，期限未超。44输入size/SHA/blob及Git mode/type/blob通过，18依赖保持；31574旧成员、30349旧evidence原mode/type/blob全保全，25新增、0修改删除。 |

这些结论基于固定JSON、工具记录和既有守卫的完成计数，不是本次重新观测网络。辅助HTTP实际发送总数、导航HTTP状态、DNS/TCP/TLS活动及CDN路径/内容/用途/必要性均UNKNOWN。单个Script元数据摘要未通过访问原件重新计算，保留此证据边界。

## 释放证据的准确范围

product持有创建身份 `134369723847803858`，worker `134369723851816614`，occupancy `134369723856186189`；各自before/after PID及created_filetime相同，after.exit_observed=true，退出码2/2/0。两Job active0及句柄关闭只证明记录中的自有资源释放，不扩为全机无进程或全profile空闲。occupancy matching_processes=0是启动前事实；未追加运行后占用探测。

launcher自身OS创建/退出身份仍UNKNOWN。工具session6147的exit2不替代launcher OS身份；launcher.errors=[]/工具errors=false仅是该层错误列表，不能覆盖current-state ERROR及product/worker exit2。原始事实充分，以上报告口径限制不阻断固定失败收口。

## 授权、保全和未执行部分

authority/user-decision原件记录用户直接回复“一直批准”，本次decision SHA `f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46`，activation SHA `20fd7317bedd70b6e9685a0de44d930f5da85cd45fdffeea386f26fa440c63be`。同类专用context临时TLS持续许可已登记，不重新询问；后续具体阶段仍绑定自身范围、版本和额度，不恢复本轮、不扩写入/登录/新来源或全局设置。本核证不启动后继。

已检查15条source-copy记录、24交付成员+清单、18候选依赖及本地不可变Git父链/树。固定包新增仅预定脱敏JSON/MD/base-tree.raw，不含Script body、static-assets文件、完整source sidecar、cookie/token/auth/header值或profile内容。原Script仅.local保留的说明未通过本次访问原件核实，不宣称有原件内容审阅。

原有限离线接受、R01非阻断归因残留、旧REWORK及21组NOT_RUN原样保持；本次实际顶层首错一致不表示R01一般情形全关闭。原R02仍REWORK且能力停用。其他三例HOLD，Q22不导航/重放，0B/外部联系人消息、不推送、无书级送交。

本次仅静态读取/散列和报告工具。运行 `python -B docs/evidence/A17/independent-live-review/verify-fixed.py` 一次，exit0；工具只解析固定JSON、文件散列及3次只读Git元数据调用，无产品import、suite、launcher、浏览器、网络、profile、native API、占用、登录或业务调用。所有输出仅本独立目录，44输入末次原bytes复核通过。

本独立已释放，无真实产品资源创建或持有，未扫描或终止外部进程。完整逐项记录见evidence-checks.json，输入核证见intake.json和input-preservation-final.json，机器结论见independent-result.json，成员清单见manifest.json，自身释放见release.json。后续由调度集中安排必要适配，A17旧额度保持1已耗/余0。
