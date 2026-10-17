# A04 coordinate-R3 执行交付：REVIEW

2026-10-17（Asia/Shanghai）。本轮完成一次缺行 PNG 的有界离线修复，交回主调度安排独立复验。**这是执行者交付，不是验收通过；整个 A04、S01 完整性以及真实 R01～R06 均未释放。** D01 是主调度另行接受的安装事项，本轮没有重新处理。

## 版本、范围与复现输入

- 固定 workflow：`99bae146ee01525005f269dfde27f507d9e8124c`。
- 原交付基线：`76898657e76ac2db071327e90c6ca5031d17571f`。
- 实现冻结提交：`81d62255b545b88f344849d08011a2a859c49c5e`。
- 交付提交为本报告及清单归档后的提交，确切完整 SHA 随最终交付回执提供；实现不随归档改动。
- 工作目录：`C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800`；分支 `codex/a04-headless-readonly`。没有合入浮动主树、推送或修改主调度目录。
- 固定任务 Git 字节 SHA256：`f2aed3c85b06509e524b1403fbebeaa2174bc89e3f796a65e8a9440075ba38bd`。[固定文档、复验脚本摘要及原始副本](../evidence/A04/execution/coordinate-R3/fixed-inputs.json)包含 R3 任务、AGENTS、coordination、R2 独立报告、主调度决定及 checks。
- Python 3.9.13、Pillow 11.3.0；没有新增或升级依赖。[实现文件、Git blob 与磁盘摘要](../evidence/A04/execution/coordinate-R3/version.json)。

产品改动仅为来源模块的 `parser.py` 和新增 `png_pixels.py`；新增对应 `tests/test_a04_png_r3.py`。公共合同、source/static、geometry、delivery、根依赖和调度 state 未改动。新证据均在 `docs/evidence/A04/execution/coordinate-R3/`；其中 `frozen-product/` 是实现提交中 36 个源码／夹具文件的原始 Git 字节导出，不是公共模块的新实现。

## 缺陷与修复判据

未修改独立复验者的 `repro_incomplete_rows.py`，并保留其原始 `offline_guard.py`。精确反例是 180 字节、37×29 RGB8 PNG，SHA256 `205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd`；CRC 和 zlib EOF 都有效，但解压仅 112 字节，声明布局需要 3248 字节。

| 执行位置 | 复现脚本退出 | 产品 CLI 退出 | 最终包／公共 loader |
| --- | --- | --- | --- |
| 原 R2 基线 | 1（缺陷存在） | 0 | 生成并接受 |
| R3 工作树 | 0（缺陷未重现） | 2 | 不生成 |
| R3 原始 Git 字节隔离导出 | 0 | 2 | 不生成 |

[修复前原始结果](../evidence/A04/execution/coordinate-R3/before-exact-repro/result.json)、[修复后工作树结果](../evidence/A04/execution/coordinate-R3/after-exact-repro/result.json)、[原始 Git 字节复现](../evidence/A04/execution/coordinate-R3/after-exact-raw-git-repro/result.json)均保留 Pillow verify/load 仍接受该反例的事实。失败位置固定为 `$.pages[0].asset_path`；CLI 仅输出 `A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path`。发布复查位置为 `$.pages[0].path`。

新门禁在共用 `_image_inventory` 中执行，所以来源解析和 `build_source` 发布前复查都会经过它，且在写入来源历史之前失败。PNG 检查包含：

1. 受限读取原始字节，校验 chunk 长度、顺序、CRC、唯一 IHDR、连续 IDAT、终止 IEND；不接受未知 critical chunk、尾随内容或 APNG。
2. 从实际色型、位深和交错声明推导行宽。普通 PNG 每行要求 `1 + ceil(width × channels × depth / 8)` 字节；Adam7 按七个有效 pass 分别计算，空 pass 不消耗过滤字节。
3. 有界 zlib 解压，要求恰好等于上述总量、流正常结束且没有额外压缩流或尾随数据；每行过滤类型须为 0～4。对索引色逐 pass 逆过滤、重置上行状态，再核对实际像素的调色板索引；忽略合法 packed padding。
4. 继续执行既有 Pillow strict verify/load、原始格式／尺寸核对、SHA256 和发布前身份复查。不修改全局容忍设置，不重编码或修补输入，也不使用空白／色差阈值。

