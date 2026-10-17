# A04 coordinate-R1 独立复验报告

2026-10-17（Asia/Shanghai）。**结论：REWORK；真实平台必需项仍 BLOCKED，整个 A04 不予 ACCEPTED，不释放下游。** 本轮可接受的是下表限定的离线坐标、局部边界防护和已复现回归。独立发现损坏原图可经公开离线入口发布为已取得页，必须返修。

## 版本与执行边界

| 项目 | 固定值 |
|---|---|
| 被验冻结交付 | `a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39` |
| 实现提交 | `66aa1a3754f31a831b38ca9894bd1c203498985d` |
| coordinate-R1 base / 执行 workflow | `3e4dba5676c2dc4a71d7826827a76df11017a68b` / `f15f7bc03fac8994ade1642fa7547cbd823c6d43` |
| 本轮验收 workflow | `2ef3bfda20476dff3bdd23912d5bf2d1e3eb5ce1`；正式续派要求 xhigh |
| 接受的 A01 实际集成 / A04 依赖合入 | `c6bebdf43eb93f7a6ae21e96ec07ed155686777d` / `3d4d10a0e12faa1af8d47e9f180d086ce401509c` |
| 原任务 base / workflow | 均为 `39341c98d73c354d639f3beeb55429f55d0e9be5`；只作历史，不能代替本轮输入 |
| 合同 / geometry | C01 `1.0.0-a-proposal`；A01 `a01-geometry-1` / `a01-geometry-1-r1`；B 共同确认不由本验收推定 |
| 执行 / 验收对话 | `01a144cc-dde4-73a1-9e83-be485380ea25` / `01a144cc-e93d-7841-a259-d6aac22c94f4` |

依据 [正式交接](A04-coordinate-R1-review-handoff.md)、[续派范围](A04-coordinate-R1-dispatch.md) 和 [原验收条款](A04-independent-review.md)。被验工作树 `C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800` 全程只读。测试使用从确切 Git blob 导出的隔离目录 `D:/1800/.local/stages/A04-review/coordinate-R1/frozen input with spaces`；[完整输入压缩包](../evidence/A04/review/coordinate-R1/inputs/frozen-inputs.tar.gz)、[逐文件清单](../evidence/A04/review/coordinate-R1/inputs/frozen-tree-manifest.json) 和补充的合同 examples 均来自同一冻结提交，不运行浮动主目录产品代码。

本轮未启动 persistent context、未读取授权凭据/profile、未登录或访问真实平台。仅运行本地替身临时浏览器；合成 helper/lease 的异常注入不涉及实际账号。未修改产品、合同、根依赖、调度 state 或被验工作树，未提交、合并、推送、联系执行者/B 或调用付费模型。付费模型调用和费用均为 0。

## 必须修复：A04-CR1-01（P2）损坏原图被公开入口接受

位置为固定输入的 `src/annotation/source/usense/parser.py:160–208`，特别是 169–171 行：PNG 分支只读取签名、IHDR 标记和宽高，没有确认整张图像可以解码；`build_source` 再检查时仍使用同一头部解析。此处是原 A04 继承实现，新独立复验发现，不称为 coordinate-R1 增量引入。

独立把正常合成包的正文14原图替换为 **24 字节截断 PNG**（没有完整 IHDR、CRC 或像素数据）。Pillow 完整读取拒绝该文件；公开 `annotation.source.usense offline` 却退出 **0**，生成 SourceBundle / PlatformSnapshot，`pages_acquired` 为 **3**，随后公共 `load_bundle` 仍接受。缺陷既可从 `parse_capture` 重现，也已走到真实公开产物消费边界。

证据：[最小观察](../evidence/A04/review/coordinate-R1/minimal-repro/result.json)、[实际输入](../evidence/A04/review/coordinate-R1/minimal-repro/input/capture.json)、[被接受输出](../evidence/A04/review/coordinate-R1/minimal-repro/output/bundle.json)、[原始控制台](../evidence/A04/review/coordinate-R1/minimal-repro-console.log)。这不是平台写入或线上故障注入。

最小复现命令；`--output` 必须使用尚不存在的新目录：

```powershell
python D:\1800\docs\evidence\A04\review\coordinate-R1\scripts\repro_truncated_original.py `
  --root 'D:\1800\.local\stages\A04-review\coordinate-R1\frozen input with spaces' `
  --output 'D:\1800\.local\stages\A04-review\coordinate-R1\fresh F06 reproduction'
```

