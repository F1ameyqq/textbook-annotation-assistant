# A04 coordinate-R3 独立离线复验报告

2026-10-17（Asia/Shanghai）。**OFFLINE_R3=ACCEPTED；A04_OVERALL=BLOCKED。** 本结论只接受固定R3的缺行PNG离线修复、受检静态布局、发布前复查及有界资源行为；不接受整个A04，不集成或释放真实平台/I01依赖。

## 固定版本与输入

| 项目 | 确切值 |
|---|---|
| 被验交付 | `6c8137a4fadddc01a47906d564ab3460277c8958` |
| 实现 / base | `81d62255b545b88f344849d08011a2a859c49c5e` / `76898657e76ac2db071327e90c6ca5031d17571f` |
| 本轮验收workflow | `d834bf531f95abac7ed30b89b3ca55105fa6f491`，续派明确xhigh |
| 执行workflow | `99bae146ee01525005f269dfde27f507d9e8124c` |
| 执行报告SHA256 | `9e80fb8e715da518b1e999c951b9798ad5cb0b7dbfc12c09d325ea0f5f850334` |
| 作者清单SHA256 / 项数 | `634c254021f91ec2f6ed2b0737a3b234f4fb382c4e8878490abedf3b428d1b92` / 852 |
| 执行 / 验收对话 | `01a144cc-dde4-73a1-9e83-be485380ea25` / `01a144cc-e93d-7841-a259-d6aac22c94f4` |

先从确切workflow读取AGENTS、coordination、[R3验收任务](../evidence/A04/review/coordinate-R3/inputs/workflow/docs/tasks/A04-coordinate-R3-review-handoff.md)及[调度前检](../evidence/A04/review/coordinate-R3/inputs/workflow/docs/evidence/coordinator/heartbeat-20261017-0649/A04-delivery-preflight.json)。被验工作树全程只读；运行输入从原Git blob导至 `D:/1800/.local/stages/A04-review/coordinate-R3/frozen source with spaces`。没有使用浮动主树或checkout换行替代原字节。

[输入核对](../evidence/A04/review/coordinate-R3/snapshot-check.json)独立确认852项原Git/磁盘摘要和清单自身、853处授权范围变化、工作树干净。产品增量仅`parser.py`、`png_pixels.py`和专属测试；公共合同、geometry、source/static、delivery/runtime、根配置/依赖及父入口与base一致。原执行三份清单共306项、原准备/R1/R2复验共565项保持，旧报告与失败未改动。A01依赖仍沿用已接受的`c6bebdf43eb93f7a6ae21e96ec07ed155686777d`。

## 精确反例和独立检查

未修改原复验者的 `repro_incomplete_rows.py` 或配套guard；作者复制件与本workflow保存的R2原件逐字节相同。精确输入仍为180字节、37×29 RGB8、SHA256 `205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd`，实际112字节一行，声明需要3248字节。Pillow verify/load仍接受它，但R3公共来源入口已经拒绝。

| 证据 | 本轮结果 |
|---|---|
| [未改脚本的实际命令与原始流](../evidence/A04/review/coordinate-R3/initial/process-results.json) | wrapper退出0，表示此精确缺陷未重现 |
| [精确结果](../evidence/A04/review/coordinate-R3/exact-replay/result.json) | 产品CLI退出2，固定`RESOURCE_INVALID; LOCATION=$.pages[0].asset_path`；没有输出目录、历史或最终包 |
| [独立26项](../evidence/A04/review/coordinate-R3/independent-cases/results.json) | **26 PASS / 0 FAIL**；以下代表布局、发布、资源与兼容边界全部完成 |
| [受影响回归](../evidence/A04/review/coordinate-R3/initial/regression-result.json) | 只选`test_a04_png_r3`、`test_a04_decode_r2`、`test_a04_source`、`test_a04_cli`，**70/70**；未重复旧完整矩阵 |

独立PNG生成器按物理像素的8×8 Adam7归属表分组并打包样本，期望值不调用产品`_layout`或pass尺寸公式。7种代表布局为：灰度1bit 9×5普通行、索引2bit 7×6 Adam7/Paeth、RGB16 11×3普通行、RGBA16 9×13 Adam7、灰度16 1×9 Adam7、灰度alpha8 2×5普通行、索引1bit 1×1 Adam7且unused padding非零。每种均用独立字节/行清单核对合法总量，再验证少1字节及多1字节被拒绝，包含空pass、打包取整和高位深。

8个正常包经公开CLI发布，再复制到含空格目录，从另一cwd用**未改公共loader＋Pillow完整解码**消费；覆盖上述4个代表PNG以及全白PNG、JPEG、ASCII P2、二进制P5。真实尺寸、MIME、原始字节SHA256和相对路径绑定保持，原图没有重编码。全白PNG通过，未引入内容/颜色阈值拒绝。索引色另检验Paeth逆滤波和合法padding，非法实际palette index被拒绝。

同尺寸原图在`parse_capture`后替换为精确缺行图，`build_source`返回 `RESOURCE_INVALID / $.pages[0].path`，**写入历史前停止**；公开CLI的解析/复制之间替换也被再次拒绝，仅保留部分失败文件，没有历史或最终有效包。见 [直接发布复查](../evidence/A04/review/coordinate-R3/independent-cases/U-same-size-swap/result.json) 和 [公开复制复查](../evidence/A04/review/coordinate-R3/independent-cases/U-public-copy-swap/result.json)。不同尺寸的打包灰度和Adam7 RGBA缺字节反例也经公开入口安全拒绝，非特定hash/尺寸补丁。

