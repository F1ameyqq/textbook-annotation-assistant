# A24 本机接管：固定离线重建与重放包

日期：2026-10-22，Asia/Shanghai。工程输入B提交 `150a82d645fddcbb9a62508cf359150ec3c6cb90`；固定A24 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`。本增量落实已完成的本机修复和交接，不扩展预框工具，也不等待A恢复编码。

用户暂时不方便查看平台导出入口，本轮无需用户执行网页步骤。来源成员保持停止，未重试调试连接、原生控制、HTTP或其他采集通道；沿用[登录后只读阻断事实](a24-readonly-acquisition-20261022.md)。

## 固定交付及真实范围

[离线包](../handoffs/b/a24/a24-offline-replay-20261022-v2-final.zip)，2,034,326字节；SHA-256：

```text
c4ad1b298dd34a8b0a5ec8706a3514fefe19d9a33582cd27fa826ef1a94ec89e
```

压缩包531个文件；根清单自排除后530项。三个不同分母分别是：

|集合|范围及绑定|
|---|---|
|`baseline/`|原A24公开522成员，9,060,211字节；逐项保持原文件字节，不包含本机额外status、私有业务原件、profile或缓存|
|`manifests/baseline-original-manifest.json`|原清单另存；SHA `a927a201988a277520275509791401e00cc45fdd9edcde140056bf85060633a9`，原522分母自排除该清单|
|`overlays/`|恰好3文件：替换owner及minimum-gate夹具，新增book-snapshot测试；不是再次改写A原件|
|有效源码树|原522替换2、增加1，合计523；effective清单SHA `c92e891b9644f1a24c6352a40ba4abc8691f76390ad892ad6b81209a84c50fe0`|
|包根清单|SHA `0770e2a17278a8f046e224d178113e0cbcebc08e206d5e56a2501c1833572d56`，绑定脚本、说明、基线、覆盖层与三个内层清单|

原清单放在源码树之外，不谎称它覆盖修改后的owner。主会话另对照原522和当前隔离副本，确认只有上面三份覆盖文件，摘要与上一轮已审修复完全相同。详细摘要及原始回执见[机器记录](../evaluation/a24-offline-replay-20261022.json)。

## 复现入口

先核对整个ZIP的上述SHA，再解压至尚不存在的新目录。`a24-offline-replay/offline_replay.py` 仅提供 `verify`、`rebuild`、`test`；不调用live启动器，不生成或激活线上配置。

本机已有且实际使用的运行时为：

```powershell
$a24ReplayPython = 'C:\Users\LIHAOYANG\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$a24ReplayPackage = 'C:\path\to\fresh-extracted\a24-offline-replay'
$a24ReplayRun = 'C:\path\to\fresh-run'
& $a24ReplayPython -B "$a24ReplayPackage\offline_replay.py" verify
& $a24ReplayPython -B "$a24ReplayPackage\offline_replay.py" rebuild --target "$a24ReplayRun\source"
& $a24ReplayPython -B "$a24ReplayPackage\offline_replay.py" test --tree "$a24ReplayRun\source" --report-dir "$a24ReplayRun\reports" --temp-dir "$a24ReplayRun\long-temp"
```

替换示例路径即可；source/reports/long-temp均须事先不存在。使用规范长路径，避开Windows 8.3 TEMP别名。复用已安装的Python3.12.14、Pydantic2.14.1、Pillow12.3.0，没有安装或下载；尚未做空白机器安装，也不能称原A Python3.9/浏览器环境等价。

`test` 在创建输出目录和导入待测源码之前核对必需包根清单及有效树全部523文件的集合、长度和SHA。只向显式的新目录写入；拒绝覆盖已有结果。失败回执保存测试ID和原traceback，保持失败证据。

## 发布前审查与更正

首版ZIP SHA `21b4e9f22910469c0af9592de944a919e0c0ac8895bd7b2d8c8fbdf895bb8435` 已退回，不作为发布件：第一组误选另一个同样7项的bootstrap-exclusion套件；test未先绑定有效源码；根清单可缺省；失败仅计数；Windows相对路径门不足。主审和质量成员的拒绝记录归档在[本轮证据](evidence/a24-offline-replay-20261022/first-version-rejection.json)。旧ZIP和中间草案留存在成员及主工作区，不覆盖、不以旧通过回执验证最终版本。

最终版改用controlled-capture，强制必需清单及全树校验，保留原traceback；拒绝盘符、冒号、反斜杠、空/点段、保留设备名、尾点空格及casefold重复。没有为交接扩大成通用沙箱工具。

## 实际验证和限制

作者从最终ZIP重新解包重建后运行：controlled-capture 7、minimum-gate 10、book-snapshot 4，共21项通过。主会话另从相同固定ZIP安全解包，逐项验证523文件，并实际通过三项拒绝检查：已有目标不改动、篡改owner在导入和创建输出前拒绝、缺必需根清单拒绝。[主审命令及原始输出](evidence/a24-offline-replay-20261022/main-review.json)保留确切退出码。

质量成员随后从同一固定ZIP独立安全解包531文件，核对基线/覆盖/根清单，实际重建523文件并运行正确三组21/21通过；测试后523文件全量哈希仍一致，已有目标重建退出码1且原树不变。[独立报告](evidence/a24-offline-replay-20261022/independent-final-report.md)、[机器回执](evidence/a24-offline-replay-20261022/independent-final-receipt.json)及[本次原始测试回执](evidence/a24-offline-replay-20261022/independent-final-raw-tests.json)均保留。结论仅 `PASS_OFFLINE_REPLAY_ONLY_LIVE_HOLD`，不是独立人工内容验收。

有限防护范围为已有 `asyncio MemoryPolicy` 加 `socket.create_connection`、`socket.socket.connect`、`subprocess.Popen`、`urllib.request.urlopen` 入口。固定套件使用合成浏览器/响应与mock，不是OS文件系统沙箱，也不能证明所有可能IO入口都被阻断。未新增OCR、外部模型API、平台业务读取、标注写入或下载。团队使用既有Codex会话，不宣称零模型消耗。

## 仍待真实来源验证的主线

当前 `CURRENT_SCHEMA_UNBOUND`、`write_allowed=false`、live后继 `NOT_RUN`，整体HOLD。当前书籍身份、完整目录/旧题/题框/自然导出、保存请求及目标裁图均未因本包补齐；真实字段适配、完整旧题保全和fresh独立重开尚未证明。

本包可让接管方在新路径恢复同一修复版本，但不能启动网站标注。历史authority、activation和候选依赖哈希不能复用；将来获取真实输入后须重新固定实际依赖、目标范围和精确前检。既有Q16/阅读内容包、Q9缺题页、章节分母和独立人工核对仍按各自证据保留，未宣称章节交付或A侧接收通过。
