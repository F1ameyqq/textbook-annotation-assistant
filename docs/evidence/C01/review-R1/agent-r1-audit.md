# C01 R1 映射与共享投影专项复验

日期：2026-10-16（Asia/Shanghai）。专项结论：**ACCEPTED**，仅指 R1 平台引用闭合及本稿列出的合同边界；最终 C01 验收和集成由主调度汇总决定。

被验交付 HEAD：`4e42668ab28eda37a37285285d2f6c595d3bba12`；代码提交：`cb684f90a2cd7bd7064ce1f30b7d024a49389132`；返修基线：`b8c4341d277d205dddfae22b26c245b646a1cea2`。冻结导出：`D:\1800\.local\stages\C01-review-R1\tree`。按 `docs/evidence/C01/review-R1/delivery-manifest.json` 核对 **84/84** 文件 SHA-256 匹配，commit 一致。

## 本次结果

独立自造 **22 个场景，22/22 通过预期**：12 个合法场景保持可执行资格，10 个非法场景被公开语义验证、资格 API 和 CLI 正确拒绝。负例同时核对错误 code 和字段路径；CLI 正例退出 0、负例退出 1。

运行环境 Python 3.9.13、Pydantic 2.12.5。没有使用作者固定样例构造本专项输入；沿用先前独立自造的基本交换包生成逻辑，按 R1 语义新增实体和映射。每场景保留完整 input.json、实际 PGM/文本/JSON 资源、result.json、cli-stdout.txt、cli-stderr.txt。所有依赖均经公共封签 API 重算，图像尺寸、原图摘要、依赖摘要、范围和答案归属保持一致；`validate_bundle(..., asset_root=case_dir)` 与默认 CLI 均启用资源字节校验。

主证据：[results.json](D:/1800/.local/stages/C01-review-R1/agent-r1/results.json)、[stdout.jsonl](D:/1800/.local/stages/C01-review-R1/agent-r1/stdout.jsonl)。每个场景的目录名与下表一致，均位于 `agent-r1/` 下。

| 场景 | 预期及实际 |
|---|---|
| known-mapping-baseline | ACCEPT |
| snapshot-directory-missing | REJECT / MISSING_REFERENCE / `.questions[0].directory_id` |
| snapshot-directory-duplicate | REJECT / DUPLICATE_ID / `.directories` |
| action-platform-id-missing | REJECT / MISSING_REFERENCE / `.target.platform_question_id` |
| graph-platform-id-missing | REJECT / MISSING_REFERENCE / `.external_refs.platform_question_id` |
| action-other-existing-id-conflict | REJECT / PLATFORM_MAPPING_CONFLICT / `.target.platform_question_id` |
| existing-action-requires-explicit-mapping | REJECT / PLATFORM_MAPPING_REQUIRED / `.target.platform_question_id` |
| existing-mapping-action-null-conflict | REJECT / PLATFORM_MAPPING_CONFLICT / `.target.platform_question_id` |
| new-null-target-nonempty-snapshot | ACCEPT |
| new-null-target-empty-snapshot | ACCEPT |
| empty-string-action-not-null | REJECT / MISSING_REFERENCE / `.target.platform_question_id` |
| empty-string-graph-not-null | REJECT / MISSING_REFERENCE / `.external_refs.platform_question_id` |
| known-order-conflict | REJECT / PLATFORM_MAPPING_CONFLICT / `.external_refs.platform_order` |
| unknown-order-accepted | ACCEPT |
| explicit-mapping-other-known-order | ACCEPT |
| two-internal-questions-share-platform-id | ACCEPT |
| parent-child-share-platform-id | ACCEPT |
| two-internal-dirs-share-platform-id | ACCEPT |
| different-internal-platform-dirs-repeat-order | ACCEPT |
| repeat-order-same-platform-directory | ACCEPT |
| shared-platform-id-second-order-unknown | ACCEPT |
| two-new-null-internal-questions | ACCEPT |

