# A24 book 正文私有落盘补丁独立差量审查

## 结论

`PASS_SOURCE_AND_SYNTHETIC_SCOPE_LIVE_UNVERIFIED`

作者补丁在源码差量与有限合成测试范围内通过。它没有新增 GET、没有改变鉴权/guard、没有改变写资格、没有保存请求头或凭据，也没有覆盖已有私有原件。实际网页本轮仍为 0 业务 GET / 0 写；没有真实 schema，因此本结论不是 live、平台、人工或官方验收。

## 精确差量

补丁只修改 `src/annotation/runtime/live_pilot/owner.py` 的 `acquire_current_schema` 一个 hunk：

1. 四个既有响应槽 `book/directory/frames/export` 均将 `response["body"]` 按 UTF-8 编码后保存到 `authority.output/private/<slot>-snapshot.bin`。
2. 原先仅保存后三槽的条件被移除；请求列表、顺序、路由、参数、`authority.check()`、`GET` 方法和 `phase="acquire"` 均未改变。
3. 观察记录和 `controlled_raw_ref` 新增 `capture_representation="UTF8_REENCODED_RESPONSE_TEXT"`，明确不把它声称为 native HTTP raw bytes。
4. 继续使用 `open("xb")`，已有文件立即失败且不覆盖。
5. `write_allowed=False`、`successors="NOT_RUN"` 未改变。HTTP 非 200 在编码和落盘前触发 `OWNER_FIRST_SAVE_BLOCKED`；异常使 `run_owned_worker` 跳到错误处理，不能进入 adapter。

## 安全边界

| 检查项 | 结果 | 依据 |
|---|---|---|
| 新增 GET | PASS：0 | 四项 requests 列表未修改，成功路径仍恰好 4 GET |
| 鉴权 / guard | PASS：无变化 | 补丁 hunk 不涉及 authority、binding、guard 或 session |
| 写资格 | PASS：无变化 | unbound 结果仍 `write_allowed=false`、`successors=NOT_RUN`；失败不返回结果且 caller 不进入 adapter |
| 凭据/请求头泄漏 | PASS：未发现 | 公共 observation 仅含 slot、path template、query key 名、状态、长度、哈希、representation 和私有引用；未持久化 headers、token、cookie 或 query 值 |
| 响应正文暴露 | PASS：仅私有目录 | 正文字节只写到 owner-controlled `private` 目录；公开结构只含引用、长度和哈希 |
| 覆盖原件 | PASS：拒绝覆盖 | `xb` 独占创建；作者原测试与独立复测均通过 |
| 原始字节表述 | PASS（限定） | 明确标为 UTF-8 重编码文本；不得把这些文件称作原始 HTTP 压缩/传输字节 |

## 独立补充负例

在我方隔离副本应用补丁后，增加“第三个 GET 返回 503”负例：

- 只发出 book、directory、frames 三个 GET，export 不再发送；
- book、directory 两份已经成功取得的私有证据保留且字节正确；
- frames、export 文件不存在；
- 抛出 `OWNER_FIRST_SAVE_BLOCKED`；
- 没有 POST，函数未返回任何可把 `write_allowed` 置真的结果，caller 无法进入 adapter。

连同作者三项测试共运行 4 项，全部通过；未运行旧大型套件。

首次启动因隔离源码树未设置 `PYTHONPATH=src` 而在测试收集阶段报 `ModuleNotFoundError`，未进入被测代码。补足实际源码导入路径后，4 项测试正常通过；该启动错误不计为产品失败。

## 哈希与行尾说明

- 作者 patch SHA-256：`b52a9d820ddb9a4edf5a6b43357566851f588804941d5e807d72e8019b43a7e6`
- 基线 owner SHA-256：`fb5bcd815d075f425d97845da13b64c2e06f62ecb990f41924377dadea8aeaaf`
- 作者 LF owner SHA-256：`dc5113d1984c58d63ea3a26b95d45664aed60a0915a31b9f4afab592169e1318`
- 我方 CRLF 副本应用后的原始 SHA-256：`f21e48c53aeb238b5fe629c642f5fb322f47e2b50c8bb382b2c5ff4dda446f55`
- 我方文件规范化为 LF 后 SHA-256：`dc5113d1984c58d63ea3a26b95d45664aed60a0915a31b9f4afab592169e1318`
- 独立扩展测试 SHA-256：`3af68d67fe779c1b054a2b4b2a2277577c55b6c32956544166b319251a6f1210`
- 额外负例 patch SHA-256：`834bf9a2feed9ae99eb323acef5dbd9025af14561d0e7756330e1ff7ba53cd8c`

我方与作者 owner 文件用忽略行尾的逐行 diff 比较无差异；整文件 SHA 不同仅由 CRLF/LF 造成，统一 LF 后与作者声明哈希完全一致。

## 未证明边界

本审查没有获得当前真实 book、directory、full frames、natural export 响应和逐文件 manifest。因而仍不能验证真实字段映射、全量旧题/框分母、五区与 info/meta 完整性、HTTP raw bytes 身份、保存后保全效果或独立 reopen。此前旧题保全 HOLD 结论不变。