## 资源上限与兼容边界

代码声明上限为PNG文件64 MiB、像素32 Mi、单边32768、解压scanline 128 MiB、chunk数16384。独立检查包括：

- 五项上限以小样本缩放到“恰好允许”和“少1即拒绝”，验证边界包含关系。
- 默认超限IHDR分别触发尺寸/像素/行字节限制；在创建解压器之前拒绝，不分配声明的巨大图像。
- 一个压缩后代表2 MiB输出、却声明154字节布局的输入，被 `max_length=155` 有界解压拒绝；禁止使用无界flush。Python分配峰值和耗时有实测记录。
- PNG限长读取用1024字节缩放上限验证：实际2600字节文件只请求`read(8)`和`read(1017)`，最多读取1025字节用于判断超限。

以上原始观察在 [独立结果](../evidence/A04/review/coordinate-R3/independent-cases/results.json)；**没有进行64/128 MiB配置极限的内存/耗时压力测试**，不把小样本和代码边界检查外推成完整性能保证。

静态PNG声明支持下列组合，每项同时支持普通行/Adam7，共30种布局：

| 色型 | 位深 |
|---|---|
| 0 灰度 | 1、2、4、8、16 |
| 2 RGB | 8、16 |
| 3 索引 | 1、2、4、8 |
| 4 灰度alpha | 8、16 |
| 6 RGBA | 8、16 |

作者测试中的150组合/过滤subtest作为回归执行，不能冒称为本轮独立样本。独立覆盖为上述7种代表，不声称逐组合独立穷举。APNG、PNG尾随内容、未知critical chunk、非法stream/布局/索引等失败关闭；本轮独立确认可被Pillow读取的双帧APNG和带尾随字节PNG仍被公开入口明确拒绝，属于已声明兼容收紧。

不证明所有PNG ancillary元数据语义、所有解码器等价、图像内容正确或所有格式完整性。JPEG/PGM沿用原解码路径，本轮只检查正常公开消费及受影响回归。CLI状态仍为依赖`ACCEPTED`、提交`c6bebdf...`、坐标`NOT_PERFORMED_BY_SOURCE`、验收`NOT_ASSERTED`、`network_used=false`。

## 复现与限制

精确反例可用下列**未改脚本**重放，输出目录须不存在：

```powershell
python -B D:\1800\docs\evidence\A04\review\coordinate-R3\inputs\unchanged-R2-repro\repro_incomplete_rows.py `
  --root 'D:\1800\.local\stages\A04-review\coordinate-R3\frozen source with spaces' `
  --output 'D:\1800\.local\stages\A04-review\coordinate-R3\fresh exact reproduction'
```

固定输入压缩包、源码逐文件摘要、完整argv/cwd、stdout/stderr、构造脚本、可搬运样例和过程记录见 [证据索引](../evidence/A04/review/coordinate-R3/README.md)。生成型脚本要求新目录，不在既有证据包反复运行。实际导入路径和现有Python/Pillow/Pydantic版本见 [环境](../evidence/A04/review/coordinate-R3/environment.json)；所有产品导入来自隔离原字节目录，没有安装/升级依赖。

Node deadline、Windows junction、旧全部合同/浏览器/坐标矩阵本轮未运行，不记本次通过；不为消除这些排除项扩大边界。D01已由主调度另行接受，本轮不重复安装验收。初次输入导出错误假定作者存在README，Git archive在运行产品前拒绝，去掉非必要路径后导出；此验收工具错误已记录，未修改任何产品或测试输入。实际产品/独立检查均无失败。

## 自有释放与结论

[进程结束证明](../evidence/A04/review/coordinate-R3/self-release.json)以 **PID＋创建时间**核对27个记录的原自有进程身份，全部结束；其中1个数字PID后来被不同创建时间的新进程复用，没有将其误判成原worker，也没有操作新进程。25份guard退出记录均无越界事件。只查询自己已知身份，不扫描全系统或任何profile。所有自有子进程已等待回收，无后台服务。作者61个进程释放记录只作为冻结历史回执核对，不代替本轮自有证明或当前profile状态。

本轮浏览器、平台、网络、登录、profile、凭据、OCR、模型及书籍动作均0；付费模型调用/花费0。不重试GET或题22，不修改产品、依赖、state、旧证据，不提交、推送、集成或联系执行者/B。额外的`sitecustomize.py`仅是自己临时stage的审计bootstrap，未替换任何冻结产品文件。

**A04_OVERALL仍BLOCKED**：真实R01新会话/目标、R02当前14/15/173原图、R03翻页返回、R04当前目录/题/框审计、R05真实查看器坐标、R06独立当次会话/释放均未运行；S01全书来源完整性仍未通过。须主调度另行明确有界续派、服务/输入条件改变和实际会话占用检查后才能开展真实验证。不得用本次离线接受推定B确认、真实保存/OCR/恢复、内容或成本通过。

[最终检查](../evidence/A04/review/coordinate-R3/closure-checks.json)和 [完整清单](../evidence/A04/review/coordinate-R3/sha256-manifest.json)冻结本报告、输入、脚本、原始输出及自有释放。仅交付 **OFFLINE_R3=ACCEPTED / A04_OVERALL=BLOCKED**，主调度决定后续接受范围与集成；本轮结束，不继续扩展测试或释放下游。
