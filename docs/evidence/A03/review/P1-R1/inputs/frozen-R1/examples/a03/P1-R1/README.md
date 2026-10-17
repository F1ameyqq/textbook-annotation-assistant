# A03 P1-R1 候选设计样例

状态为 DESIGN_ONLY / P1 REVIEW。本目录只包含候选 JSON Schema、API 声明、静态数据生成器和静态检查器；恢复、提交、新观察、权限、效果与拒绝行为全部 **EXPECTED_NOT_EXECUTED**。

修订依据是冻结 P1 `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9`。原 P1 文件没有覆盖；`pre-continuation/build_r1_examples.before.py` 保留续跑前脚本，SHA256 为 `11ee6f7a865a8c06e6311f5c862537f360596a36b82c7df4e772d7315752d810`。失败生成目录、stdout、stderr 保留在 `attempts/`，它们是作者工具过程，不是平台或功能证据。正式消费包为 `data/`，不能把 `attempts/` 当作最新候选。

从仓库根执行最短只读静态命令：

```powershell
python -B examples/a03/P1-R1/check_design.py --root examples/a03/P1-R1/data
```

单独搬运本目录也可以运行：

```powershell
python -B check_design.py --root data
```

检查只使用 Python 标准库；不导入 src、旧 checker 或任何恢复/数据库/目标业务模块。Schema 检查器仅覆盖本包使用的 JSON Schema 关键字，遇到不认识的断言会失败；不宣称完整标准认证。网络、浏览器、平台、凭据/profile、OCR、模型和付费服务调用均为 0。

`data/case-mapping.json` 一一保留原 42 案例的路径、原 SHA256、新 SHA256、预期语义层与错误码。`data/case-manifest.json` 共 69 个案例：原 42、12 个未尝试 ABSENT 提交 API 前提案例、15 个引用闭包/Schema 邻近案例。原恶意例保留原预期层；`actual_static` 只报告形状、引用、资源字节、摘要与静态字段一致性，`semantic_actual` 一律为 NOT_EXECUTED。静态拒绝分类与未来 API 语义错误码不是同一层。

未尝试 tail 的候选 fact 采用 `origin_phase=UNATTEMPTED_ABSENCE`，有非空 `unattempted_basis` Resource；EXECUTION、RECOVERY 的该字段必须为 null。`data/unattempted-basis.schema.json` 是非 Artifact 资源的小 Schema。basis 绑定原 plan/action、owner/generation、target/store/session/source/scope、完整未调用前缀与两个独立新观察的静态输入，事实序号为 head+1。其 gate、观察和前缀字段均为设计数据，不能自行建立实际权限。未来入口 `commit_unattempted_absence` 只能从当前拥有的闸和当前库产生/核验这些事实，不接受调用方自报 JSON 作为授权。重复相同事实也拒绝 `UNATTEMPTED_FACT_DUPLICATE`，没有幂等成功分支。

API 负例中的 `runtime_claim` 是合成前提：wrong-plan-action 改实际请求 action ID；missing-absent 另给 scope 不完整的第二观察 Resource；stale-observation 重用第一次观察身份；incomplete-prefix 另给缺首事件的前缀；prepared-mismatch 改只读 prepared 的 action ID；重复/冲突给出当前库既存绑定。它们不是实际 API 调用。bundle 保留正例的拟议事实图用于结构对照，不宣称失败请求已经提交该事实。B UNKNOWN 保持 pending/pause，旧计划 INTERRUPTED，旧 tail 不续发。

普通 ArtifactRef 必须精确四字段，同 namespace/book/scope，身份、kind 与 hash 完全匹配。每个消费 Artifact 都要在自己的 input_refs 声明 payload 及其任意深度 Resource JSON 的全部普通引用。正式 evidence_refs、before_evidence_refs、after_evidence_refs、submission_evidence_refs 中的字符串，只按所属 bundle 唯一 EvidenceRecord ID 表解析，再作为当前消费者展开相应 Resource；其他字符串不是引用。解析文件的缓存不能代替消费声明，去重只在同一消费者内进行。

检查资源先核可搬运路径及 SHA256，再解析 JSON；Artifact 与 Resource 共用依赖图，拒绝混合环和资源环。`nested-resource-cycle` 故意保留无法得到一致摘要的资源环，实际先在 RESOURCE_HASH_MISMATCH 拒绝；不能把它冒称已走到环拒绝分支。`mixed-artifact-resource-cycle` 的有效资源字节指向消费产物身份，实际到达引用环静态门。所有循环、观察新鲜度和事务行为均未功能执行。

`data/migration-map.json` 澄清 namespace=(schema_version, exchange_version)，未来索引键=(namespace, book_id, scope_id, artifact_id, revision)，kind/hash 为不可变唯一绑定；跨旧/新 namespace 可以保留相同本地 ID/revision。转换只生成候选设计数据，不迁移历史结果，不解除旧无 intent UNKNOWN。版本标识没有变成自动选最新规则，需结合本次修订 profile、Git 提交和 Schema SHA256 明确选定。

需要重新生成时，生成器只读取旧 P1 静态文件并写到本目录内一个尚不存在的子目录；不是常规检查所需，也不会覆盖 data：

```powershell
python -B examples/a03/P1-R1/build_r1_examples.py --output examples/a03/P1-R1/new-reproduction
python -B examples/a03/P1-R1/check_design.py --root examples/a03/P1-R1/new-reproduction
```

完整设计选择见 [R1 提案](../../../docs/a03-recovery-contract-v1-r1-proposal.md)。P1 静态自检相符不等于独立通过，也不授权 P2；S01、根 Pillow、B 确认和 I01 边界继续未解决。
