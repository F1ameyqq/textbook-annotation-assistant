# A04 coordinate-R2 独立离线复验报告

2026-10-17（Asia/Shanghai）。**R2 离线结论：REWORK。整个 A04：BLOCKED。** 原24字节PNG反例和过期CLI状态已修正，但独立发现另一种像素不完整PNG仍能由公开入口发布。真实R01～R06均未执行、不予通过，不接受整个A04或释放下游。

## 固定输入与边界

| 项目 | 确切值 |
|---|---|
| 被验交付 / 实现 | `76898657e76ac2db071327e90c6ca5031d17571f` / `45150b57f5ae6cc8f4c55ffc6f7e417a0957f32e` |
| base / 执行workflow | `a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39` / `e1b1475597f80d46c5ace5c004f5091d139ac6cc` |
| 本轮验收workflow | `e7ff892776f53636fcddfe136d1659204c4ff738`，续派明确xhigh |
| 验收任务单摘要 | `48c6cb8d41c3598c3fa10f438da0da9d00486c133bc4e97a161ed42518b8d468` |
| A01依赖 | 保持已接受的 `c6bebdf43eb93f7a6ae21e96ec07ed155686777d`，不重新等待 |
| 合同 / geometry | C01 `1.0.0-a-proposal`；A01 `a01-geometry-1` / `a01-geometry-1-r1`，未改公共定义 |
| 执行 / 验收对话 | `01a144cc-dde4-73a1-9e83-be485380ea25` / `01a144cc-e93d-7841-a259-d6aac22c94f4` |

先从该workflow原始Git字节读取AGENTS、调度、[冻结交接](../evidence/A04/review/coordinate-R2/inputs/workflow/docs/tasks/A04-coordinate-R2-review-handoff.md)及其[预检](../evidence/A04/review/coordinate-R2/inputs/workflow/docs/evidence/coordinator/heartbeat-20261017-0604/A04-delivery-preflight.json)。被验工作树只读；实际运行的是从精确交付导出的 `D:/1800/.local/stages/A04-review/coordinate-R2/frozen source with spaces`。输入压缩包及逐文件摘要见 [证据索引](../evidence/A04/review/coordinate-R2/README.md)。没有合入浮动主目录。

本轮禁止项均保持：浏览器、平台、登录、授权profile、网络、模型及书籍动作0；不重试既有GET、不重放题22。仅使用离线Python、合成图像及少量历史离线测试输入；Git仅用于本地对象读取。不修改产品/合同/根依赖/state，不提交、合并、推送，不联系执行者或B。安装和依赖变更0，付费模型调用/花费0。

## 必修 A04-CR2-01（P2）：缺失像素行的PNG仍被发布

固定源码的 `src/annotation/source/usense/parser.py:221–230` 采用 `verify()` 后重开并 `load()`，但当前Pillow对本反例两步均不报错。因此“完整原图”的判据仍不足，不能仅以解码调用成功推定声明范围的像素齐全。

独立生成的PNG只有180字节，SHA256为 `205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd`。IHDR声明 **37×29、8bit RGB、不交错**；IHDR/IDAT/IEND完整，所有CRC有效，zlib流也能正常结束。每行应有 `1 + 37×3 = 112` 字节（含滤波字节），整图应有 `29×112 = 3248` 字节；实际解压仅 **112字节，即1行**。

| 独立观察 | 实际结果 |
|---|---|
| 逐块CRC及zlib检查 | 通过，但明确少28行像素 |
| Pillow 11.3.0 `verify()` / `load()` | 均接受；未启用截断容忍 |
| 另一套本地完整解码器 `cv2.imdecode` | 拒绝，返回空；原始stderr为 `Not enough image data` |
| 公开 `python -m annotation.source.usense offline` | **退出0**，创建SourceBundle / PlatformSnapshot和最终bundle |
| 未改写输出的公共 `load_bundle` | **接受**最终包 |

