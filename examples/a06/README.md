# A06：固定 B 原生包的只读接收入口

本地交付状态 **REVIEW**，等待独立验收和调度决定。A 基线为
`a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`；实现冻结提交为
`9076d35e81678cdba8ad8651e95a44265fdc345c`。最终交付提交仅追加本文、报告和证据，产品字节不变；
见[执行报告](../../docs/tasks/A06-execution-report.md)。本说明未发给 B；没有共同映射确认或联合业务验收。

B 包提交 `0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f`，包说明代码基线
`c3cc2df7a0be24c125c83681c0499c0d328d78f6`。仅消费固定的
`B-46007447-Q16-offline-HOLD-2026-10-17.zip`（11,681,712 bytes）：

```text
ZIP SHA256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d
manifest.json SHA256 3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f
run_id pipeline-run-0a2c03e193694ef88953f3ca08b8cde2
package schema b-handoff-package-trial/0.1
```

不从分支 HEAD、B UI 或网络补对象。原 ZIP 不改写；路径由调用方提供。依赖使用本机既有
CPython 3.9.13、Pillow 11.3.0、pydantic 2.12.5；本任务未安装依赖，也不提供清洁安装证明。

## 最短导入与固定消费者

以下 `$repo` 是这个固定 A 候选的完整导出根；`$package` 是原 ZIP 的显式本地路径。
采用显式源码路径导入，不依赖旧 editable 安装。可以从任意 cwd 调用。

```powershell
$repo = 'D:/path/to/fixed-a-checkout'
$package = 'D:/path/to/B-46007447-Q16-offline-HOLD-2026-10-17.zip'
$env:PYTHONPATH = "$repo/src"
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python "$repo/examples/a06/consume.py" $package --sha256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d --manifest-sha256 3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f
# 等价公共 CLI：
python -m annotation.source.b_handoff $package --sha256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d
```

```python
from annotation.source.b_handoff import HandoffError, receive_package, version_policy

received = receive_package(package_path, expected_sha256=zip_sha256,
                           expected_manifest_sha256=manifest_sha256)
receipt = received.receipt
native_graph = received.documents['artifacts/graph.json']
# documents 保留所有外层及内层原生 JSON 值，不补字段、不转换 C01。
# HandoffError 有 code/path/message/layer；as_dict() 提供拒绝回执。
```

`expected_sha256` 必填；`expected_manifest_sha256` 可选。消费者 stdout 是 JSON 回执，成功完成
只读诊断退出 **0**（decision=HOLD），拒绝退出 **2**。`--documents` 另外输出全部原生 JSON，
包括未逐字段解释的档案、候选、风险、检查复用依据和未知字段；数据库与脚本仅核对成员字节。
API 返回的 JSON 值保持字段和值；不声称返回重新编码后的字节与原文件相同。

回执字段：`input` 是实际 ZIP/manifest 身份；`versions` 分别记录当前 E/G/Check/report；
`scopes` 保留原 source/package 五页范围及当前相邻答案前缀范围，保留 Evidence 自有 run 和
Graph/Check 缺失的 run_id。`pipeline.stages` 记录当前运行回执、wrapper/result 精确引用及
三个最终对象的真实嵌套路径。READY 只表示流水线阶段状态。

`integrity` 报告字节/对象/图像核对数量；不是测试数或质量分。
`assets` 区分原图、裁片及 viewer-173/resource-173。`content.entities[].native` 保留当前题答的
全部字段，`layers` 分别定位来源 fragments、活动 content_fragments、typed regions/render_regions；
不按 OCR 数量推框，`platform_box_count=null`。`region_drafts` 保留来源区域，即使旧来源片段列表为空。
`character_spans` 按 Unicode 码点、左闭右开读取；JS 使用 `Array.from(text)` 后切片，不能用
UTF-16 字符串下标。plain/LaTeX runs、图像/文本区域和内容片段引用分别处理，不核准文字。

`archives` 只标记精确引用绑定的 0.4/0.5 archive，并给出原生文档指针及候选/风险/core/basis 路径；
不把档案作为当前检查。其他旧版本只保留在原生文档，未宣称逐字段语义兼容。
`references` 区分原生产物、原生文档、资产、裁片和 acquisition receipt，不制造 C01 kind/revision。
`issues` 保留当前127项原生问题。

## 版本矩阵和边界