脚本退出 1 表示缺陷仍在；内部公开 CLI 的错误行为是退出 0。本轮实际保留的输出位于 `minimal-repro/`。修复应在来源公开入口确认完整图像可读取，失败时返回可定位且脱敏的资源错误，并阻止发布完整产物；覆盖截断 PNG 及其他实际支持格式的损坏像素输入。验收者未代修实现。通过本项修复也不解决下述真实平台阻断。

## 可接受的离线范围和复验结果

| 范围 | 本轮观察 | 限制 |
|---|---|---|
| 固定交付及改动范围 | 原 Git 字节核对执行清单 **67项**；旧执行报告/证据 **81项**保持；本轮增量无越界文件 | 字节检查不等于功能接受 |
| 公共依赖 | geometry、contracts、config 树与指定 A01 依赖精确一致；实际测试导入隔离输入 | 旧等待 A01 阻断已解除 |
| 作者测试复现 | A04 **141/141**、geometry **8/8**、合同 **70/70**、登录 **8/8**，合计227项 | 已记录现有环境，清洁安装 D01 未测 |
| 正常公开入口与搬运 | 从另一 cwd 运行公开离线 CLI；完整包搬至含空格目录后公共 loader 通过；独立解码、尺寸、SHA256检查通过 | 合成包，不代表当前平台状态 |
| 自建离线检查 | **49个子检查：47 PASS、2 FAIL**；两条失败同属 A04-CR1-01 | 不把作者成功用例计作独立失败输入 |
| 数值坐标与绑定 | 13个独立手算/错误映射/asset、摘要、尺寸、页与非法状态检查通过；使用接受的 A01 Transform | 仅离线映射 |
| 作者本地 renderer | 冻结脚本重跑；DPR=2，正文/答案各3点通过 | 历史原图、本地 fulfill/abort；不是当前Usense |
| 独立本地 renderer | 自选不同原图裁片，OpenCV 全图 NCC 定位，与作者稀疏匹配器独立；DPR=2.75、两页×两种状态×3点＝**12点通过**，另12种错误映射拒绝 | 使用历史正文14/答案173像素；不验证当前页15或线上手势 |
| 请求防护 | 真临时浏览器仅向127.0.0.1请求；POST/PUT/PATCH/DELETE修改被阻断，服务器接收数0；允许GET接收1，合成登录例外仅第一次到本地服务器 | 路由 facade 只把策略判定URL标记为平台域名；实际fetch始终为localhost；未登录平台 |
| 异常释放 | 合成启动、导航、认证确认、关闭失败均释放自己的测试lease，随后可重新获取；不删他人锁 | 进程计数注入，不当作实际授权profile验收 |

数值 oracle 不使用待测映射生成期望值；本地像素参考点在原图上预先选取，匹配扫描整张canvas和面板截图，不以预测平移缩窄搜索。独立 renderer 最大 canvas/CSS/原图误差分别约 **0.588 / 1.299 / 4.090 px**，按原有 **2.5 / 2.5 / 8 px**阈值检查，未放宽容差。错误映射即使自身正反变换相消，也被实测参考点拒绝。

[回归原始日志和环境](../evidence/A04/review/coordinate-R1/reproduction/results.json)、[独立子检查](../evidence/A04/review/coordinate-R1/independent/results.json)、[手算输入](../evidence/A04/review/coordinate-R1/independent/geometry-oracle-input.json)、[独立本地renderer](../evidence/A04/review/coordinate-R1/independent-renderer/result.json) 均保留。既有Python 3.9.13、Pillow 11.3.0、Playwright 1.58.0、Pydantic 2.12.5；独立像素定位另使用本机既有 OpenCV / NumPy，版本列入最终环境证据，没有安装或修改根依赖。

复现过程中的验收环境错误也保留：首次隔离导出漏掉合同消费者脚本，合同70项中同一测试的两条子断言因文件不存在失败；补导出冻结提交的 `examples/contracts` 后，仅重跑受影响合同检查，70项通过。首次独立renderer脚本引用未安装的可选 psutil，在启动浏览器之前即失败；改为只观察自己子进程PID的Windows查询后完成。两次都属于验收脚本/输入问题，不归因产品，旧日志与脚本版本未删除。见 [合同补充与重跑](../evidence/A04/review/coordinate-R1/reproduction/contracts-after-input-supplement.json) 和 [脚本失败记录](../evidence/A04/review/coordinate-R1/harness-failures/renderer-missing-optional-psutil.log)。

