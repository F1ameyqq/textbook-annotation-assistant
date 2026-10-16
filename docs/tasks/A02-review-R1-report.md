# A02 R1 独立复验报告

日期：2026-10-17（Asia/Shanghai）。结论：**ACCEPTED**，限 A02 R1 当前内存会话的跨书暂停隔离修复及原有离线模拟边界。

被验最终提交 **`38aca9dcc8d027409b95193e9cc142c2336b76d3`**；实现提交 `13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2`；R1 基线 `5c9285720c8628c5198bedeadfc9f6bc7826a914`；原 base/workflow 均为 `39341c98d73c354d639f3beeb55429f55d0e9be5`。本报告不构成集成决定或 A03 依赖释放，首轮 REWORK 报告与失败证据保持原字节。

## 修复结论与独立效果证据

生产差异仅在 `src/annotation/delivery/mock/__init__.py:49–50` 增加 ExecutionReceipt 自身书号筛选。pending 分支、完整历史的存储/读取、同书暂停和旧计划重放门均未改变；没有删除外书产物、清除 UNKNOWN、拒绝合法多书包或把历史裁成单书包的替代实现。[完整生产差异](../evidence/A02/review-R1/production.diff.txt)。

独立重建首轮合法多书输入并交换两书角色，均观察到：当前书无动作诊断为 NOT_EXECUTED，暂停保持 false，外书 UNKNOWN 的完整产物链保留；随后 READY 三动作真实执行 APPLIED，独立目标为 **3 题 / 9 框**，题序为 1/2/1，三个 intent、实际模拟平台 ID、投影与读回一致，当前书仍不暂停。对外书产物按 artifact_id+revision 精确比较，没有把同 ID 的不同不可变修订合并。

证据：[正向观察](../evidence/A02/review-R1/independent/mixed-final/forward/observations.json)、[交换角色观察](../evidence/A02/review-R1/independent/mixed-final/swapped/observations.json)。对应目录含原始合法输入、计算 TARGET、计划、诊断回执、实际执行回执及前后目标/动作日志/完整历史。

独立补测两书各自只有历史 UNKNOWN、均无 pending/intent：新 MockSession 只成功执行两个 BLOCKED 零动作诊断，把完整合法混合包分别存入各书历史。两书随后各自提交不含任何回执的合法 READY 计划，公共资格门通过，但正式 mock 入口均返回 **BOOK_WRITE_PAUSED**。两书状态和完整历史保持等值，最终零日志、零 intent；**29 项断言通过**，未读改私有 pending 集合。该场景证明修复没有只依赖 pending 而丢掉同书历史保护。[实际观察与检查](../evidence/A02/review-R1/independent/history-pair-final/actual.json)。

另独立测试一书实际产生 UNKNOWN / 4 框后，另一书分别得到 APPLIED、NOT_APPLIED、NOT_EXECUTED；原未决书的状态、按书筛选的日志及完整历史均不变，仍暂停，另一书不被误暂停，旧计划仍拒绝重放。[五组定向场景](../evidence/A02/review-R1/independent/mixed-final/results.json)。

## 确切身份、完整性及运行环境

从指定最终提交 raw Git blob 导出 **141 个必要源码/测试/样例文件**到 `docs/evidence/A02/review-R1/source-38aca9dc/`，逐文件验证 blob 与 SHA256，测试后再次核验全部字节。实际 contracts、planner、mock、targetcheck 导入均位于该副本。副本无 `.git`，`checkout_commit=null`；身份由明确的 `declared_commit=38aca9dc...` 和外部 Git blob 比对确定，没有采用父仓库 HEAD。

已独立核对：**970 个改动路径**均在 R1 允许范围；基线、实现及已接受 C01 来源均为最终交付祖先；**962 项最终 freeze 清单**匹配源工作树磁盘及确切 Git blob。执行报告 SHA256 为 `3b903c24e09a186b778c04f30354dea6c41f3925f4b8cafcf3be4b04b0516167`，最终 freeze 清单 SHA256 为 `9df33152c66e3e0ea2cb72ff3bc4162063961412e6fd007d06a6ff343fa61ea0`。

历史初始 960 项清单中的报告指针仍指向收尾前版本；本轮明确不以该历史指针验证最终报告。最终 freeze 清单同时覆盖当前报告与原字节历史清单，不能把所有阶段清单描述为都指向最终报告。[交付清单核对](../evidence/A02/review-R1/delivery-manifest-check.json)。

**382 个旧交付报告/证据/样例/脚本**与 R1 基线 Git blob 不变；主目录原准备及首轮正式报告/证据的 **2,039 个唯一文件**在运行前后 SHA256 相同。源工作树最终 HEAD 仍为被验提交，状态干净。[导出与范围](../evidence/A02/review-R1/frozen-export.json)、[运行后保全检查](../evidence/A02/review-R1/post-run-integrity.json)。

实测环境为 Windows / PowerShell、Python 3.9.13、Pydantic 2.12.5；解释器 `C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`。测试临时目录及全部新输出均在本轮独占 `review-R1/` 内。[实际源码及环境绑定](../evidence/A02/review-R1/reproduction/source-binding.json)。API `1.0.0-a-proposal`、交换 `c01-exchange-1`、原 `c01-fixtures-1` / `a02-fixtures-1` 均未变。

## 实际命令、结果与逐项复验

以下 wrapper 从 `D:/1800` 发起，完整子进程 argv、cwd、退出码、stdout/stderr 和固定源码路径均落盘。已有输出不能覆盖；再次复现须使用新输出路径。

