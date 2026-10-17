# A03 P2-R3 EvidenceRecord 消费者闭包修复：REVIEW

2026-10-17（Asia/Shanghai），按本次明确 `xhigh` 续派执行；未派发子智能体。仅修复 `R2-SCOPE-EVIDENCE-ID-01`，未自行记 ACCEPTED。确切交付提交及清单摘要在最终交付回执给出。

| 固定项 | 值 |
| --- | --- |
| base | `526d264284f36f856c306db88c1d7e71c04152e1` |
| workflow | `c3b5f38c7e9a3a4a51ae8cbe16a3821ff2f36970` |
| 任务单 raw SHA256 | `15d75600d449b783eb546feaab95aeef187fdea401be73c3f54f0f12dce5d911` |
| 工作树/分支 | `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` / `codex/a03-runtime-recovery` |
| 写入范围 | 本报告、`examples/a03/P2-R3-evidence-closure/`、`docs/evidence/A03/execution/P2-R3-evidence-closure/`，均为新增 |

读取固定工作流的任务单、调度决定、独立报告、AGENTS/coordination及正式引用权威。未合浮动主树。[输入索引](../evidence/A03/execution/P2-R3-evidence-closure/input-index.json)保留11份必要工作流原字节，包括原反例及两个资源；[R2输入pins](../evidence/A03/execution/P2-R3-evidence-closure/r2-input-pins.json)核对53份实际复用输入的raw Git/SHA1/SHA256，不复制旧候选或历史全集。

## 实际入口和单一修复

[closure.Package.validate](../../examples/a03/P2-R3-evidence-closure/closure.py) 是修正后的唯一完整包入口。它继承固定R2静态Package，加载前核对R2 checker、schema_check、oracle_verifier原字节；不import产品。模块名不是 `__main__`，不会在加载时执行R2矩阵。随后把R2模块内的Package引用统一指向该覆盖类，因此R2 helper、mutate_case和一次main回归的所有完整包检查都经过修正入口。输出一律重定向R3目录，R2原件只读。

| 实际加载源码 | SHA256 |
| --- | --- |
| R3 `closure.py` | `ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5` |
| 固定R2 `check.py` | `7bf3ea27424f7afaf3d3b264d2ab3d0bfa0fdc8bba1c178e6f488bef09e6257b` |
| 固定R2 `schema_check.py` | `9630d7e2e0d3700080f7a97a9c883877acf27929be82a41ed5a8f041240ccf7c` |
| 固定R2 `oracle_verifier.py` | `6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d` |

驱动 `controls.py` SHA=`20f64af79766da00e5026737d1bd18367584fe85d4703a13af1b498189e9bc9b`；最短回放 `replay.py` SHA=`f208986004498e67f41005510b28f6a79f208863a6061bb4b9b3569347cd8902`。实际加载来源也记录在[结果](../evidence/A03/execution/P2-R3-evidence-closure/controls/controls-01/results.json)和启动前源码快照。

修复行为：

1. 每包先建立唯一 EvidenceRecord.evidence_id 索引；重复ID直接 `EVIDENCE_ID_DUPLICATE`，实际正式引用缺失报 `EVIDENCE_ID_MISSING`，不静默跳过。
2. 正式字段来自精确固定Schema：Source/PageMapping、Region/CoverageClue、AnswerRelation、Snapshot/Capability、CheckResult/Issue、ActionResult、旧Batch提交证据等。只把已定义 `evidence_refs`、`before_evidence_refs`、`after_evidence_refs`、`submission_evidence_refs` 中的Identifier数组视为ID。Resource型attempt/reconciliation evidence仍按Resource处理，不误作ID。17处实际Schema指针见[字段表](../evidence/A03/execution/P2-R3-evidence-closure/controls/controls-01/formal-field-registry.json)。
3. 字段按Artifact payload、合法frame event、已定义action-fact/完整Artifact JSON的类型与Schema路径识别。完整Artifact值嵌在Resource内时仍继承实际外层消费者，不凭其自带scope产生新消费者边界。未知普通JSON中同名字符串不成为隐式证据ID；合法JSON evidence继续支持递归普通四元组。
4. 解析ID后，在**当前实际消费者**的found集合中展开EvidenceRecord.resource和全部嵌套JSON，检查该消费者自己的input_refs、book/scope。没有增加EvidenceRecord的book/scope字段，没有把别人的声明当作当前声明，没有全局“已检查”缓存。重复消费同一资源仍逐消费者扫描；仅活动递归保护交由统一DAG拒环。
5. 增加实际消费位置→`E:证据ID`→Resource→Artifact边，接入原统一混合DAG。保留R2明确typed prefix.frames子消费者切换，外层停止点不改；EvidenceRecord本身不形成scope豁免。实际所有普通引用仍受当前Artifact/frame声明及scope约束。

R2 profile、API、六Schema、数据、oracle及其采用状态均不变。这是有限静态验证器修复，不是新的native profile接纳资格或公共合同采用。

## 原反例原字节拒绝及新receipt确认

原 `bundle.json` SHA256仍为 `b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653`。inner/outer raw SHA分别为 `ebd3f42cc53726b05919f27e6ee7b3866cbff7c36454473fe8dfda85e10b33af`、`e14cf14a7a585ad528f7f01807d26a205cfa227c94a23dd51ff537f079dc32f6`。没有更改版本、删除证据、重封原包或损坏摘要。

修正完整入口实际报 `UNDECLARED_REFERENCE at origin-a-SourceBundle`。原输入有多个正式消费者，入口在统一声明检查之前已经扫描全部消费者；诊断列出**13个**有闭包问题的消费者及缺声明/异scope的exact ref。最先报旧Source是原包顺序的结果，未掩盖新receipt。