| 版本/位置 | 结果 |
|---|---|
| 当前 E `b-evidence-trial/0.3`，G `b-graph-trial/0.7`，Check `b-check-trial/0.7` | 仅固定 run 只读诊断，READ_ONLY_HOLD |
| G/Check 0.4、0.5，精确绑定的历史 archive | ARCHIVE_ONLY，保留混合区域、候选/风险和历史复用依据 |
| G/Check 0.4、0.5，当作当前顶层 | ARCHIVE_ONLY_NOT_CURRENT |
| G/Check 0.6 | UNSUPPORTED_VERSION；无完整 G06/Check06 正样例 |
| 未注册版本 | UNSUPPORTED_VERSION，返回路径和版本 |
| 未注册入口形状 | UNSUPPORTED_ENTRY_SHAPE；未绑定 archive 为 UNBOUND_ARCHIVE |

`version_policy(schema_version, kind=..., location='CURRENT'/'ARCHIVE', bound_archive=...)` 是公开分派
查询；仅返回分派规则，不能独自签发包接收资格。真正入口会独立检查 archive 引用，不能依赖调用方的布尔值。

固定历史引用 `b-evidence-18e2d1ee2a22288f585513f0` / revision 1 /
`a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da` 同时输出
**UNRESOLVED_HISTORY_REFERENCE** 和 **UNCONFIRMED_REQUIREDNESS**，`optional=null`。
返回 HOLD 诊断不代表完整语义闭包成立，也没有把该引用判为可选。

正常回执始终包含 `decision=HOLD`、`business_acceptance=false`、
`c01_execution_eligible=false`、`transcription_verified=false`、`joint_mapping_confirmed=false`。
34题、66答案均为候选数量，127为当前问题数量；不生成交换包、ApplyPlan、PASS 或平台资格。
本实现只承诺固定小包，不承诺任意规模、内容正确率、整章覆盖、OCR、平台保存或 B 内部算法验收。
未知字段完整保留但未逐字段解释；公共格式资格和共同业务语义仍未确认。

## 四个完整入口与确定性配方

```powershell
python "$repo/examples/a06/verify.py" $package "$repo/docs/evidence/A06/author/new-run" "$repo/tests/fixtures/a06/generated/new-variants"
```

两个输出目录必须是新目录。驱动调用独立子进程中的公共消费者：原 ZIP → HOLD；坏 JPEG →
RESOURCE_INVALID/RESOURCE；陈旧 Check → STALE_CHECK/CURRENT_BINDING；未知 G →
UNSUPPORTED_VERSION/VERSION。配方 [make_variants.py](make_variants.py) 只操作新副本，固定 ZIP
成员顺序/时间/压缩，重算非破坏点的 payload hash、wrapper/result、对象文件名、依赖、report 和
manifest。配方记录逐文件前后身份及预期层。变体均称 TEST_VARIANT，不是 B 新交付。

输出含原始 argv/cwd/退出码/stdout/stderr、版本矩阵、模块实际 `__file__`/SHA、公共合同样例和
子进程回收记录。生成的大 ZIP 保留在本地 ignored generated 目录，按配方重新生成；原包只按路径和
摘要引用。验证记录见执行报告，作者执行不构成独立验收。

## 已有公共合同 API 与 C01 固定消费者

这是另一个消费者：`annotation.contracts` 提供 A 提案 `1.0.0-a-proposal` /
`c01-exchange-1`，不能直接把 B trial JSON 输入它冒充兼容。本次没有修改其实现、样例或依赖。

```python
from annotation.contracts import load_bundle, validate_bundle, schema, ContractError, SCHEMA_VERSION
bundle = load_bundle(c01_input_path, verify_assets=True)
validated = validate_bundle(bundle, asset_root=c01_input_directory)
json_schema = schema()
```

```powershell
python "$repo/examples/contracts/consume.py" "$repo/tests/fixtures/contracts/normal"
python "$repo/examples/contracts/consume.py" "$repo/tests/fixtures/contracts/exception"
python "$repo/examples/contracts/consume.py" "$repo/tests/fixtures/contracts/unknown"
```

完整复制每个样例目录及 assets。normal 是 SYNTHETIC/SIMULATED APPLIED 待人工提交；exception
是合成结构异常；unknown 是合成 UNKNOWN/RECONCILE、不重放。它们证明公共 API 固定消费，不能
提升真实 B 草稿的执行资格。`load_bundle` 校验 C01 结构/资源/引用；`schema()` 不替代语义校验。
更完整的既有 API 说明见 [contracts-implementation-v1](../../docs/contracts-implementation-v1.md)。