R2 的 `GEOMETRY_DEPENDENCY_ACCEPTED`、`GEOMETRY_NOT_PERFORMED`、`ACCEPTANCE_NOT_ASSERTED` 语义保留；本轮没有执行坐标验收。

## 支持组合、资源限制与兼容影响

以下是静态 PNG 的支持矩阵，每种均支持普通行和 Adam7，合计 30 种布局：

| 色型 | 位深 | 已执行覆盖 |
| --- | --- | --- |
| 0 灰度 | 1、2、4、8、16 | 两种交错 × 五种过滤 |
| 2 RGB | 8、16 | 两种交错 × 五种过滤 |
| 3 索引色 | 1、2、4、8 | 两种交错 × 五种过滤，含索引及 padding 边界 |
| 4 灰度＋alpha | 8、16 | 两种交错 × 五种过滤 |
| 6 RGBA | 8、16 | 两种交错 × 五种过滤 |

150 个组合／过滤样例均经过门禁和 Pillow load；另测 1×1、1×9、9×1、2×2、3×5、8×8、9×9 的 Adam7 空 pass／行取整边界。测试生成器通过物理像素坐标分配 pass，独立于产品的 pass 尺寸公式。30 种布局另经过来源入口与发布复查、公开 CLI 和搬运消费。

明确拒绝：非法色型／位深、非零 compression/filter method、interlace 不为 0/1、APNG 的 acTL/fcTL/fdAT、未知 critical chunk、缺失或非法调色板／透明声明、非法过滤／索引、损坏 CRC、缺行／多像素、未结束或附带额外内容的 zlib 流、chunk 顺序错误及超过资源上限的输入。APNG 和尾随字节的拒绝是本轮显式兼容收紧。

固定上限：PNG 文件 64 MiB、声明像素 32 Mi、单边 32768、合计解压 scanline 128 MiB、chunk 16384。先检查尺寸和预期总量，再进行有限解压；PNG 读取最多获取文件上限加 1 字节以识别超限。资源单测用缩小后的上限分别核对“恰好达到”和“少 1”边界，并用真实配置下超限的 IHDR 验证提前拒绝；没有分配 128 MiB 做压力测试，也没有测量进程 RSS 峰值。

JPEG／PGM 保留既有严格解码路径并通过正常公开入口和搬运消费。本轮新增的独立行数证明仅适用于上述静态 PNG；没有据此声称 JPEG／PGM 的所有损坏组合或所有 PNG ancillary metadata 都已穷尽验证。未知图片格式仍失败关闭。正常 16 位 RGB／RGBA 可能由 Pillow 转换内存表示，但发布资源始终保留原始字节、声明位深与哈希，没有把转换后的像素另存为原图。

## 验证、可消费样例和命令

| 检查 | 结果 |
| --- | --- |
| A04 回归 | 169 项：168 执行通过，1 个未改 Node deadline 测试明确跳过 |
| 公共合同回归 | 70 项：69 执行通过，1 个未改 Windows junction fallback 测试明确跳过 |
| 新增 R3 测试 | 17 项全部通过，包含上述组合 subtest |
| 公开 CLI 正例 | 33：30 种 PNG 布局＋37×29 全空白 PNG＋JPEG＋PGM |
| 公开 CLI 反例 | 8：精确反例、4 种不同尺寸／行宽／交错缺字节、多像素、正确总量但非法过滤、APNG |
| 发布前替换 | 正常 37×29 解析后换成同尺寸精确缺行反例，RESOURCE_INVALID；无历史写入 |
| 新进程搬运消费 | 33 包均通过未改 C01 loader、原始字节摘要和 Pillow 解码检查 |

[A04 结果及跳过项](../evidence/A04/execution/coordinate-R3/a04-regression/result.json)、[合同结果](../evidence/A04/execution/coordinate-R3/contract-regression/result.json)及各自 `*-logs/` 中保存完整 stdout、stderr、argv、PID 和守卫记录。跳过项是本轮离线 Python-only 执行边界，不记为通过。

