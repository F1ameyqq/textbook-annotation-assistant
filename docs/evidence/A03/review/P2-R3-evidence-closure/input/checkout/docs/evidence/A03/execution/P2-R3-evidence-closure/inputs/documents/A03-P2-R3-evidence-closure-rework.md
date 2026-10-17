# A03 P2-R3：正式 EvidenceRecord 消费者闭包修复

2026-10-17。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，明确 `xhigh`。工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`，base 固定 `526d264284f36f856c306db88c1d7e71c04152e1`。包含本任务及冻结审阅归档的 workflow 由派发消息给出精确 SHA；不合浮动主树。

## 本轮目标与输入

只补 [R2 独立报告](A03-P2-R2-proposal-review-report.md) 的 `R2-SCOPE-EVIDENCE-ID-01`，遵守[主调度收口](A03-P2-R2-proposal-coordinator-decision.md)。报告 SHA256 `32d23d9e3f42ace9d6eadd88e7af2d45ffbaa58c765268056f78464f54898030`；清单 SHA256 `5b62f0ee7c893dfd419609445a118a974219269b1e87a4b9e65f2ce402092612`。

反例位于 workflow 的 `docs/evidence/A03/review/P2-R2-proposal/counterexample/evidence-id-consumer/`。`bundle.json` SHA256 `b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653`；两个 Resource 的确切路径、摘要及覆盖字节见同目录 `result.json`。原消费者是新 1.3 receipt 的 `results[0].before_evidence_refs`，经唯一 EvidenceRecord ID 与两层 JSON Resource 指向未声明、另一 scope 的 Source。字节、四元组、内容摘要均正确，路径不含 typed frame；原完整 Package.validate 误接受。

本轮仍为**纯静态提案修复**。SESSION-02、CONVERSION-07 已有有限静态接受，保持其语义与数据。R17 版本桥接和登记推导 scope 正包继续 BLOCKED；不借此实现产品、原生恢复或新版本适配。

## 唯一写入范围

只新增 `examples/a03/P2-R3-evidence-closure/`、`docs/evidence/A03/execution/P2-R3-evidence-closure/`、`docs/tasks/A03-P2-R3-evidence-closure-delivery.md`。不得修改任何旧路径、调度 state、产品、根依赖或公共合同。

复用基线中固定 R2 candidate-final、Schema/API、checker 依赖与 oracle 的字节；只导出实际需要的冻结输入，不复制历史证据全集或重新生成一套大候选。允许一个小的静态验证器修订/覆盖层及必要定位控制；报告须说明实际入口、源码与输入 pins。覆盖层如复用 R2 模块，所有本轮包检查均须经过修正后的唯一 Package 总入口，不能用旁路小函数替代。冻结原件一律只读，运行输出重定向到本轮目录。该修订不改成新的原生 profile 接纳资格。

## 必须闭合的行为

1. 建立唯一 EvidenceRecord ID 索引，只按合同已定义的正式证据引用字段解析；缺失/歧义不能静默跳过。不得仅以任意同名字符串扫描代替正式字段规则。
2. 在每个实际 Artifact 或合法 typed frame 的消费者上下文中，将正式证据 ID 解析到 Resource，再递归检查嵌套 JSON 普通引用：该消费者自己的 input_refs、book/scope 均适用。正确缓存资源字节可以复用；消费者上下文检查不得被全局缓存跳过。
3. Artifact/frame→证据→Resource→Artifact 的边进入同一个混合 DAG。保留 R2 typed frame 的明确子消费者边界；普通 evidence 不获得跨 scope 例外。不能通过禁用全部合法 JSON evidence 来“修复”。
4. 原最小反例必须由修正后的完整入口在声明/scope层拒绝，不能靠修改版本、删除证据、摘要损坏或换反例得到拒绝。若相同原例存在多个正式消费者，应列清拒绝位置，同时证明新 1.3 receipt 消费路径确实被检查。

## 最小验证与停止条件

- 固定原反例应拒绝；一份合法的普通 JSON evidence 递归引用控制应接受（声明、同书 scope 均正确）。
- 用有限的直接控制证明：同一资源被不同消费者消费时各自检查；正式证据 ID 缺失/重复被拒绝；普通证据依赖接入混合环检测。只做本缺口相关控制，不开展无关字段或原生边界搜索。
- 在修正总入口复核既有两 scope/typed frame 正包，以及已有直接 scope/声明/跨书/伪 frame/混合环控制；SESSION-02 与 CONVERSION-07 的已有正值和已定位负值保留结果。若重用作者的 36 条静态矩阵，一次记录其真实分类即可，不能记成 36 项功能通过或另加 oracle 五比较凑总数。不重跑旧产品功能矩阵。
- 如新入口揭露旧正包原本违反同一规则，保留原件，仅用最小新增差量说明；不要放宽规则、重造全部规范或自行追加修订轮。遇到无法在上述范围内解决的矛盾，给最小证据和具体选择后冻结并结束。

## 交付与禁止事项

交付确切 commit、报告/清单摘要、入口与实际加载源码摘要、必要输入 raw Git 字节索引、完整正反例及资源、错误码/位置、复现命令、限制。启动即保留 stdout/stderr、argv/cwd/PID/超时与退出记录；失败不能覆盖。清单覆盖全部新增产物（自身除外），核对旧文件不变、工作树干净、自己启动的运行全部结束，再交 REVIEW。执行者不能自记 ACCEPTED；之后由主调度安排原独立验收对话复验。

禁止产品/planner/DB/native session、网络/浏览器/平台/profile/凭据/OCR/模型/收费 API、安装依赖、推送、联系 B 或验收者。oracle 采用、公共接口版本确认、登记分支和 I01 均不释放。既有字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，不复跑、不变形、不委派、不建议再测。