各场景分别调用 `validate_bundle`、`assert_plan_ready`，并从场景自己的 cwd 通过冻结包 CLI 消费已落盘输入。表中预期不是开发者测试的复制：明确加入了无父子关系的多个内部题共享平台 ID、不同内部目录共享平台 ID、不同及相同平台目录中重复题序、多个 null 新题并存等独立正例，用来检查修复是否误加投影约束。

## 源码专项审计

1. **F1 修复准确。** [validation.py:664](D:/1800/.local/stages/C01-review-R1/tree/src/annotation/contracts/validation.py:664) 检查快照目录唯一性，668–670 校验题目目录属于同一快照，错误定位标量字段。没有将平台目录与 SourceBundle 内部目录直接比较。
2. **F2 修复准确。** [validation.py:495](D:/1800/.local/stages/C01-review-R1/tree/src/annotation/contracts/validation.py:495) 到 506 校验当前图谱显式非 null 平台映射及已知题序；523–533 校验动作目标存在、与内部题已声明映射一致，并拒绝用 null 替换已有映射。两字段均 null 的新题目标仍合法。
3. **未发现新增一对一假设。** 代码用平台 ID 索引快照实体，但不要求各内部题的映射值互异；共享 ID 正例均通过。代码没有要求平台题序全局或目录内唯一，仅比较某个明确平台 ID 已记录的题序是否一致；同目录和跨目录重复题序均通过。未知内部外部题序 null 不参与比较。
4. **提案边界有记录。** [实现说明第 78–80 行](D:/1800/.local/stages/C01-review-R1/tree/docs/contracts-implementation-v1.md:78) 明确了 null/已有映射规则、目录命名空间和不添加一对一约束。非 null 动作而内部映射 null 时要求先显式记录并重新检查，是本轮保守实现提案，未称为双方已确认规则；本专项按该公开提案验证，不把 A 的通过解释为 B 接受。

未发现 R1 代码改动中的剩余阻断项。本专项没有重复主复核负责的 70 项作者测试、原 80 项矩阵、旧原始反例或四组安装跨目录消费，也没有扩大到外部 ID 格式设计。

## 复现

```powershell
python -B D:\1800\.local\stages\C01-review-R1\agent-r1-probes.py --tree D:\1800\.local\stages\C01-review-R1\tree --output-dir D:\1800\.local\stages\C01-review-R1\agent-r1 --frozen-commit 4e42668ab28eda37a37285285d2f6c595d3bba12 --manifest D:\1800\docs\evidence\C01\review-R1\delivery-manifest.json
```

退出 0，最终汇总 `count=22, passed=22, failed=0`。可用 `--only <场景名...>` 定向复跑。脚本要求显式冻结树，输出路径必须位于新的 `.local/stages/C01-review-R1/` 下，禁止落回旧证据目录。

冻结实现摘要：models.py=`592601b8049980c38e9fb837b7e47e90352409da5562b1b086a208904eb8e1ec`；validation.py=`ca4132322966b526c8e42d4bcff4d41bc43847cde8e5a1fe9c220da9c1b473b7`；integrity.py=`378cc52d6b701011b6d074e5cbed35811bf3d927e5a3bbeb08f6acef04ee45a0`。独立探测脚本 SHA-256=`d344c71aff1295cca09081195e535dd08381bc7122de2542493d281a88ea47be`。

## 限制

共享映射场景仅证明合同未误加一对一限制，不证明平台实际支持组合父子或多个内部题共享平台题的写入投影。显式映射的业务真实性、实时快照和真正目标核验属于后续平台适配及质量检查；W 口径和 B 接口确认仍未决。

本专项只写新的 R1 stage 目录，没有修改实现、协调状态、主报告、旧报告或旧正式 evidence；未使用浏览器/profile、未读取凭据、未调用模型或付费服务、未执行线上写入，也未集成或推送。