[公开矩阵清单](../evidence/A04/execution/coordinate-R3/public-matrix/result.json)逐项保存输入、命令、退出值和拒绝后的历史／输出缺席。[33 包可搬运清单](../evidence/A04/execution/coordinate-R3/public-matrix/consumable.json)的相对路径指向 `consumer packages with spaces/`；[新进程消费结果](../evidence/A04/execution/coordinate-R3/public-matrix/consumer/result.json)保存身份和状态回读。每个 PNG 正例另有独立构造的行数／字节记录。PGM 文件名中的扩展名不参与格式判断，绑定采用原始 bytes、media type、尺寸和摘要。

原反例可在 PowerShell 离线复现（必须使用新的输出目录）：

```powershell
$r3Root = 'C:\Users\ASUS\.codex\worktrees\a04-headless-readonly\1800'
$r3Evidence = Join-Path $r3Root 'docs/evidence/A04/execution/coordinate-R3'
$r3Output = Join-Path $env:TEMP ('a04-r3-' + [guid]::NewGuid().ToString('N'))
python -X utf8 -B (Join-Path $r3Evidence 'fixed-inputs/repro_incomplete_rows.py') --root (Join-Path $r3Evidence 'frozen-product') --output $r3Output
```

预期 wrapper 退出 0；新 `result.json` 内产品退出 2、`final_bundle_created=false`、`defect_reproduced=false`。这里的 wrapper 0 仅表示此精确缺陷未重现。原始精确 argv 见 [Git 字节复现命令](../evidence/A04/execution/coordinate-R3/after-exact-raw-git-command.json)；[公开矩阵命令](../evidence/A04/execution/coordinate-R3/public-matrix-logs/command.json)和两个回归 `*-logs/command.json` 均含完整参数。重新执行矩阵或回归时也须改用新的 job／output 名，避免覆盖已有证据。

## 失败记录、保全与收尾

首轮新增测试夹具为 30 种输入复用了不可变历史路径，得到 29 个 IMMUTABLE_RESOURCE 错误；随后改成每个样例独立历史路径。第一工具输出有截断，保留了修正前测试原件及未改夹具的完整失败重放日志：[attempt-01](../evidence/A04/execution/coordinate-R3/attempt-01-test-fixture/result.json)。两次 launcher 参数解析失败在启动产品之前发生；已改为以 `--` 分隔子命令。一次 Windows rg 通配符参数错误也已修正，均如实列于 [工具失败记录](../evidence/A04/execution/coordinate-R3/tool-attempts.json)。

第一次 PID 收尾脚本仅按数字判断，把已完成 launcher 的复用 PID 当作仍活动而退出；[原脚本与失败输出](../evidence/A04/execution/coordinate-R3/attempt-02-closeout-pid-reuse/stderr.txt)保留。修正后只对本轮记录的 PID 查询退出码与创建时间：60 个已不存在，另 1 个创建时间晚于原退出记录，确认为新进程复用了 PID，未操作该新进程。全部 61 个有记录的自有工作进程已结束；父工具调用也均同步结束。[结束证明](../evidence/A04/execution/coordinate-R3/process-release.json)。未扫描全系统进程，未读取 profile；`profile_current_state=NOT_INSPECTED`。

[历史证据保全](../evidence/A04/execution/coordinate-R3/old-evidence-preservation.json)重新核对原执行、R1、R2 三份原始清单共 306 项，摘要和长度全部保持；三份清单本身与基线 Git 字节相同。原 R2 作者／验收失败和主调度首次 EOL 预检失败均未改动。新的 [SHA256 清单](../evidence/A04/execution/coordinate-R3/sha256-manifest.json)覆盖本轮证据、报告和实现文件，自身明确排除。

全部操作离线。未使用浏览器、平台、登录、profile、网络、OCR 或模型；没有重试 GET、操作书籍、重放题 22、推送，或向 B／验收者发消息。真实 R01～R06 仍 BLOCKED；后续由主调度决定独立复验及集成。
