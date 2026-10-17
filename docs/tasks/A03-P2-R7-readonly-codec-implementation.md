# A03 P2-R7：产品只读 codec 实现

2026-10-17。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，保留用户当前模型/思考设置，不改 thinking/model、不委派。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`；唯一 base `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4`。调度消息给出 workflow 与任务摘要，按 raw Git 读入，不合浮动主树。

## 目标与边界

R6 静态控制已收口，见[R6 调度决定](A03-P2-R6-mixed-control-coordinator-decision.md)。本次实际编写产品代码：把 R2 完整 Package 校验、R3 正式 EvidenceRecord 消费者闭包和 R5 登记上下文修正迁入独立可导入的只读 codec。输入/规则 pins 见[固定输入清单](../evidence/coordinator/heartbeat-20261017-1144/R7-input-pins.json)。不是新的设计稿、提案检查脚本或示例加载壳。

只批准 A 内部 `STATIC_INSPECTION` 角色。保留原 `a03-exchange-3-proposal`、`1.3.0-a03-static-proposal` 和 `a03-p2-r2-static-2-PROPOSAL` 值以及 Schema/API 字节；新角色采用记录明确只授权只读校验。原 profile 的 STATIC_UNIMPLEMENTED/implementation_authorized=false 原字节不得改写，它不代表已批准原生运行。1.1 Artifact 只作为该固定静态 envelope 已允许的不可变历史输入；不新增旧 envelope 自动升级、降版重封签、CURRENT 或写入接纳。

此次不实现 BridgeContext 的原生 authority 部分、AdmittedPreRun、CurrentWriteEligibility 或 HistoricalDerivationView。它们不是空壳通过或可用占位符：应不存在可发放资格的实现，任何 CURRENT/未知角色选择均明确拒绝。后续原生任务须另冻结 R4 留下的 PRE producer、INITIAL/POST_HOLD 生命周期和 creation-input anchor；本次成功不越过该依赖。

## 冻结的只读接口

在 `annotation.contracts.a03_bridge` 提供以下 Python API，调用者不需要访问仓库 examples、docs 或 Git：

1. `select_static_codec() -> BridgeSelection`。返回不可变选择描述：codec_id=`a03-static-readonly-v1`、role=`STATIC_INSPECTION`、exchange_version、artifact_versions（固定 1.3 与只读历史 1.1）、profile_id/profile_sha256、schema_pins（有序不可变名称/摘要对）、api_sha256、validation_rules_id=`a03-r2-r3-r5-r6-static-closure`、adoption_scope=`A_INTERNAL_READONLY`。全部来自内置确切 pins，不接受任意白名单或调用者指定采用记录。描述对象不是 authority。
2. `open_static_context(*, asset_root, selection=None) -> BridgeContext`。selection 省略时取上述唯一选择；提供时验证具体类型及全部固定字段，不能只检查对象名字或 role。context 只包含这个选择和显式解析的 asset_root，不含 writer、session、PRE handle 或“已批准”布尔值；不得由 JSON 反序列化出资格。
3. `validate_static_bundle(bundle, *, context) -> ValidatedA03Bundle`。接收 JSON 原生数据，拒绝非有限数/不符合固定结构的输入；先做固定完整校验，再返回隔离且不可变的快照。输出含 selection、bundle 的 canonical SHA256、已消费 Resource 的 path/raw SHA256 清单和完整验证后的数据；`model_dump()` 只返回独立副本。修改原输入或 dump 不得改变已验证对象。输出仅证明此次读取字节的静态结果，不是持续文件锁，也不能成为原生计划/执行凭据。发生错误使用明确 code/path，兼容现有 ContractError 体系或明确的子类。

模块可以将模型/资源读取/Schema/闭包规则分文件实现，常规局部实现选择由执行者完成，无需另开设计轮。原有 `contracts.validate_bundle`、`assert_plan_ready`、seal、C01/1.1 默认分发保持原行为；本轮从明确的新模块入口调用，不把 proposal 自动放进既有 writer 路径。

## 规则迁入与可安装性

- 迁入的完整入口必须保留：固定 Schema/registry、exact refs、Artifact hash、全部 Resource 原字节/摘要与路径边界、正式 EvidenceRecord 唯一 ID/字段定位、每个真实 Artifact/frame 独立 found/declared/book/scope、无上下文全局遍历、registration Source/Snapshot/canonical target、typed prefix 与混合 DAG，以及固定 Package.validate 的 PRE 静态尾段。全局遍历不能捏造 None-book 消费者，不能因资源已访问就跨上下文复用通过结论。
- 产品代码正常 import 产品模块；禁止 exec/AST 改写旧源码、动态加载 examples、绝对工作树路径、静默 fallback 到原候选目录或硬编码样例 ID/结果。允许迁移固定纯校验规则并清理运行器/输出目录初始化，但逐项列出对应关系及差异。不要导入或执行旧 main/session/conversion/oracle compare，也不将旧静态 PRE 当作真实 run。
- 内置 Schema/API/profile 等必要数据放 `src/annotation/contracts/a03_bridge/data/`，原 raw bytes 与 pins 一致。schema interpreter 只支持冻结方言，遇未知断言 fail closed，不声称通用 JSON Schema 认证。oracle/verifier 摘要仅保留为来源元数据，不加载、不执行、不批准它们。
- 资源均来自显式 asset_root，校验规范化路径及实际解析后的根边界，不提供未经校验的 overrides 字典。测试包可把原 case 映射的分散资源按固定 path/SHA 物化到新的单一 root；这是测试准备，不能改业务 JSON/旧文件或成为产品 fallback。
- 可用现有本地 Python/依赖离线构建，无安装/下载。为将新数据打入 wheel，调度作为根依赖负责人仅允许在 pyproject.toml 新增该包的显式 package-data 条目；不得改任何依赖、版本、其他包配置。若本地缺少构建工具，记录事实，用隔离 src 拷贝证明 import，wheel 项标 NOT_RUN，不安装补齐。

## 允许写入范围

新增 `src/annotation/contracts/a03_bridge/`、`tests/test_a03_r7_readonly_codec.py`、`tests/fixtures/a03/P2-R7-readonly-codec/`、`examples/a03/P2-R7-readonly-codec/`、`docs/evidence/A03/execution/P2-R7-readonly-codec/`、`docs/tasks/A03-P2-R7-readonly-codec-delivery.md`。pyproject.toml 仅允许上面的 package-data 条目。其他 src、旧 tests/examples/docs/证据、根依赖与调度 state 保持原样；不得重写任何 R2–R6 输入或报告。

## 有界验收

先实现和静态检查，再经新的产品入口执行下列有限集合。迁移改变了实际实现，因此这些是新入口的直接回归；不重跑旧入口、旧 36 矩阵或原 P2 全套。

| 集合 | 检查与结果 |
|---|---|
| 七个固定包 | 原 R5 六个接受范围内的 case，加 R6 修正后混合环。正包完整返回；Source/Snapshot/target、未声明正式证据、全局 Resource hash、混合环分别在原约定语义层拒绝。固定输入与原 raw Git 逐项核对；不能仅以同退出码/更早无关错误判定通过。 |
| 角色与版本 | 对固定输入分别尝试 CURRENT 角色、错误 profile/schema pin、未知 envelope 版本；全部拒绝，不能改输入版本后重封签升级。仅新静态 API，无 DB/native 调用。 |
| 数据快照 | 原输入及 model_dump 返回副本的修改不改变已验证对象；对象不暴露可变嵌套数据。保持 UNKNOWN/登记历史及全部 Artifact/ref，不生成缩减的“可执行”视图。 |
| 路径边界 | 新测试资源 root 外的相对逃逸/绝对路径拒绝；不读取 .local、profile 或凭据。新临时普通文件即可证明。 |
| 隔离可用性 | 在仓库外临时目录、清除 PYTHONPATH，使用离线构建/解压的 wheel 导入实际产品模块，报告 __file__、分发文件和数据 pins，运行正包及一项 target 负控；不能依赖原 examples/docs/Git。缺本地 build 工具按前述限制记录。 |
| 兼容性 | diff 证明旧产品默认入口未改；只运行原 C01 合同测试入口以发现包装副作用，不扩张 A03 功能测试。 |

最多一次针对本轮局部缺陷的修复，仅重跑受影响集合，保留首轮失败。新独立语义问题或需要扩大范围时给出最短失败/代码位置/依赖后停止，不能以新增大量候选或放宽预期持续迭代。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`；本轮不进入该专项、DB、注册表修改、native dispatch 或其变形。

## 交付

冻结实际提交，报告状态 REVIEW，由原独立验收对话在交付确切版本和自有进程释放后复核。报告列接口、迁移对应关系、完整输入 pins、实际 __file__、命令与结果/拒绝层级、差异、限制和未运行项。新增文件清单只排除清单自身；必要 raw Git 输入即可，不复制历史证据全集或重复保全大清单。旧文件保全用 mode/type/blob 差分证明。

每个实际子进程记录输入/脚本摘要、argv/cwd、限时、原 stdout/stderr、PID、退出/超时/alive；所有自有进程结束、工作树干净后交付。测试临时产物不得混入旧证据。不得自行标 ACCEPTED/INTEGRATED、推送或联系验收者/B。无网络/浏览器/平台/模型/OCR/付费 API；S01、A03 原生功能、R17、I01 及跨侧合同均未释放。
