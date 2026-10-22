# A24 离线重建重放包 v2-final 独立验收

## 结论

`PASS_OFFLINE_REPLAY_ONLY_LIVE_HOLD`

v2-final 已从固定 ZIP 身份开始完成独立安全解包、包清单校验、全新 523 文件重建和本次实际 21 项合成回归。三组均零失败、零错误；测试后再次逐文件核对 effective manifest，523/523 仍一致。重建到已存在目标按预期拒绝且原树未变化。

这只证明固定公开成员的离线重建与合成回归。`CURRENT_SCHEMA_UNBOUND`、`write_allowed=false`、`successors=NOT_RUN` 和总体 HOLD 不变；不构成 live、平台、写授权、人工或官方验收。

## 固定输入

- ZIP 字节数：`2034326`
- ZIP SHA-256：`c4ad1b298dd34a8b0a5ec8706a3514fefe19d9a33582cd27fa826ef1a94ec89e`
- root manifest SHA-256：`0770e2a17278a8f046e224d178113e0cbcebc08e206d5e56a2501c1833572d56`
- effective manifest SHA-256：`c92e891b9644f1a24c6352a40ba4abc8691f76390ad892ad6b81209a84c50fe0`
- ZIP：531 个普通文件，展开 9,641,605 字节，CRC 全量通过。

旧 v1 `21b4e9f…` 没有参与本次重放，旧结果未继承。

## 安全解包与清单

独立解包器先在 central directory 阶段检查路径逃逸、盘符/UNC、反斜杠/ADS、NFC 与 casefold 冲突、Windows 保留名、尾随点空格、文件/目录前缀冲突、加密成员、symlink/special 成员、展开大小/压缩比和 CRC。全部通过后才向事先不存在的目录逐文件 `xb` 创建。

root manifest 必需且逐项绑定其余 530 个成员；包内 verifier 随后独立得到：baseline 522、overlay 3、effective 523、root checked，状态 PASS。

## 实际重建与回归

重建目录：

`work/a24-offline-replay-v2-final-independent-20261022/effective-tree`

实际新建并验证 523 个文件。测试入口再次强制验证 package 与整棵 effective tree 后运行：

| 套件 | 实跑 | 失败 | 错误 | 结果 |
|---|---:|---:|---:|---|
| controlled_capture | 7 | 0 | 0 | PASS |
| minimum_gate | 10 | 0 | 0 | PASS |
| book_snapshot | 4 | 0 | 0 | PASS |
| 合计 | 21 | 0 | 0 | PASS |

运行时为 bundled Python，Pydantic `2.14.1`、Pillow `12.3.0`。原始本次测试回执 SHA-256：`ee4a8555816b783316a14054c456bab72c4f95518e37e8a07fda83fb06efd724`。

三个测试入口已静态核对：controlled-capture 使用 synthetic owner/framework；minimum-gate 使用 synthetic authority 与 mock 的 Playwright/child；book-snapshot 使用 fake `CurrentPageIO`。历史 authority 文件仅作为基线字节被清单核验，没有作为授权输入复用。

## 入口 guard 与观察边界

测试 runner 声明并安装的有限 guard 为：asyncio `MemoryPolicy`、`socket.create_connection`、`socket.socket.connect`、`subprocess.Popen`、`urllib.request.urlopen`。21 项中未观察到这些入口被调用。

该结论不把猴补丁描述为通用 OS 沙箱，也不证明所有可能 I/O API 均被阻止。实际观察到的新增文件仅位于本质量工作区的新目录：解包 531、effective 523、test report 1；测试结束后 test-temp 无文件。未操作浏览器、平台、live authority、模型或共享仓库。

## 有限负例

再次要求 rebuild 写入已经存在的 effective-tree 时，命令以退出码 1 和 `FileExistsError: rebuild target already exists` 拒绝；随后对原树重新执行 523 项完整哈希核对，仍为 PASS。

更完整的篡改树/非法路径拒绝矩阵由主审单独执行，本报告不重复或代报其结果。

## 保留边界

本轮仍没有当前真实 book、directory、fullframes、natural export 原件及清单。因此没有证明真实字段映射、旧题与框完整分母、保存效果、独立 reopen 或 HTTP 原始字节身份。离线包可以移交用于可重复的源码/合成验证，但不得据此解锁写入或提升为平台已验证。