| 实际命令 | 退出码 | 观察结果 |
|---|---:|---|
| `python -B docs/evidence/A02/review-R1/prepare.py` | 0 | raw 导出、范围、祖先、最终清单及旧材料保全 |
| `python -B docs/evidence/A02/review-R1/run_author.py` | 0 | 复现 **52 项 A02、70 项 C01、16 个 R1 场景、10 组演示** |
| `python -B docs/evidence/A02/review-R1/run_risk.py` | 0 | 原独立矩阵的 61+9 个风险用例全部通过 |
| `python -B docs/evidence/A02/review-R1/run_final_risk.py` | 0 | 明确 ABSENT 后重查/新计划成功，另一书单独包可模拟 |
| `python -B docs/evidence/A02/review-R1/run_mixed.py --output D:/1800/docs/evidence/A02/review-R1/independent/mixed-final` | 0 | 两方向完整多书包及三类另一书结果，共 5 组通过 |
| `python -B docs/evidence/A02/review-R1/probe_history_pair.py --output D:/1800/docs/evidence/A02/review-R1/independent/history-pair-final` | 0 | 双历史 UNKNOWN、无 pending，29 项检查通过 |
| `python -B docs/evidence/A02/review-R1/check_integrity.py` | 0 | 新源码及旧材料复核；格式例外分别记录 |
| `python -B docs/evidence/A02/review-R1/consolidate.py` | 0 | 67 行矩阵、72 个原独立用例及定向场景汇总 |

[命令与退出码收据](../evidence/A02/review-R1/command-receipts.json)包含首次不成功的验收脚本尝试。两项为验收者构造错误：跨书保全比较初次只按 artifact_id 建索引，混淆两个修订；历史输入克隆初次误给 check_id 枚举加前缀，尚未进入 mock。只修正本轮验收脚本，分别改用新输出重跑，失败日志/初始脚本和部分输入保留。收尾资源收集器首次把固定 expected.json 摘要误当作交换包，修正分类条件并保留初始脚本后重新核验；以上均不计为产品缺陷，也未修作者实现。

| R1 交接要求 | 独立复验结果 |
|---|---|
| 1 作者套件/矩阵/演示、确切导入身份 | 通过：52/70、16、10；所有实际源码绑定最终冻结提交，导出 checkout 身份为 null |
| 2 原跨书诊断 → READY 实际执行，交换角色 | 通过：诊断不误暂停、3 题 9 框、完整外书历史保留；未靠返回值或作者预期文件判定 |
| 3 同书保护、输入省略历史、无 pending、两书未决 | 通过：原换 run/action/question/scope 用例保持拒绝；新双历史探针分别拒绝省略历史 READY；作者双实际 UNKNOWN 场景也复现 |
| 4 其他书结果不解锁、重放及 ABSENT 语义 | 通过：APPLIED/NOT_APPLIED/NOT_EXECUTED 不清另一书 UNKNOWN；旧计划拒绝；ABSENT 后新检查/计划可执行；未派发项保留独立 ABSENT 读回 |
| 5 原十条标准风险复核及最小生产差异 | 通过：72 个原独立用例全部通过；仅回执书号筛选变更，无删包/清历史/限制单书捷径 |
| 6 字节保全、资源闭包及格式 | 通过，保留格式例外：完整交付 `git diff --check` 对原失败 unittest stderr 首行尾空格退出 2；源码/测试/演示为 0，排除此原始日志的其余差异为 0 |
| 7 原边界不扩大 | 保留 N1/N2、S01、A03 恢复、内容质量和 B 确认限制 |

[逐场景索引](../evidence/A02/review-R1/matrix-results.json)对应原 67 行矩阵及本轮定向检查。原未派发项的 ABSENT 不是由“没有派发”直接推出：独立风险检查再次核对相关 before/readback、读回 OK、目标未绑定且无预期框，UNKNOWN 本身仍保留实际效果和暂停。

## 接受范围与未验证层

本次接受的是 SYNTHETIC 输入下的 SIMULATED 内存执行及书级暂停隔离；诊断回执为 NOT_EXECUTED。框匹配后的批次仍 **CONTENT_PENDING / PENDING / NOT_SUBMITTED**，未变为 COMPLETED。未执行浏览器、平台、凭据、网络、OCR或外部模型调用，外部模型费用为 0，真实运行成本未测。

N1 排除区域关联与 N2 证据注册标签准入保持原限制，未放宽覆盖检查或宣称能够消费真实来源。S01 公共真实来源资格、A01 当前任务验收结果、B 合同确认均不由本次合成模拟通过替代。

A03 持久 intent、跨进程书锁、崩溃/重启恢复、正式 ReconciliationResult 与 UNKNOWN 解除仍未实现或未验证。UPDATE、组合/父子、七选五、合并 W 仍为原显式拒绝路径；最终内容质量、算法准确率、真实平台和人工最终提交均未验收。

本轮只写新报告及 `docs/evidence/A02/review-R1/`，未修改实现、公共合同/政策/样例、根依赖、主调度状态或任何旧验收材料。未管理 B、向其他 Codex 对话发消息、推送或集成。[统一 SHA256 清单](../evidence/A02/review-R1/sha256-manifest.json)包含本报告及本轮全部文件；清单自身不自引用。

交回主调度：R1 独立复验 **ACCEPTED**；由主调度复现并决定集成及 A03 依赖释放，验收者不自行执行这两步。