这是由修复后的A04公开入口直接发布的输出，**没有人为重封摘要或修改合同**。证据：[行数/解码器/公开入口观察](../evidence/A04/review/coordinate-R2/pixel-diagnostics-cases/short-row-observation.json)、[原始stderr](../evidence/A04/review/coordinate-R2/pixel-diagnostics/pixel-diagnostics-stderr.txt)、[最小输入](../evidence/A04/review/coordinate-R2/minimal-repro/input/capture.json)、[最终输出](../evidence/A04/review/coordinate-R2/minimal-repro/output/bundle.json)、[最小结果](../evidence/A04/review/coordinate-R2/minimal-repro/result.json)。另一个自建“解析后替换、再公开发布”例也产生了最终包，与此处是同一像素完整性缺口。

最小复现命令，输出必须使用不存在的新目录：

```powershell
python -B D:\1800\docs\evidence\A04\review\coordinate-R2\scripts\repro_incomplete_rows.py `
  --root 'D:\1800\.local\stages\A04-review\coordinate-R2\frozen source with spaces' `
  --output 'D:\1800\.local\stages\A04-review\coordinate-R2\fresh missing-row reproduction'
```

该复现脚本退出1表示缺陷存在；**产品CLI本身的错误行为是退出0**。要求来源入口和发布前复查都拒绝这种声明尺寸与实际像素行不完整的输入，保留安全定位及正常PNG/JPEG/PGM兼容性，不得发布完整来源包。具体验证方法由执行者实现；本验收未代修或新增根依赖。

## 已通过的离线范围

| 检查 | 本轮结果 |
|---|---|
| 原R1 24字节PNG | 公开CLI退出2，`RESOURCE_INVALID; LOCATION=$.pages[0].asset_path`，不创建输出目录 |
| 有效头部、熵流截断JPEG | 独立结构检查通过、完整解码拒绝；公开CLI安全拒绝，无最终包 |
| 有效P5头部、像素不足PGM | 同上，拒绝 |
| CRC损坏但像素可读取PNG | 结构层拒绝，公开入口拒绝 |
| 完整解压长度、非法滤波字节PNG | CRC/结构通过，两套像素解码均拒绝；公开入口退出2，无输出 |
| 正常PNG、渐进JPEG、ASCII P2、二进制P5 | 四种自建包均经公开CLI发布；搬到含空格目录后，从另一cwd由公共loader及完整解码器消费；37×29、原字节SHA256、MIME及相对路径绑定保持 |
| 发布前复查 | 已确认可检测的坏滤波像素在parse后损坏时，`build_source`返回`RESOURCE_INVALID`且不写历史；CLI复制阶段损坏时也不发布历史/最终包。有效图像换字节则返回`RESOURCE_MISMATCH` |
| 环境容忍与脱敏 | 隔离进程内注入`LOAD_TRUNCATED_IMAGES=True`时来源拒绝，产品未改该标志；测试随后还原False。解码异常的合成敏感标记与本机路径不进入公开错误 |
| 状态语义 | `geometry_dependency_status=ACCEPTED`、依赖提交准确；`geometry_status=NOT_PERFORMED_BY_SOURCE`、`acceptance=NOT_ASSERTED`、`network_used=false`；局部CLI无过期等待字符串 |

正常格式及失败例原始输入、命令、stdout/stderr、便携包均保留。见 [首轮独立15项](../evidence/A04/review/coordinate-R2/independent-cases/results.json)、[定向像素4项](../evidence/A04/review/coordinate-R2/pixel-diagnostics-cases/results.json)、[公开迁移消费者](../evidence/A04/review/coordinate-R2/scripts/consume_package.py)及 [六条任务要求逐项结论](../evidence/A04/review/coordinate-R2/review-verdict.json)。

首轮原始统计为11 PASS / 4 FAIL，定向检查3 PASS / 1 FAIL，均未覆盖或改写。首轮N02原先误以为Pillow应拒绝缺行图，故在运行CLI前失败；随后用精确行数和另一解码器核实，并从公开入口形成上述独立缺陷证据。U01对错误码的过严断言失败，但实际摘要复查已拒绝改图；D03/D04另证实解码拒绝路径。U03是同一缺行图实际发布；L01是明确标记的人为重封测试包，只证明哈希层边界，不冒充修复后的合法输出。人工重封包不参与上述必修缺陷的证明。

