# A01 R1 有界修复任务

日期：2026-10-16。状态：READY。执行者仅交付 REVIEW，由原独立验收对话复验。

## 基线与证据

继续原工作目录 `C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`、分支 `codex/a01-source-geometry`，基于首次冻结交付 `a8d5e96d128e10d341de935d4856682e50df79d9`。原 base/workflow 为 `39341c98d73c354d639f3beeb55429f55d0e9be5`。不合并浮动主分支，不改他人文件。

必读主工作目录的[正式验收报告](A01-review-final-report.md)、[运行摘要](../evidence/A01/review/formal/review-summary.json)、[几何最小反例](../evidence/A01/review/formal/geometry-independent/minimal-counterexamples.json)、[来源结果](../evidence/A01/review/formal/source-independent/results.json)与[调度复现](../evidence/A01/coordinator/R1/coordinator-check.json)。这些文件在 `D:/1800`，原工作树未必包含；通过绝对路径只读。调度已在确切源码上复现7个几何失败及2个最小来源失败。正式报告SHA256为 `157dddf56287a1a3b3d1fd2714d63e8a068fb34b052fe949eb06b75c9901a8a3`。

## 本轮必须修复 R01–R04

| 缺口 | 固定反例与接受条件 |
|---|---|
| R01 P1 合法边界误拒绝 | 原图5×1、crop=[2,0,5,1]、scale=[7/3,1]，点(5,0)应为(7,0)，整裁片框应为[0,0,7,1]；原图3×7、crop=[0,1,3,7]、scale=[1/3,1]、顺时针90°，处理点(6,0)应逆向为(0,1)，处理整框[0,0,6,1]应为[0,1,3,7]。修复4个点/框案例并覆盖邻近边界组合。这是已声明的普通支持域，不能改称不支持。 |
| R02 P2 补边域漏拒绝 | 原图4×1、crop=[1,0,4,1]、scale=[2,1]、padding=[1,0,0,0]。处理x=nextafter(1.0,0.0)严格位于补边；点(x,0)及框[x,0,3,1]必须拒绝，同时精确边界x=1应接受。须在舍入丢失域信息前校验输入域。 |
| R03 P2 整数静默改变 | 原图1×1、padding左为2**53+1。精确保留或明确拒绝不能表示的输入；不得静默改成2**53。若明确限界，文档与输入检查一致，并验证边界内外；不能以此排除R01/R02。 |
| R04 P2 来源/历史内部矛盾 | 对重新计算资源摘要并重新seal的有效新包，仍需检查内部一致性。S12–S20：origins被清空、origin清单摘要与original_manifests冲突、无依据printed_page、删除已知missing_sources、unchanged=false且before/after不同、历史book/原件字节矛盾、无证据升REVIEWED、scope状态与UNKNOWN矛盾、参考ID与公共scope_manifest不一致。逐例给出定位拒绝，正常两书与整包搬运仍可消费。 |

不能用统一扩大epsilon、静默clamp、去除校验、删除失败样例或缩小正常支持域规避。R04要求包内一致性，不要求无签名材料独立证明外部真实性；固定导入器未生成上述坏包，报告须准确描述加载边界。若某例需要合同变更，先给明确结构/语义提案，由调度处理，不擅自改公共合同或把该项记通过。

## 改动范围与禁止事项

允许修改原授权实现 `src/annotation/source/static/`、`src/annotation/geometry/`、`tests/test_a01*.py`、`tests/fixtures/a01/`、`examples/a01/`（保留既有固定样例字节，新样例使用R1子目录或新名）、`docs/a01-source-geometry.md`。新增本轮报告 `docs/tasks/A01-rework-R1-report.md` 和证据 `docs/evidence/A01/execution/R1/`。原执行报告、旧执行证据、正式验收及调度证据全部保留；不要复制或改写主工作目录调度文件。

不修改contracts、父入口、根依赖/配置、delivery、runtime、B模块或其他任务。S01公共完整性门禁和D01 Pillow根依赖由调度负责，继续明确列为未解决的集成限制；本轮不扩权解决。源版本若变更需如实记录A内部提案，不能宣称B确认。

严格离线：浏览器、profile、平台、凭据、网络、OCR、付费模型均不使用；不推送、不合并、不清理他人工作目录。

## 交付与复验

1. 针对全部R01–R04反例补有意义的回归，保留修复前失败与修复后结果；邻近合法输入、非法输入、两书串用、搬运、历史原件保全需不退化。
2. 重跑A01和C01相关套件、两书消费者；给出实际命令、cwd、Python导入位置、退出码、通过/跳过数。独立原脚本可能写证据目录，只能复制或用新输出目录重放，不覆盖冻结验收材料。
3. 报告逐项列修复内容、确切实现提交、最终交付提交、未覆盖项、S01/D01限制。提交报告/证据后冻结工作树，交付 `git status` 与报告SHA256；最终回复状态仅REVIEW。
4. 没有打开浏览器也须说明没有待释放会话。原独立验收对话将基于新确切版本复验，调度确认后才可能ACCEPTED/INTEGRATED及释放A04几何依赖。此次为有界R1；若仍有阻断缺口，继续按具体证据决定后续，不无限自动重试。
