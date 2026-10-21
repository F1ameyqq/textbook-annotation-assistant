# A24 current-context-r1 固定实际书源独立验收

结论：**ACCEPTED_FIXED_CURRENT_SOURCE_READ_WITH_GAPS_AND_OWN_RELEASE_ONLY**。接受本轮固定范围内的真实书源读取及已证自有释放；不构成首题保存、生产就绪或新请求/写入许可。

actual final `dceda09db31487d64654e23dd36ccd3705c740fc`；执行产品 `dde5746600df9854c33c5814a8f41ad85b7b4e16` / readonly final `6740d7533ea7b5bf5f322d768e8688826afe5d43`；候选 SHA256 `c68ce354be516552e1aadafe253cd3f9c12785b3107d2454e59f10446ef31b77`。本次独立派发 workflow `575f79eb74dfc5c06af88facbc5dd59e8dee455a`；正式独立 `01a15cf8-68e0-7b63-91a3-657a567b344c`。

仅使用 `D:/1800-worktrees/a24-current-context-r1-live-review`。根 input SHA256 `35ef7572c797dfa73d4e0859ab05cae2ca67e8b933597702bda18acaec4ae912`、任务 SHA256 `4c11935552011894a7bef8829d6e28228705894970b50431ac81d08f04c8e83c`、实际交付清单 SHA256 `5c5e6b955a35a70a09216e26cc6d69569ee22f1262779214035f9303033d30e0`均匹配。独立核完92输入、42执行依赖、48交付成员的大小/SHA256/Git blob/mode/type与28 raw副本摘要，并在封存前复核原输入不变。根已核32,410旧成员保全、49新增/0修改删除；本次引用该机械边界，未重复全库扫描。

## 本轮事实

唯一900秒窗口为2026-10-21 UTC08:04:39.744169—08:19:39.744169（北京时间16:04:39.744169—16:19:39.744169）。固定argv/cwd、activation/decision/原独立报告摘要一致，launch1/retry0。launcher记录08:06:10.766990—08:06:27.223006，capture记录08:06:27.490122结束，均在原窗口；outer/product/worker/occupancy退出0，capture envelope记录退出0，分别保留含义。

原主导航HTTP200、domcontentloaded/容器ready；原permissions响应有原主框预留网络关联、HTTP200与有限接受业务投影，当前VIEWER组合准入。activeprofile0、账号字段NOT_OBSERVED、配置读取/登录0。一次官方上下文query准备/绑定/read intent、send recheck=BOUND_CONTEXT_UNCHANGED，账户/query/token值未导出。此成功不证明之前空查询的角色/权限/筛选原因，旧原因继续UNKNOWN。

canonical records选中唯一id46007447，书名为 `0917-136-9787555396581-名校课堂八年级数学上册`，返回page_count214/question_count22。book/directory/frames/source/page14/page173六个不同逻辑槽均有独立HTTP200/code0/VALID_JSON有限事实。实际frames为NUMERIC_CODE_0/DATA_ARRAY；实际source明确LEGACY_DB、返回file_id匹配，非frontend缺省。两legacy页各一次，OSS页JSON分支未选、NOT_RUN，不额外计额度。

独立交叉计数：121目录、22题节点、68个唯一框（无orphan），raw与单独frontend DFS序列均为1—22/max22，重复及差异均0。Q22自然留库存，没有导航/样题/正文/重放。库存仍PARTIAL、正文覆盖UNKNOWN、write_preservation_baseline=false、append_after_order=null；计数/框覆盖不能证明完整旧正文、合法插入或save order。

| Viewer | 实际返回resource | JPEG尺寸 | 字节 | 原图SHA256 |
| --- | --- | --- | --- | --- |
| 14 | 13 | 1218×1694 | 396099 | `4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9` |
| 173 | 172 | 1148×1621 | 428192 | `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be` |

legacy响应投影、对应raw-response hash、注册原图与private-originals manifest的索引/摘要/尺寸一致。13/172为本轮legacy返回字段，不以OSS viewer-1推导替代。执行产品记录full_pixel_decode=true，归档记录size/hash核证；独立只核记录，不读取私有原图、不新下载或解码。

mapping14/173 DONE仅表示被动检查完成：两项visible_status与save_page_status均UNKNOWN、save_page=null。body/schema UNKNOWN，sample/info/三个正文zone均NOT_RUN，production_ready/write_eligible=false。完整旧正文保全、当前未录入候选、文字/bbox、目录合法插入、save-page转换、裁片/上传整数、save/receipt/readback合同仍未证明；没有实际保存、OCR或模型调用。

## 请求与释放边界

audit30是观察事件，不是30个HTTP请求。独立核六种不同BUSINESS native逻辑预留及两原图预留，六JSON实际HTTP状态另有原件。version native/context各1不等于HTTP成功，仍UNKNOWN；共享排除事件1/限16、已完成拒绝1，辅助发送总量及DNS/TCP/TLS/脚本必要性UNKNOWN。

两legacy URL的known_route均标page173，原因是既有按path标记碰撞；原件保留。BUSINESS_PAGE14/PAGE173类别、独立槽及显式viewer/resource记录分别对应，未因此重跑或修产品。图像HTTP200只可沿冻结成功控制流及缓存/完整解码前置条件推知，未单独存raw状态，不称独立重新抓包。

product47000、worker20552、occupancy28004前后PID+created_filetime一致，exit_observed/exit0、各持有句柄关闭均有原件。两自有Job最终active0/closed，context_closed/runtime_stopped=true、errors空，pending0，未记录超期。仅接受这些有身份的自有资源释放，不扩为全机/profile清理。outer launcher9096退出0有采集观察，自身OS创建身份UNKNOWN。

outer stdout135原字节与摘要匹配；product stdout90仅计数/摘要、原字节不可用；stderr原件公开未保留的限制不补造。单调钟/UTC/FILETIME各自记录与差值保留，原因及精确分解UNKNOWN。所有actual/raw/claim/window原件不修改。

本次一条静态元数据命令因Split-Path参数组合在路径初始化失败，无报告输出或产品动作；改用.NET路径后静态核证完成。原工具错误转录在metadata-first-error.json，未重跑任何产品、suite、capture/archive或真实请求。

## 收口与独立释放

本修订实际used1/remaining0/retry0；原A24旧轮也remaining0，不恢复窗口/额度/标记或自激活。作者在同阶段并行的首题离线实现不属于本次被冻结只读产品，后续另固定交付并独立核证。真正保存仍须完整具体新题/policy/payload/写集/整数预算与适用许可/activation；本报告不准新读取或写入。

本次只用静态读/hash/JSON核对及报告写入，suite/产品导入/作者helper/产品launcher/browser/network/profile/credentials/native/occupancy均0；未读作者活动目录、Script/sidecar、私有响应或原图。输出仅指定独立目录，原92输入不变，没有保留进程/会话/句柄/等待helper，0外部消息/推送。其他三例HOLD，Q22不重放。固定报告及清单后释放。
