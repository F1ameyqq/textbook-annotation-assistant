# A03 P2-R7 产品只读 codec 交付

状态：**REVIEW**，等待原独立验收。本轮实际实现产品模块 `annotation.contracts.a03_bridge`，仅 A_INTERNAL_READONLY / STATIC_INSPECTION，不是继续提交提案，也没有采用原生 PRE/CURRENT 或写入资格。

base `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4`；workflow `5a69df310517f0ca22708262c737db9a5676be32`。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。[固定任务](../evidence/A03/execution/P2-R7-readonly-codec/inputs/workflow/docs/tasks/A03-P2-R7-readonly-codec-implementation.md) SHA256 `fc32fe579d2131cb38a9682b6497060cc3469b604507a9dde9bb145919d7766c`；调度输入 pins SHA256 `4ba6e0a646f403f552d71c091b62d0a53623f5ea90728ffea7dd2bab8ec172b1`。保留用户当前模型/思考设置，没有改档、委派或合浮动主树。

## 产品接口与迁移

[产品 API](../../src/annotation/contracts/a03_bridge/__init__.py) 提供任务单规定的 select_static_codec、open_static_context、validate_static_bundle。选择描述采用确切内置 profile/schema/API/rules pins，只有 STATIC_INSPECTION；给定 selection 时核对具体类型、字段类型及全部固定字段。CURRENT/未知角色和错误 pins 均拒绝。Context 仅含固定选择和显式解析后的 asset_root，无 writer、session、PRE handle 或“已批准”布尔值。

ValidatedA03Bundle 保存完整输入的隔离 canonical bytes、canonical_sha256、冻结 selection 和 Resource(path/raw_sha256) 元组。对象无 __dict__，data 深层只读，model_dump() 每次返回完整独立副本。没有删 UNKNOWN、登记事件、Artifact 或 ref 来生成缩减执行视图；输出只是本次字节的静态验证结果，不是持续锁或原生凭据。

[规则迁移对应表](../../examples/a03/P2-R7-readonly-codec/migration-map.json) 逐项对应 R2 完整 Package.validate、R3 正式 EvidenceRecord 闭包及 R5 上下文/target 修正。产品正常 import 产品代码，不 exec/AST 改写旧源码、不加载 examples、不导入旧 oracle/main/session/conversion。完整 Schema/registry、exact refs、Artifact hash、Resource raw SHA、正式 ID/字段权威、每消费者声明/book/scope、typed prefix、全局图和 mixed DAG、registration target 及 PRE 静态尾段均保留。

必要差异：先 shape 后建立索引；合并重复 shape 及覆盖层为普通产品类；Resource 仅来自显式根，规范化路径并检查实际解析边界，去除 overrides 与仓库 fallback；只缓存已读原始字节，每个上下文重新解析/检查，不共享 found/scope 通过缓存；错误为现有 ContractError 子类，保留明确 code/path，并增加有限 JSON、路径、IO 错误。原 C01/1.1 默认入口未改。

[内置数据索引](../evidence/A03/execution/P2-R7-readonly-codec/packaged-data-index.json) 固定 6 份 Schema、API、profile 原 raw bytes及新只读角色记录，共 9 份。原 profile 的 STATIC_UNIMPLEMENTED/implementation_authorized=false 不变；oracle/verifier SHA 仅为来源元数据。新记录 SHA256 `41f50606ad8b2283acad08ae5d63e0c40681ec424c83c026fe654d3c3734880c`。唯一根配置变化是 pyproject.toml 的显式 package-data 条目，依赖/版本/其他配置未改。

## 固定七包的新入口结果

[新夹具索引](../../tests/fixtures/a03/P2-R7-readonly-codec/index.json) 逐项对应 R5 六包及 R6 修正混合环。bundle 与原 raw Git 字节相同，资源只按原逻辑 path 物化；故意损坏的全局 Resource 保持原始 51 字节及不匹配声明，未在准备中修好。[执行前静态核对](../evidence/A03/execution/P2-R7-readonly-codec/pre-execution-static-audit.json) 在产品测试前落盘。

| 新产品入口场景 | 实际结果 / 拒绝位置 |
| --- | --- |
| registration-positive | 完整返回 STATIC_ACCEPTED，完整 dump 与输入相同 |
| source-binding-negative | FRAME_REGISTRATION_BINDING，r4-static/source-binding-negative/prefix.json |
| snapshot-binding-negative | FRAME_REGISTRATION_BINDING，r4-static/snapshot-binding-negative/prefix.json |
| target-tuple-negative | FRAME_REGISTRATION_TARGET，r4-static/target-tuple-negative/prefix.json/registration/target |
| r3-original-undeclared-evidence | UNDECLARED_REFERENCE，origin-a-SourceBundle |
| global-resource-hash-corruption | RESOURCE_HASH，r5-static/global-only-proof.txt |
| R6 修正混合环 | MIXED_CYCLE，A:760b541bec881e9d98abb75f38bc7e34a75d2ed047edbc8ac657091c70fdc320 |

这些代码仅在对应规则位置产生；没有用更早的 Schema/hash 错误替代绑定/DAG 层。输入业务字节及原预期语义均保留，未执行任何旧 A03 入口或旧 36 矩阵。

## API、路径、兼容性及安装验证

[product-01](../evidence/A03/execution/P2-R7-readonly-codec/product-01-result.json) 运行 13 项：12 通过，符号链接解析边界因 Windows 1314 跳过。7 个固定包、CURRENT/未知角色、错误 profile/schema pin、伪造选择类型、未知 envelope、非有限数、输入/dump/深层视图隔离、未知 Schema 断言 fail-closed、相对/绝对路径拒绝均有记录。