另有状态观察 **A04-CR1-02（非新增阻断）**：通用离线CLI仍硬编码 `geometry_status=WAITING_ACCEPTED_COMMIT` 及同名stdout；[本次公开入口输出](../evidence/A04/review/coordinate-R1/reproduction/public-entry.json)已复现。A01依赖实际已接受，这些旧字符串不能作为当前调度阻断。建议按实际区分“来源未执行坐标检查”和“依赖已接受”；也不能直接把离线包标为真实坐标通过。

## 28项映射与真实阻断

原准备场景逐项对照见 [28项机器矩阵](../evidence/A04/review/coordinate-R1/scenario-matrix.json) 和 [证据索引](../evidence/A04/review/coordinate-R1/README.md)：**21项 PASS、F06为REWORK、6项真实场景BLOCKED**。这里的矩阵D01是原“证据收口”场景，和项目另行管理的D01清洁安装不同。本报告没有对整个source适配器给出通过结论。

作者的 live-01/02/03 均在 `read_current_state` 阶段 `TIMEOUT / fetch`，后两次诊断的 DIRECTORY / SOURCE_INDEX 也超时。已按冻结字节复核五次失败及其释放记录，见 [历史真实证据复核](../evidence/A04/review/coordinate-R1/historical-live-evidence-review.json)。本轮没有重试，不能把作者失败前的登录复用、历史22题68框/121目录/214页、旧原图或本地renderer替代当前观察。

| 真实场景 | 当前结论 | 仍需的独立证据 |
|---|---|---|
| R01 | BLOCKED / 本轮不执行 | 获准的新会话、目标46007447及受保护界面/内容确认 |
| R02 | BLOCKED | 当前原图14/15/173、资源映射、字节摘要、真实尺寸 |
| R03 | BLOCKED | 正文14→15→14及答案173状态、翻页前后/返回证据 |
| R04 | BLOCKED | 当前目录/题/框、观察时间、目标摘要及脱敏只读网络审计 |
| R05 | BLOCKED；离线部分PASS | 实际查看器的参考点、viewport、DPR、canvas/backing/CSS、缩放平移及正反映射 |
| R06 | 未取得真实会话 / BLOCKED | 下一次获准会话的独立获取、正常结束及当次实际释放证据；本轮仅本地释放PASS |

恢复真实验证须先有服务/输入变化或主调度明确有界续派；届时确认具体允许范围、当前书籍/profile调度交接及实际进程/锁/lease，再运行上述真实项。证书忽略仍只可使用当次明确参数。发现冲突不抢锁；遇失败停在可核对结果，不以再次写入或扩大采集范围解除阻断。A01已接受不需重新等待或重验其集成；须保留其确切消费版本。

## 自有释放、保全与交付

[自有释放记录](../evidence/A04/review/coordinate-R1/reviewer-release.json)显示：独立renderer的context/browser/Playwright、本地服务器均关闭；运行时观察的9个自有浏览器/driver PID结束后均不存在。作者renderer复现命令已退出0，MODE记录关闭。授权profile没有取得lease、没有打开；未查日常或授权profile当前状态。作者最后释放时间为 `2026-10-17T05:05:41.884825Z`（北京时间13:05:41），匹配进程0/锁0/lease无仅证明其当时观察，不代表现在或永久空闲。

[最终收口检查](../evidence/A04/review/coordinate-R1/closure-checks.json)核对链接、输入未变、旧准备材料保留、被验工作树干净、公开边界、敏感材料排除和必要忽略日志清单；[SHA256清单](../evidence/A04/review/coordinate-R1/sha256-manifest.json)覆盖本报告、新输入/脚本、失败、原始输出及证据，清单自身除外。未更改 [原准备报告](A04-review-report.md) 或旧失败。主目录协调者并发更新不作为本验收改动，也没有由验收回写state。

正式交付为上述 **REWORK + 真实项BLOCKED**，不是已集成。修复及后续真实运行由主调度安排；本轮完成报告并释放自有资源后结束，不继续轮询或访问平台。
