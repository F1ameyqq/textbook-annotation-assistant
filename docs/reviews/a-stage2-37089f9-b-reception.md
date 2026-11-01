# A 第二阶段发布的 B 侧接收核验

2026-10-18，Asia/Shanghai。A 分支 `codex/a-stage2-handoff`，实际远端提交 `37089f9e0229da76ae1c45461b7e63929590be56`；本轮 B 输入基线 `4bb0a0086c3f69e9ad46d55466295870a409ec59`。本报告确认代码已经可获取，并记录 B 在独立目录运行 A 固定消费者的结果，不代替 A 对 B 新增单题附件的接收回执。

## 已验证

从该固定提交获取独立源码快照，压缩包 commit 标识吻合；A 发布清单的131个来源成员，大小、SHA-256和Git blob全部一致。没有覆盖 B 工作目录、合并 A 分支或修改 A 源码及 pins。

使用 A 的 `examples/a06/consume.py` 读取 B 原包，传入 ZIP SHA `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` 和原 manifest SHA `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f`。实际退出0、stderr为空，结果：

- `decision=HOLD`、`business_acceptance=false`、`c01_execution_eligible=false`、`joint_mapping_confirmed=false`。
- 34题候选、66答案候选、127检查问题；固定14阶段及来源/依赖校验完成。
- 完整 stdout 3,698,309字节，SHA `6755c0573edd0cc47371f0634d84881bf7ddf03611e59a3fd5491422676a3ba8`，与 A 随包封存的原接收 stdout **逐字节相同**。
- A 接收视图里的第1题 `q-e92a499995ca1bbd570a2a09` 和答案 `a-b22c88c763b7dfb917d02d18` 的 native 对象，与 B 本轮指定清单完全相同；A 保留原始层级，没有因为缺少 `content_fragments/render_regions` 而丢失本题。

A 自带5项窄测试通过，范围是版本路由和阶段结果 kind/schema。C01 三份静态样例 normal/exception/unknown 经公共消费者读取均为 EXACT_MATCH；没有 dispatch，没有新建 ApplyPlan 或模拟执行回执。样例自带的 PASS、READY 或3动作只是原静态数据，不能算本题或本轮业务成功。

本机环境为 Python3.11.8、Pydantic2.13.4、Pillow12.2.0；A 历史接受环境为 Python3.9.13、Pydantic2.12.5、Pillow11.3.0。本轮是现有环境下的源码模式接收验证，不宣称重新完成固定依赖清洁安装或 wheel 验收，未为此安装/更改依赖。没有重跑 A03/I01 历史业务、B 流水线、模型或平台。

## 接口差异和下一步

1. **历史附件尚未由当前 A06 消费。** 接收 API 只接受原包路径和摘要，没有旁文件参数；当前代码仍输出 `UNRESOLVED_HISTORY_REFERENCE/UNCONFIRMED_REQUIREDNESS`，`optional=null`。B 已在4bb0a00补交对应 E0.1 原字节文件及“直接快照消费非必需、上游重建必要”的依据；不修改原 ZIP，不篡改接收回执来消除该标记。后续由 A 确认并设计旁文件审计或记录其处置，不代表 A 的既有固定消费者有回归。
2. **两侧内容摘要算法不同。** B trial 的 `content_hash` 只对 payload 计算；C01 `canonical-json-1` 对规范模型的整个对象、排除顶层 `content_hash` 后计算。适配时必须生成 C01 独立信封/身份/摘要并保留 B 原始引用；不能直接搬用 B 的 hash、补几个字段后称为 C01 已封签。公共版本 `1.0.0-a-proposal` / `c01-exchange-1` 已可获取，但真实题映射及共同语义尚未冻结。
3. **当前真实题仍 HOLD。** [单题确认](../b-a-single-real-question-46007447.md) 中的作答括号、答案估计框、题答关系及31范围问题适用性尚待核准。A 提供单题政策和覆盖处置，重新完成五项 PRE_APPLY 与模拟 TARGET，再决定是否形成正向计划。不能把此次 A06 可读和 I01 历史合成链拼接成真实 B 正向联合通过。

目前能确认的是“取得 A 固定实现并复现只读 HOLD”，不是“真实题已进入模拟”。A 的新交接文档仍引用最初三项确认请求，尚未记录对 B 4bb0a00 单题及历史补件的接受。

## 回执和复现

机器摘要：[book-46007447-a-stage2-reception.json](../../evaluation/book-46007447-a-stage2-reception.json)。完整 stdout、测试日志及三个静态消费者输出已封存在 [接收证据 ZIP](../../handoffs/b/46007447/B-A06-stage2-37089f9-readonly-reception-2026-10-18.zip)，包 SHA `cf8f947d480ad3d58a9461c96e218a20bd60700e922351706e9c1f4fd9bac096`；清单 SHA `1b076002670225b463663227428afeda69414d259cdc1e9f4e5a2fd53086ceee`。归档后逐项重读校验通过。

在 A 的独立固定源码目录，设置 `PYTHONPATH` 指向其 `src`、`PYTHONIOENCODING=utf-8` 后：

```powershell
python examples/a06/consume.py <原包路径> --sha256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d --manifest-sha256 3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f
python -m unittest tests.test_a06_versions tests.test_a06_stage_results -v
python examples/contracts/consume.py tests/fixtures/contracts/normal
python examples/contracts/consume.py tests/fixtures/contracts/exception
python examples/contracts/consume.py tests/fixtures/contracts/unknown
```

首次从子进程下载源码遇到本机网络绑定错误，改用直接下载获得完整快照后才执行上述验证；接收本身一次成功。发布状态以本报告所在 PR head 为准。