## 受影响回归、保全和过程异常

按本轮“仅离线Python”边界，A04覆盖152个方法，最终 **151通过、1跳过**；合同覆盖70个方法，最终 **69通过、1跳过**。Node合成fetch截止时间测试、以及本机缺少symlink权限后需调用`cmd`创建junction的合同测试未运行；两者均是未改动边界，不能记为本轮通过。原R1完整矩阵、坐标renderer及旧失败按原版本保留，没有无条件重跑或启动浏览器。

验收审计脚本初稿未处理Windows `subprocess.Popen` 审计参数中`executable=None`，导致初轮A04出现2条error、合同8条error（含子测试）。日志完整保留；仅修正审计脚本，随后定向补跑受影响的6个Python测试方法通过，另1个junction方法明确跳过；产品源码和失败输入未修。初次快照脚本也因假定namespace父目录存在`__init__.py`停止，后改为比较Git tree中的同等缺席，已导出字节先核对后继续。见 [回归日志](../evidence/A04/review/coordinate-R2/regression/process-results.json)、[定向补跑](../evidence/A04/review/coordinate-R2/guard-correction/process-results.json)、[剩余补跑/排除项](../evidence/A04/review/coordinate-R2/guard-correction-remaining/process-results.json) 和 [原审计脚本](../evidence/A04/review/coordinate-R2/harness-notes/offline-guard-before-windows-fix.py)。

[输入检查](../evidence/A04/review/coordinate-R2/snapshot-check.json)独立核对作者清单158项原Git与磁盘字节一致、旧执行清单81+67=148项不变；本轮产品只改`parser.py`、`cli.py`，公共合同、geometry、source/static、browser、delivery、根配置/依赖及父入口保持原基线。原准备5项和R1复验227项及其报告/失败保留。测试stage额外放置的`sitecustomize.py`是有单独摘要的验收审计bootstrap，未替换任何冻结产品文件。

环境为现有Python 3.9.13、Pillow 11.3.0、Pydantic 2.12.5及本机既有OpenCV/NumPy，仅用于本地字节和像素检查；详见 [环境记录](../evidence/A04/review/coordinate-R2/environment.json)。未安装或变更依赖。D01已由主调度另行接受并本地集成于`c78c8a123437e6c53096e0c48f1dd14aad10c2c3`；本轮未重测安装，不把执行报告的任务范围限制误记成D01仍未接受。

## 真实阻断、释放和交付

真实六项继续 **BLOCKED / NOT_RUN**：R01新会话及登录/实际目标，R02当前14/15/173原图，R03正文14→15→14与答案页状态，R04当前目录/题/框及网络审计，R05真实查看器参考点/坐标，R06当次独立会话获取和释放。需要主调度新的明确有界续派与服务/输入条件变化，届时再核对授权范围和实际占用；本轮不取得或检查profile、不重试此前五次GET。A01依赖不再是阻断；源码修复或消除旧状态文字不替代这些真实证据。S01来源完整性、B共同确认、保存/OCR/恢复、内容质量和真实成本不因本轮离线检查而通过。

[自有进程释放](../evidence/A04/review/coordinate-R2/self-release.json)记录35个本轮已知Python工作/启动进程PID，均已退出；30份审计退出记录没有网络/敏感路径或非Python进程的实际放行。查询只针对自己记录的PID，没有全系统或他人会话扫描。所有自有子进程已等待回收，无浏览器、profile lease或后台服务待释放，不声称授权profile当前空闲。

[最终检查](../evidence/A04/review/coordinate-R2/closure-checks.json)及 [完整SHA256清单](../evidence/A04/review/coordinate-R2/sha256-manifest.json)包含新报告、固定输入、脚本、原始失败/输出、必要日志和释放证明，清单自身除外。报告仅交付 **R2 REWORK / A04 BLOCKED**，不提交、不集成、不释放下游；完成本轮后结束。
