# 预览绑定apply和单题新增writer

在离线结构草稿之后新增独立显式writer。真实平台运行由总控独占；本工作线只编写及合成验证，没有接入profile或执行业务请求。原公共合同、OCR、Q7专用写器不变。

## 目录apply

`directory_apply.make_apply_plan`消费真实preview请求、原始响应、执行结果、网络事件和独立全局读回。当前已观察响应是HTTP200/code整数0，`question_moves`精确为五个稳定node的目录变化，old/new order不变，其他增删/目录移动/题序变化/risk列表全部为空。代码逐字段、类型、数组顺序核验，保留所有原字节引用；不能用手写has_changes摘要替代。

绑定还验证preview两层各一次POST、无apply/commit、成功释放，及之后新capture中directory/frames/source与preview前原字节相同。实际独立PID/OS释放仍由总控外层证明，模块不据摘要自造PID证据。

```powershell
python tools/prepare_usense_apply.py --move-draft PRIVATE/move-bundle.json --sha256 MOVE_BUNDLE_FILE_SHA --preview-request PRIVATE/preview-request.json --preview-response PRIVATE/preview-response.json --preview-execution PRIVATE/result.json --preview-network PRIVATE/network-events.json --preview-readback PRIVATE/directory-preview-readback.json --out PRIVATE/apply-plan.json
python tools/run_usense_structure_writer.py apply --config PRIVATE/fresh-config.json --sha256 CONFIG_FILE_SHA --plan PRIVATE/apply-plan.json --plan-sha256 APPLY_PLAN_FILE_SHA --baseline PRIVATE/full23 --ledger-root PROFILE_PARENT/usense-existing-ledger --authorization-reference CURRENT_ROOT_AUTHORIZATION
```

配置用原 `run_usense_live.py configure`，operation保持READONLY_CAPTURE、static_get禁用，限定15分钟以内的当前profile/角色/TLS/代码摘要。配置不授写权；显式mode、真实preview绑定计划和当前写授权参数三者一起才进入本writer。它按计划派生精确全书GET范围，复用既有OwnedReadonlyContext生命周期、FETCH和SEND，两个拦截层只放行此范围及一个apply端点的精确载荷。配置窗口和计划文件原字节在每次拦截再次校验。新增包文件会改变implementation_digest，必须在最后集成后重新冻结配置。

旧完整快照可以作为不可变seed，原观察时间明确保留，不重标成当前采集；writer在发送前实际重读全部23题annotations/info/五区，加目录、全框、来源与已绑定页，逐原生对象严格等于seed，最早本次GET距提交不超过900秒。任何一题或未知字段变动都在intent前阻断。此路径的当前基线依据是writer实际新采集，不能凭旧seed或旧preview本身放行。

随后复核证据和ledger，独占创建一份intent并flush+fsync完成后才arm，两层POST各一次。不能额外preview、directory/save、commit或转向其他API。HTTP失败、超时、坏JSON或不明发送状态都保留intent为UNKNOWN，不能换运行目录重发。

首次apply响应schema此前尚未观察：writer先原字节落盘，HTTP200/code整数0仅返回`APPLY_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK`，`save_success=null/platform_acceptance=false`。没有伪造或硬编码“apply成功”收据。主进程必须退出并由总控确认释放，再以新配置/新进程完整读回，使用原`verify_move`逐对象核验和真实导出。未知格式由总控基于原回执与独立读回审计，不自动清除intent。

## 通用单题新增

```powershell
python tools/run_usense_structure_writer.py insert --config PRIVATE/fresh-config.json --sha256 CONFIG_FILE_SHA --plan PRIVATE/new-question-draft.json --plan-sha256 DRAFT_FILE_SHA --baseline PRIVATE/fresh-full-book --ledger-root PROFILE_PARENT/usense-existing-ledger --authorization-reference CURRENT_ROOT_AUTHORIZATION
```

plan是经来源/scope/crop审校的原`make_new_draft`输出（bundle内draft单独原字节保存），不能把整个bundle当draft传入。writer重新构造计划、核所有来源/裁图引用、当前目录完整稳定绑定及白名单逻辑题，再同样实际重读全书、一次intent、一次统一commit。操作者username及所有新框user_id只在页面内绑定，Python仅得到摘要。

新题收据沿用已观察统一commit格式，必须新插入、精确当前new_order、非全局尾追加，返回新且唯一node，格式不认识立即UNKNOWN。返回`INSERT_RAW_RESPONSE_REQUIRES_INDEPENDENT_FULL_READBACK`后仍没有验收；总控用新进程完整读回和原`verify_new`核新info/rect、内容/图框及全部旧题，仅允许已计划的+1重排，旧时间戳额外变化HOLD。

Q6/Q7/Q8/变式分四次，每次重新取得完整当前基线和scope，下一题anchor只能使用上一题真实读回的稳定身份。没有将能力自动开放给整书任意候选。旧intent存在时本writer拒绝，外层先审计UNKNOWN，不能自动再发。

基础owner的`release.json`只负责其生命周期，内置save_attempts为0；结构writer的`execution-result.json.release.save_attempts`是实际结构发送计数，附语义说明。总控应以结构execution、send-intent、原生回执、原始网络事件及外层PID释放共同验收，不能把基础owner的计数字段当作“未写平台”。

合成测试入口：`python -B -m unittest discover -s tests -p test_usense_structural_writer.py -v`。测试假上下文不联网、不接入profile，实际调用写器的full-prewrite、intent、SEND调度、原字节回执保留与清理逻辑。首次synthetic apply响应只用于证明不猜receipt schema，不冒充真实apply回执。