只对跳过的解析边界补充 Windows 目录联接备用方式，[path-01](../evidence/A03/execution/P2-R7-readonly-codec/path-01-result.json) 单项补测通过，验证根内路径实际指向根外普通临时文件时 RESOURCE_ESCAPE。没有重跑其它已通过检查；产品代码自首轮前静态核对起未改，产品缺陷修复/重跑为 0。原跳过及测试源码快照保留。

[原 C01 入口](../evidence/A03/execution/P2-R7-readonly-codec/c01-01-result.json) 仅运行 test_contracts*.py，共 **70 项全部通过**，没有扩大到 A03 功能测试。8 个原测试子进程逐个保存 argv/cwd/限时/PID/raw stdout/stderr/退出；其中 CLI 拒绝用例的非零退出是原测试预期，不能误记为运行器失败。

通过现有 setuptools 82.0.0 / wheel 0.46.3 的 build_meta 离线构建，未安装或下载。使用独立 staging，未在旧 src 写 egg-info；完成后只清理已核对位于自有临时根内的目录。[wheel 结果](../evidence/A03/execution/P2-R7-readonly-codec/wheel-result.json) 固定分发文件和 9 个 raw 数据 pins。

[wheel 文件](../evidence/A03/execution/P2-R7-readonly-codec/distribution/annotation_contracts-0.1.0-py3-none-any.whl) SHA256：`c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7`。

[仓库外验证](../evidence/A03/execution/P2-R7-readonly-codec/isolation-result.json) 在清除 PYTHONPATH 的外部临时目录解压 wheel，实际导入路径为 `C:/Users/ASUS/AppData/Local/Temp/a03-r7-isolation-ia1yvnpo/unpacked/annotation/contracts/a03_bridge/__init__.py`。实际分发版本 0.1.0、9 数据 pins 一致，正包和 target 负控经新入口通过。该进程只有 wheel 和两份新夹具，不依赖原 examples/docs/Git；自有进程退出后清理临时目录，__file__ 是本轮实际历史记录。仓库内实际产品 __file__ 为本工作树 `src/annotation/contracts/a03_bridge/__init__.py`。

## 留痕、保全与停止

[完整 raw 输入 pins](../evidence/A03/execution/P2-R7-readonly-codec/raw-input-pins.json) 含 170 项；[C01 消费脚本补充 pin](../evidence/A03/execution/P2-R7-readonly-codec/compatibility-input-pins.json) 单列。raw Git 与 checkout 的纯 LF/CRLF 转换分别记录；七包、资源、内置数据仍要求原始字节一致。pyproject 唯一配置追加以 raw Git 基线核对，未把换行转换冒充配置变更。

保留两个准备阶段失败：freeze-01 因最初未区分 pyproject 的 Git LF 与 checkout CRLF 而 AssertionError；prepare-01 因元组/列表拼接 TypeError 在写数据前退出。原脚本、流、退出 1 保留；修正的只是输入记录/准备工具，均发生在任何产品测试前。随后 freeze-02/prepare-02 成功，无产品语义失败被覆盖。wheel 仅有关闭 byte-compiling 的告警，未安装依赖。

首次 Git 暂存 whitespace 检查对 wheel-01 原始 stderr 末尾空行报告非零。日志原字节保留，仅为新证据范围内 stdout/stderr 添加 -whitespace 属性；产品/夹具/测试未改或重跑。预封存清单、进程记录及属性原件保存在 provisional/，封存差异另记 seal-adjustment.json，最终清单覆盖这些历史材料，仅排除最终清单自身。

[旧文件先行指纹](../evidence/A03/execution/P2-R7-readonly-codec/old-preservation-before.json) 与 [终检指纹](../evidence/A03/execution/P2-R7-readonly-codec/old-preservation-after.json) 核对 28,410 个旧路径的字节及 mode/type/blob（仅排除授权追加 package-data 的 pyproject）。[归档核对](../evidence/A03/execution/P2-R7-readonly-codec/archive-verification.json)、[全部新/授权修改文件清单](../evidence/A03/execution/P2-R7-readonly-codec/sha256-manifest.json)（仅排除自身）、[自有父运行释放](../evidence/A03/execution/P2-R7-readonly-codec/process-release.json) 及 [嵌套进程释放](../evidence/A03/execution/P2-R7-readonly-codec/nested-process-release.json) 一并封存。记录输入/脚本摘要、argv/cwd/限时、原始流、PID、退出/超时/alive；不输出全量环境或凭据，不扫描/停止他人进程。

复现说明见 [README](../../examples/a03/P2-R7-readonly-codec/README.md)。只读归档命令不执行产品或测试：

```powershell
python -X utf8 -B docs/evidence/A03/execution/P2-R7-readonly-codec/archive.py --check
```

提交 raw Git blob、范围和干净状态在冻结时核对，确切 commit 由交付消息给出。静态 codec 不运行旧 session/conversion 的协议接纳，也没有 PRE 实际 producer、CURRENT/原生 authority、历史 creation-input 执行视图或持久 UNKNOWN 恢复链。A03 整体功能、R17、S01、I01、oracle/跨侧采用仍未通过。无网络/平台/profile/凭据/OCR/模型/付费 API、推送或 B/验收者消息。字段重置专项为 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**。交 REVIEW 后停止。
