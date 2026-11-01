# A24 book 响应快照最小修复回执

日期：2026-10-22（Asia/Shanghai）

## 结论

已在自有隔离副本中完成 `acquire_current_schema` 的最小修复，未修改固定源、B 共享仓库或网站：

- 固定的四个 GET 路由、顺序和数量保持不变；成功路径仍严格为 4 次 GET。
- `book` 响应现在与 `directory`、`frames`、`export` 一样保存到 `private/book-snapshot.bin`。
- 四份证据均明确标记为 `UTF8_REENCODED_RESPONSE_TEXT`，表示它们来自 `response["body"]` 文本的 UTF-8 重编码，不宣称是网络层原始压缩字节。
- 继续使用 `xb` 独占创建；已有文件时拒绝并保持旧字节不变。
- HTTP 非 200 在正文编码和落盘之前停止；未知 schema 仍为 `write_allowed=false`、`successors=NOT_RUN`。
- 没有新增 GET，没有改变鉴权、guard、写资格，也没有持久化请求头或查询值。

## 定向合成回归

使用指定的 bundled Python 3.12.14，仅运行新增测试：

```text
test_existing_output_rejects_without_overwrite ... ok
test_four_gets_save_four_utf8_reencoded_bodies_and_digests ... ok
test_http_failure_stops_before_any_snapshot_or_later_request ... ok

Ran 3 tests
OK
```

覆盖内容：四份正文逐字节读取和 SHA-256 核对、成功请求数恰为 4、重复输出拒绝且不覆盖、首个 HTTP 失败后只发出 1 个请求且不创建快照、未知 schema 不解锁写入。

## 文件与哈希

- 固定源 `owner.py` SHA-256：`fb5bcd815d075f425d97845da13b64c2e06f62ecb990f41924377dadea8aeaaf`
- 隔离副本修改后 `owner.py` SHA-256：`dc5113d1984c58d63ea3a26b95d45664aed60a0915a31b9f4afab592169e1318`
- 新增定向测试 SHA-256：`26d2a4d98bf1ffefad1e920c91284e285734d68681e7642f1db3443ac770c3c8`

## 任务 2 状态

已只读检查来源成员工作区。最新机器回执仍写明：`book`、`directory`、`fullframes`、`natural_export` 全部 `NOT_RUN`，`manifest_status=NO_SOURCE_INCREMENT`；目录中没有本轮真实响应原件和对应清单。因此目前不能进行自然导出、五区内容/元数据、旧题/frames、identity/legal、append/savepage 的真实格式适配，也不能把 DOM 文本当作下载原件。

继续适配前仍需来源成员交付：当前真实 book、directory、full frames、natural export 四份响应正文，以及逐文件记录字节数和 SHA-256 的 manifest。收到并校验这些原件前，不猜字段、不置 `VERIFIED`、不解锁写入，首目标保持 `dir-1792063578574-g0n3ulsni`。
