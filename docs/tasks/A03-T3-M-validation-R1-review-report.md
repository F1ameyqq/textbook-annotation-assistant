# A03-T3 M-validation-R1 固定失败交付只读复核

2026-10-18（Asia/Shanghai）。**REWORK；本次只读收口完成。** 改动、八个前置负控留存、看门狗中断、实际效果/未决及释放事实相符；本轮未发现该四文件差异中明确跳过实际bytes、pins、registry、root或公开重验的静态缺陷。M/A03功能仍未通过，I01未释放。本结论不自动发起优化、替代实现、延长时限或重跑。

## 固定对象与核对方法

| 身份 | 确切提交 |
| --- | --- |
| 本次workflow | `f82ae616a528b0fb8d98d4b4ee6d0fb52bf7363b` |
| 最终交付F | `d5f777590e72eb070af0497afdb144d60c61b95d` |
| 首次业务前候选R | `b8c75119c556b61e36b0cc1f817dbc53044cce41` |
| 起点 | `7b9245eaa55bad1699ee40baf71be09dd6df8371` |

F中执行报告raw SHA256为 `558c0072064a5cb84c1ddd3e9d0db09a964427f810aeaddebd5338a699bfa88f`，新index为 `af95d10819a8086ece40d69ca81b04fa891ebde6b4b5d14a104e6d378afaee41`。调度已核334成员，本轮不重新逐项封存/核验全集；只读固定差异、测试入口/断言、原始完成文件和已有JSON/SQL导出。必要引用与复算见[只读记录](../evidence/A03/T3/review-M-validation-R1/readonly-checks.json)。

未导入产品、执行任何测试/业务/诊断/基准或连接SQLite；没有打开、恢复或继续任何pending库。清理后SQL.json只作为已有导出读取，不称终止瞬间SQL。

## 改动与前置控制

产品差异限四文件：native合同 `__init__.py`、`runtime/storage/native.py`、native `data/profile.json`和`adoption.json`。新增私有 `_validate_native_for_registry(registry,bundle,asset_root)` 在每次调用中检查真实registry身份、strict root，以新reader完成一次原_validate_value，再用此次data/manifest签发context，经当前select_native_codec及require_context核对后返回NativeBundle。NativeRuntimeStore._validate登记实际root并调用它；没有caller预验证标记、公开skip开关或跨调用PASS缓存。

静态独立比对确认：

- native合同原15个顶层函数AST不变，包括完整_validate_value和公开context/验证路径；新helper显式完整_validate_value调用恰为一次。公开消费者仍重验。
- NativeRegistry整类AST不变；NativeRuntimeStore原21个方法AST不变，只增加_validate覆盖。因此native._append仍在原位置调用self._validate，owner/head/pending/hold/fence/intent/permit等原方法没有因本次去重而删除。
- profile其他字段不变，仅两项实施pin与实际新文件摘要匹配；adoption只更新profile摘要。schema/oracle、共同合同确认状态及fresh-only/迁移边界未被本次改动开放。

八个控制通过真实NativeRegistry和NativeRuntimeStore.__new__验证夹具进入新路径，不init运行库、不创建目标或dispatch；它们不证明真实运行资格或完整保存/恢复。实际命令明确选择 `--validation-controls`，不是旧全集或五例留存验收。原stderr为“Ran 8 tests in 1.295s / OK”，控制子PID73640为exit0、1.546秒、waited、alive=false。

| 控制 | 真实断言/留存结果 |
| --- | --- |
| 缺嵌套正式引用 | 新路径EXACT_REF，定位nested_ref |
| 第二consumer借用声明 | 第一consumer先实际合格；第二consumer新路径UNDECLARED_REFERENCE |
| 错书 / 错scope | 新路径分别FOREIGN_BOOK / ORDINARY_SCOPE |
| 成功后资源字节变化 | 新路径再次调用和旧context公开消费均RESOURCE_HASH |
| 成功后实施字节变化 | 新路径和旧context公开消费均NATIVE_IMPLEMENTATION_PIN |
| 错root | 空目录使真实资源读取RESOURCE_READ；不外推为所有同字节副本root都非法 |
| 未登记registry/context | 新helper拒绝NATIVE_REGISTRY_REQUIRED；伪context公开消费拒绝NATIVE_CONTEXT_REQUIRED |

