# A01 R2：来源记录内部一致性补全

日期：2026-10-16。状态：READY。此次仅补足 R1 复验已证明的三类来源一致性缺口，交付仍为 REVIEW；不自动接受或集成。

## 基线与证据

继续原工作树 `C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`、分支 `codex/a01-source-geometry`。R2 基线为 **`03c1af41a134945c406a52a48e3d4f6f0da33eb2`**，其 R1 实现为 `0ee7e836e3bc1849f91840b4271d233bbd8e72dd`；原 base/workflow `39341c98d73c354d639f3beeb55429f55d0e9be5`。不得合并浮动主分支。

从主目录只读 [R1 独立复验](A01-review-R1-report.md)、[原 R1 修复范围](A01-rework-R1.md)、[原独立标准](A01-independent-review.md)、[四个最小输入及结果](../evidence/A01/review-R1/primary-source-confirmation/results.json)、[来源邻近检查](../evidence/A01/review-R1/source/REPORT.md) 与 [调度复现](../evidence/A01/coordinator/R2/coordinator-check.json)。本轮主调度核对 11 个固定源码 blob、53 个反例输入文件并读回四包，均通过公共资源验证而被 A01 接受，确认失败。该重放未运行整套测试。

这些问题属于既有 R04“包内一致性”及原任务的范围/来源/映射检查；不要求无签名材料证明外部真实性。原 16 例及几何独立 630 项已在 R1 复验通过，不把这些局部结果扩成整个 A01 通过，也不重做几何实现。

## 必修三项

| 项目 | 固定输入与要求 |
|---|---|
| R2-01 范围分区矛盾 | 保持旧书 source7 已取得资产/映射/selected，设置 `selected_missing_source_indices=[7]` 仍被接受；另 N14 把同一个已取得 source7 放入 `outside_selected_scope_unacquired_indices`，使已取得与外部未取得相交、总数超元数据。按现有格式核对 selected / acquired / selected_missing / outside-unacquired 的集合及计数关系，必须定位拒绝，不删真实缺失记录或假定取得=完整覆盖。 |
| R2-02 历史响应 URL 绑定矛盾 | 新书 `history/00-independent-source-page14.json` 保留 file_id=46007447、page_index=13，却把 image URL 改为旧书 46006966 或同书 `_page_172.jpg`；历史输入 before/after 与资源摘要同步后仍被接受。离线解析已知来源 URL 格式，核对 URL 的书籍/源索引与响应字段和保留映射一致；复用既有导入语义，不写固定页号规则，不请求网络。 |
| R2-03 观察索引摘要冲突 | 新书 `provenance.observation.observation_index_source.sha256` 全零，而同 archive_path 的 input-integrity before/after 仍为正确摘要；新资源重封装后仍接受。核对同一路径来源身份和摘要，不仅检查 archive boundary；矛盾须定位拒绝。 |

每类至少覆盖固定失败、邻近非法/合法输入及两书正常旧包/R1包。范围分区还核对重复、边界及空集合的既定含义；不得以禁止所有缺页或拒绝所有历史来源规避。URL 检查保留合法现有 URL 格式和主机文本，不把任意字符串无根据解释为可信实时观测。摘要检查不以重算当前改写内容冒充原保留摘要。

来源 N15 的 LIVE_OBSERVATION precision 标签为低风险元数据观察，记录限制即可，本轮不扩成观测认证或网络信任系统。S01 公共自动资格与 D01 Pillow 根依赖继续归调度，均未解决；B 未确认。

## 独占改动范围

允许 `src/annotation/source/static/`、必要 `tests/test_a01*.py`、`docs/a01-source-geometry.md`。新输入、脚本和产物放 `tests/fixtures/a01/R2/`、`examples/a01/R2/`、`docs/evidence/A01/execution/R2/`；报告仅 `docs/tasks/A01-rework-R2-report.md`。

保留旧固定包、原输入、首轮及 R1 执行/验收/失败证据原字节。不得改 geometry、contracts、父入口、根依赖/配置、其他任务或主目录调度状态。若现有格式确实不能表达必需关系，报告具体矛盾及最小提案，交调度处理，不能自行放宽标准或更改公共合同。

全程离线：不打开浏览器/profile，不读取凭据，不访问平台/网络/OCR/模型，不推送、不集成。不重放 A05。

## 交付与停止边界

1. 新目录保留修复前失败与修复后结果；原 R1 复验脚本有固定输出位置，只能复制后配置新路径，不能覆盖冻结材料。
2. 回归原 16 例及本轮明确反例；运行 A01/C01 相关套件、旧/R1/新两书消费者与含空格目录搬运，确认历史输入保全。geometry 必须保持字节不变，已有几何回归仍通过。
3. 证据绑定确切实现提交和实际导入源码摘要。给出真实命令、cwd、退出码、通过/跳过数、范围和限制；报告与新证据纳入统一摘要清单。
4. 最终交付确切实现/冻结提交、干净工作树、报告 SHA256、零平台/模型与无待释放会话声明；只交 REVIEW。
5. 本轮是有界 R2。复验仍失败时先给残余最小反例和原因归类，由调度决定停止、拆分或下一有限任务；不持续循环修补、不降低标准、不自行释放 A04。
