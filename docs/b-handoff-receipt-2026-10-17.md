# A 侧接收记录：B 侧 46007447 离线 HOLD 输出包

日期：2026-10-17，Asia/Shanghai。检查方：A 侧调度。范围：交付包完整性、可读性及最小联调接口前检；不评价 B 内部研发是否完成，不代替内容质量验收。

**结论：已取得完整的当前 E/G07/Check07 文件和相关运行材料，包级字节核验与图像解码通过，可以据此准备局部离线读取、呈现和 HOLD 分流。A 公共合同直接兼容、完整语义引用闭包及端到端联调尚未确认。**

## 固定版本

| 对象 | 本次核对值 |
|---|---|
| B 发布分支 | `b-side/readonly-book-46007447` |
| B 包交付提交 | `0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f` |
| 包说明中的 B 代码基线 | `c3cc2df7a0be24c125c83681c0499c0d328d78f6`；校验器随本次包提交 |
| 仓库内 ZIP | `handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip` |
| ZIP SHA256 | `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` |
| ZIP 大小 | 11,681,712 bytes；展开成员总计 42,344,912 bytes |
| run_id | `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2` |
| 包格式 | `b-handoff-package-trial/0.1` |
| A 本次检查起点 | `0360ec9902d63e0d36d7afcd93ae17b2f3252ab9` |
| B 可取得的 A 阶段版本 | `a15301ef3532aca25dcd527aae1c680c1e220e9f` |

包的 Git 原始字节导出到本机 `D:/1800/.local/stages/coordinator/b-handoff-0e5434f/`。未合并 B 分支，没有平台动作、模型调用或对 B 发送消息；本接收记录只在本地归档。

## 已核对的事实

- ZIP 共 **104 个成员**，其中 **103 个清单文件＋manifest 自身**。重复路径、非法相对路径、重复清单项、字节数及 SHA 全部检查通过。包内外验证脚本字节一致。
- 原 B 校验器 `--self-test` 在 A 本机退出 0；A 另用独立脚本核对主报告、14 个阶段 wrapper/result、最终 E/G/Check 精确引用和规范化 payload 摘要。
- **44 个历史输入文件摘要**均有包内字节对应；内层 observed ZIP 中 **95 个实际消费成员**的长度和 SHA 相符。内层 ZIP 实际有 118 个成员，95 是本次运行消费的子集，不混写为整个内层成员总数。
- 外层 **38 张图片**完成像素解码；5 张原图的声明尺寸和 SHA 相符，相邻答案原图也在包内。`viewer-173` 与 `resource-173` 摘要不同，保持两个独立资产。裁片变换和所有区域的业务语义尚未逐项验收。
- 当前图谱确有 **34 个题候选、66 个答案候选**；当前 Check 含 **127 项问题**。主报告、图谱、检查报告均为 **HOLD**，`business_acceptance=false`、`transcription_verified=false`。流水线 READY 表示 14 阶段完成，不赋予平台执行资格。
- 本次扫描校验了 158 个不同的 payload 产物身份。此数量包含历史嵌入对象，不是 158 项功能测试或算法正确性证明。

检查证据：[包前检](evidence/coordinator/b-handoff-0e5434f/package-audit.json)、[引用分类补充](evidence/coordinator/b-handoff-0e5434f/reference-resolution.json)、[B 校验器退出记录](evidence/coordinator/b-handoff-0e5434f/b-verifier.exit.json)。

## 一条需要 B 说明的历史引用

外层及内层 JSON 中未定位到以下引用对应的完整产物 envelope：

```json
{
  "artifact_id": "b-evidence-18e2d1ee2a22288f585513f0",
  "revision": 1,
  "content_hash": "a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da"
}
```

例如它出现在 `inputs/evidence.json#/input_refs/0` 和最终 `artifacts/evidence.json#/payload/base_evidence_archive/input_refs/0`。请 B 说明：

1. 若它是接收校验或复现必须解析的上游对象，请给确切包内路径，或补原对象及摘要。
2. 若它只是可选历史来源标识，请明确其可选地位、它证明什么，以及当前 HOLD 读取为何不依赖解析它。A 不会把它伪造为已闭合的公共 ArtifactRef。

这是 A 的接收边界问题，不据此判定 B 模块失败。包内 `formula/inline-formula.sqlite3` 未查询；本结论限定为可搬运 JSON/明确资源索引，不能推断任意数据库内部没有该对象。

初始前检还列出了六类未匹配为 artifact envelope 的引用，后续已分类定位：五类是实际资源或裁片字节，一类是嵌入的 acquisition receipt。它们不是六个缺失文件。B 的 `input_refs` 同时使用产物引用、资产摘要、裁片摘要和嵌入记录摘要，接收器需要显式区分。

## 最小接收映射：供双方确认

建议首轮只读 B 原生格式，保留原始身份和 HOLD；暂不把它改写成 A 的可执行 C01 包。下列为 A 的接收建议，尚不表示 B 已确认共同合同。

| 项目 | 从本包确认的事实 | A 首轮建议 |
|---|---|---|
| 格式与入口 | Evidence `b-evidence-trial/0.3`；Graph/Check `b-graph-trial/0.7`、`b-check-trial/0.7`；阶段真实结果在 `payload.result` | 明确支持这些固定版本；未知版拒绝；保留 wrapper 与 result 的不同身份 |
| 摘要与引用 | 文件 SHA 和 payload 的规范化 JSON content_hash 分别存在；部分引用缺 kind/revision | 两层分别验证；按引用形状分类解析，不补造字段，不改版本号冒充兼容 |
| run 与 scope | 包/report scope 为五张已观察页；最终图谱 scope 另含相邻答案前缀；最终 graph/check 无独立顶层 run_id | 通过固定 pipeline 输出关系绑定交付运行；保留各产物真实 scope，不统一覆盖为包顶层值 |
| 内容与区域 | 已交当前内容、图谱、问题及来源图；候选和内容仍未核准 | 对活动内容、呈现区域、来源区域分别读取；保留问题与歧义，不按 OCR 片段数生成平台框 |
| 业务门禁 | READY 与 HOLD 并存且含义不同 | 允许查看/导出诊断；保持 HOLD，不产生写入计划或 PASS |
| 负例 | 随包自测检查陈旧引用、未知资产、坏资源三个辅助函数 | A 接收器落地后，以完整输入走总入口验证拒绝；现有自测不算 A 接收器已通过三类包测试 |

本次包没有单独的 `cases/expected` 三类完整消费样例，也没有定稿需求 DOCX 或接口逐项确认答复。当前真实包足够作为正常可解析但仍 HOLD 的基准；负例可以在新副本中由 A 确定性构造并记录，原件保持不变。需求原文与业务政策对齐仍沿用[既有交接清单](b-minimal-integration-handoff-2026-10-17.md)；不要求重新决定已经确认过的规则。

## 后续步骤及完成口径

1. 记录双方对上述原生只读映射及历史引用处理的确认，或具体差异。
2. A 在隔离范围实现接收入口，输出来源/活动内容/呈现区域/问题及 HOLD 回执；不改 B 内部流水线。
3. 用本包及有标记的坏资源、陈旧检查、未知版本变体做总入口检查；另用 A 已有合成正常/UNKNOWN 对照验证模拟分流。
4. A 独立验收接收器并给确切双方版本、包摘要和实际回执，才记录最小离线联调通过。

以上局部读取与 HOLD 分流可以独立于 A03 跨进程恢复推进。A03 功能、I01 完整恢复链、整章覆盖、内容准确率和真实平台保存仍分别保留原有验收门槛。本记录没有释放它们，也未重放 A05 题22或进行书级送审。