共8个具名测试、11条合并拒绝断言；results.json中实际code与预期逐条一致，正向data/manifest/digest/root/registry比较也有留存。资源/实施字节控制限定可丢弃副本并有finally恢复，不能解释为修改正式产品。**本轮审读上述作者执行证据，没有独立重跑，也不把这8项升级为M功能接受。**

## 45.031秒中断与正式事实

原完成记录与facts提取一致：execute子PID25324实际45.031秒，timeout=true、kill/wait、exit1、alive=false；M1父PID35968为45.219秒、exit1、timeout=false、waited。业务matrix只有这一失败项；M2-sufficient、M2-insufficient、M3-new-plan、M3-final-drift均NOT_RUN。该模式没有调用诊断探针或基准，子stderr为空，无终止前新栈，不能定位kill瞬间内部函数。

独立从已有清理后SQL导出、清理前后public JSON核对：

| 项目 | 实际保留状态 |
| --- | --- |
| 新业务起点 / DISPATCH_STARTED / target effect | 1 / 2 / 2 |
| observation / PRE | 5 / 1 |
| 三动作 | APPLIED、INTENT、RESERVED；第三无intent/fact |
| intent / permit | APPLIED、PENDING；两个permit均CONSUMED |
| 正式产物 | 一份ExecutionProgress；无ExecutionReceipt、BatchReport；没有第二APPLIED正式fact |
| reconcile、readonly entry、报告读 | 全部0；finish/query/replay未进入 |

第二实际效果及读回行存在，不等于第二正式结果已提交，更不等于三动作完成。当前保留的一个pending正是不能自动续写/重发的事实；作者报告未用两个效果替代完整回执或报告。

**45秒是从单题合成场景继承的看门狗配置，不是业务SLA。** 它说明这次验证被中断、未形成所需功能证据；超时本身不足以判定保存/恢复语义错误，也不能证明验证去重无收益。与旧轮进度的差别没有受控性能对照，本轮不推算收益正负或要求新基准。

## 保全与释放

释放辅助先在自有worker结束后保存新终止DB及当时存在的sidecar，随后一次正常open，等待既有lease自然到期6.919369秒，不延长、不循环，再claim/release一次。辅助PID60988实际8.078秒、exit0、waited、alive=false；未重复旧capture/journal失败路径。本轮没有重新打开这些库。

前后public动作及effect_log一致，导出的事件头14→17仅增OWNER_CLAIM_RESERVED、OWNER_ACTIVE、OWNER_RELEASED。计划INTERRUPTED/cursor1；owner=null、lease=0、RELEASED、generation2；**pending=1、paused=true保持**。release-proof的dispatch/reconcile/PRE/publisher均为0。正常open后的public与释放后SQL不能冒充终止瞬间独立SQL，顺序双库复制也不是原子快照。

5个登记子过程（控制、execute、观察子、M1父、释放辅助）完成记录逐份吻合。观察子PID36208为exit0、alive=false，原文件未另记waited；外层包装63772的自记录/工具退出边界不补造wait字段，不为此追加补证。worker的keeper随已终止进程结束，清理后只余MainThread。历史233/263成员及旧失败保持原记录，不重封、不继续它们的pending。

## 本次收口

仍缺原M1三动作完整执行、正式receipt/新鲜报告、重开/旧动作拒绝，以及后四例功能证据；这些不是当前可据静态检查填成通过的结果。已核对改动与8个作者控制，不能据此释放M/A03或I01。

**本次不安排下一轮修复、替代架构、诊断或延时重跑。** 用户关于等价替代实现的讨论由调度处理；本报告只封闭这份固定失败交付事实，等待后续明确范围。

本轮只新增本报告及一个小型只读记录，未修改产品、执行树、旧证据、协调JSON、Git索引或提交。自有只读Git批处理均已communicate/wait结束；无自有业务进程、owner、keeper、后台或profile会话待释放，不是全机PID扫描。

field reset保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`；零网络、平台、凭据、安装、费用模型、OCR、推送、A05题22或书级提交，不联系B/退役A03、不委派。最终状态：**REWORK（只读事实收口完成，M/A03功能未接受，I01未释放）**。
