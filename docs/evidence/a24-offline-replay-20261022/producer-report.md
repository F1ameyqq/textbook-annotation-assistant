# A24 离线重建/重放包 v2-final

日期：2026-10-22（Asia/Shanghai）

## 最终发布件

- ZIP：`a24-offline-replay-20261022-v2-final.zip`
- 字节数：`2034326`
- SHA-256：`c4ad1b298dd34a8b0a5ec8706a3514fefe19d9a33582cd27fa826ef1a94ec89e`
- root manifest SHA-256：`0770e2a17278a8f046e224d178113e0cbcebc08e206d5e56a2501c1833572d56`
- effective manifest SHA-256：`c92e891b9644f1a24c6352a40ba4abc8691f76390ad892ad6b81209a84c50fe0`

旧 v1 和 v2 草案 ZIP 均保留、未覆盖；它们已被本发布件取代，不应继续分发。

## 修订内容

1. 7 项首组改为本轮实际集成的 `controlled_capture`，测试组合为 controlled-capture 7 + minimum-gate 10 + book-snapshot 4。
2. `test` 在创建报告/临时目录或导入测试模块之前，强制校验包的必需 root manifest，并要求 `--tree` 的完整文件集合、长度及 SHA-256 精确匹配 effective 523。
3. 测试失败回执保留测试 ID 和 unittest 提供的原 traceback，不再只保留计数。
4. `verify` 不再允许缺失 root manifest。
5. 路径检查拒绝盘符/冒号、反斜杠、空段、`.`、`..`、Windows 保留名、尾随点或空格，以及 casefold 重复。
6. README 和回执明确：MemoryPolicy 与被 patch 的入口只是有限防护，不是 OS 文件系统沙箱，也不能证明所有可能 I/O API 均被阻断。

## 最终 ZIP 实际复验

最终 ZIP 被解压到全新目录后：

- 包清单校验：PASS，root 必需且已检查；
- effective 重建：523/523 文件及哈希 PASS；
- 固定合成测试：21/21 PASS；
- 套件：controlled_capture 7、minimum_gate 10、book_snapshot 4；
- 路径负例：8 个非法路径加 1 个 casefold 重复，共 9 项均拒绝；
- 向已验证树增加额外文件后，`test` 在创建 report/temp 目录之前拒绝；
- 失败记录字段已包含 `test_id` 与 `traceback` 数组契约。

保护范围仅限 `asyncio MemoryPolicy`、`socket.create_connection`、`socket.socket.connect`、`subprocess.Popen`、`urllib.request.urlopen`。这 21 项固定测试中未观察到这些被防护入口被调用；这不是全 I/O 隔离声明。

## 解压后运行

在解压得到的 `a24-offline-replay` 目录内：

```powershell
python .\offline_replay.py verify
python .\offline_replay.py rebuild --target C:\path\to\a-new-effective-tree
python .\offline_replay.py test --tree C:\path\to\a-new-effective-tree --report-dir C:\path\to\a-new-report-dir --temp-dir C:\path\to\a-new-long-temp-dir
```

三个输出路径必须是尚不存在的新路径。

## HOLD

该包只证明固定公开成员能够离线校验、重建并通过上述合成测试。它不证明当前真实平台格式、自然导出兼容、完整 I/O 隔离或平台验收；不得标记 `VERIFIED`、解锁写入或运行 live 启动/激活。