新1.3 receipt的实际路径：

```text
r2-static-complete-receipt/results/0/before_evidence_refs
  -> EvidenceRecord(proof).resource
  -> review-static/outer.json -> review-static/inner.json
  -> review-isolated-source-b (original-b)
```

该receipt是original-a，未声明该普通四元组。扫描记录确认此直接before路径已解析到原目标；同一receipt的after字段及其fact/result的before/after正式字段也被实际消费。[原例完整诊断](../evidence/A03/execution/P2-R3-evidence-closure/controls/controls-01/original-counterexample.json)保留全部消费者位置及receipt trace。原16个Artifact content_hash均重新核对相等，资源raw SHA、版本及四元组正确；拒绝发生在声明层。若补声明，异scope仍适用，不能借EvidenceRecord绕过。

## 最小控制和受影响回归

完整控制包与额外资源保存在 [cases/controls-01](../../examples/a03/P2-R3-evidence-closure/cases/controls-01/legal-json-evidence-declared-same-scope/case.json)；每份case.json给出完整bundle、资源logical/file/raw SHA、固定R2 data_root/base。固定图片和其他未变资源通过53项R2输入pins复用，不复制大候选。所有判断经修正完整Package入口。

| 控制 | 实际静态结果 |
| --- | --- |
| 原始最小反例 | UNDECLARED_REFERENCE；新1.3 receipt路径已确认 |
| 合法普通JSON证据，两层资源、同书scope、声明完整 | STATIC_ACCEPTED |
| 普通JSON证据消费者漏声明 | UNDECLARED_REFERENCE |
| 同一资源给合法/另一scope消费者分别消费 | ORDINARY_SCOPE；两消费者均有实际trace，不被全局缓存跳过 |
| 正式证据ID缺失 / 重复 | EVIDENCE_ID_MISSING / EVIDENCE_ID_DUPLICATE |
| 普通正式证据链接入混合环 | MIXED_CYCLE |
| 普通JSON中的同名字符串，非合同类型字段 | STATIC_ACCEPTED；不误扫为证据ID |
| 合法typed frame经正式证据消费scope-b引用 | STATIC_ACCEPTED；使用frame自己的scope/声明，外层scope-a不继承 |
| 上述frame漏自己的声明 | UNDECLARED_REFERENCE |

共10项闭包控制：3项静态接受、7项预期静态拒绝。混合环控制沿用图阶段先于最终Artifact hash的方式，故意保留改变后的leaf旧hash以定位图环；它不是原始反例的替代，不能声称该环值拥有自洽加密hash。原始反例则全部hash正确。

原R2 **36条静态矩阵仅复核一次**，分类保持：7 STATIC_ACCEPTED、23 EXPECTED_STATIC_REJECTION、1组含五项STATIC_MATCH、5逐项STATIC_MISMATCH。没有把五比较另加成通过总数，也没有单独再跑oracle比较。修正Package实际调用25次，其中15次来自R2矩阵的完整包检查；其余R2条目是已有定位字段控制，不冒称36次全包或功能通过。见[一次回归结果](../evidence/A03/execution/P2-R3-evidence-closure/r2-regression/controls-01/static-results.json)。

既有两scope/typed frame正包、直接scope/声明/跨书/伪frame/混合环控制，以及SESSION-02、CONVERSION-07已有正值/定位负值保持结果。它们仍仅有限静态接受；真实锁、读取、计数持久化、CAS、转换/重开、原生质量均未执行。未扩展R17或登记推导分支。

## 复现、原件和停止点

最短只读回放（实际拒绝，但“符合期待”时进程退出0）：

```powershell
python -X utf8 -B examples/a03/P2-R3-evidence-closure/replay.py --case original --expect UNDECLARED_REFERENCE
```

单个合法JSON控制可将 `--case` 指向上述case.json，`--expect STATIC_ACCEPTED`。全套有界静态控制在隔离复核副本内用全新run ID执行：

```powershell
python -X utf8 -B docs/evidence/A03/execution/P2-R3-evidence-closure/runner.py independent-r3 controls
```

实际运行[controls-01](../evidence/A03/execution/P2-R3-evidence-closure/runs/controls-01/exit.json)及[最短回放](../evidence/A03/execution/P2-R3-evidence-closure/runs/replay-original-01/exit.json)退出0；前者表示所有预期静态控制匹配，后者actual是UNDECLARED_REFERENCE，不表示原包被接受。启动前保存argv/cwd/脚本SHA及源码，stdout/stderr先持久打开，再启动子进程；退出/PID/alive均记录，无失败覆盖。本轮没有新增未预期失败。历史REWORK/NOT_RETAINED原声明保留，不重建冒充。

[旧文件及范围核对](../evidence/A03/execution/P2-R3-evidence-closure/delivery-verification.json)、[自有进程释放](../evidence/A03/execution/P2-R3-evidence-closure/process-release.json)、[统一清单](../evidence/A03/execution/P2-R3-evidence-closure/sha256-manifest.json)在原始流和退出完成后冻结。清单仅排除自身，覆盖全部新增产物，包括所有额外资源、反例原件、结果、加载pins及启动快照；旧Git原件逐字节不变、最终提交raw blob核对与干净状态以最终工具回执为准。

产品/planner/DB/native session、网络/平台/浏览器/profile/凭据/OCR/模型/安装/推送/调度state改动、联系B或验收者均0。只结束自己启动的同步静态子进程，无后台任务或全系统扫描。

**停止在REVIEW，等待主调度安排原独立审阅者。** R17版本桥接、登记推导scope正包、oracle/公共合同/native采用及I01保持原阻断，不作新的功能接受。既有字段重置专项继续 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议再测。
