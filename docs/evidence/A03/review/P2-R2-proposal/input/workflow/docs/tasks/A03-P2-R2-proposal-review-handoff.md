# A03 P2-R2：有界静态独立复验

2026-10-17。继续原独立验收对话，明确 `xhigh`。只审本轮三个静态缺口与明确残余，不实施产品/DB、不批准共同合同或I01，不自行扩展修订轮数。

## 冻结输入

- 工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；只读。
- base：`7fdbde8f16569fd3bc399013115e13269d5d33fa`。
- 交付：`526d264284f36f856c306db88c1d7e71c04152e1`；执行workflow `d834bf531f95abac7ed30b89b3ca55105fa6f491`。
- 执行报告：目标提交 `docs/tasks/A03-P2-R2-proposal-delivery.md`，SHA256 `e6df1732e7a3623047a4ed02457a1d5b453cb2aae3253a3913426a00fcf5b218`。
- 清单：目标提交 `docs/evidence/A03/execution/P2-R2-proposal/sha256-manifest.json`，SHA256 `75f158577e48f029e542674ad5216df0b41ea02df69e76cf646cd35f4a83ed64`，205项；加清单自身共206个新路径。
- [执行任务](A03-P2-R2-static-rework.md)、[上一轮独立结论](A03-P2-R1-proposal-review-report.md)、[调度决定](A03-P2-R1-proposal-coordinator-decision.md)。本次workflow由派发消息给出，不能合浮动主树。
- [主调度前检](../evidence/coordinator/heartbeat-20261017-0734/A03-R2-delivery-preflight.json)：205项及清单自身磁盘/raw Git一致，全为允许三处内新增，工作树干净；完成turn和10个已记录静态run退出核对，无产品/DB运行或当前profile扫描。

唯一候选 `examples/a03/P2-R2-proposal/candidate-final/profile.json`，profile=`a03-p2-r2-static-2-PROPOSAL`，SHA256 `f7385ba20090b5df8aa062c417e3d5c66a889a30f464facff994d9929b94f9ea`。新版本1.3提案、六份Schema pins/API/oracle/verifier exact集合从该候选读取。`candidate/`为保留失败值，旧R1 candidate-v2不作新候选别名。

## 复验边界与结果分类

1. 从固定Git blob隔离导出必要输入，逐文件对比运行字节；不能用未经逐blob核对的 `git archive` 断言原始字节。不复制历史全集；旧309项仅按明确引用取必需诊断/报告。
2. 先静态检查新checker及其依赖没有产品/DB/native调用，再按原任务检查同书两scope、不同计划、嵌套Resource全包、typed frame递归与混合DAG。关注整个包入口、普通引用不获scope豁免，以及具体拒绝位置。只运行已有依赖/标准库的纯静态检查。
3. 验证会话一致性、H0为STARTED前头、三读与Hfinal/唯一fact/CAS前驱的值级绑定。原两份诊断应以损坏字段触发拒绝，而不是仅版本不同即拒绝。真实锁/fence/read持久化不在本轮证明范围。
4. 核对新初始类型结构/语义registry一致、INITIAL/POST_HOLD区分、完整新旧映射与分母/资源摘要、COMMITTED唯一接纳点及中断状态。审阅固定oracle来源、五项独立预期和静态verifier；作者STATIC_MATCH不等于native PRE资格或B质量验收。
5. 对作者明确的两个残余单独给结论：R17的1.1 observation bridge与1.3新初始/PRE没有获准版本桥接；登记推导scope分支没有独立正包。判断它们分别阻断哪些入口，不能把三项局部静态自洽升级为整条恢复路线可实现。仅按冻结文本/源码说明最小后续选择及受影响接口，供调度缩小下一阶段范围；不自行修改公共合同、不发明适配器实现或新一轮大候选。
6. 逐项区分“本轮三个缺口是否闭合”“是否存在新的确定静态矛盾”“原生实现/功能是否获准”。若原列缺口仍存在，给一个可复现最小静态反例后收口；若三项成立但残余阻断，允许给有限静态接受＋残余BLOCKED。不要为了得到总ACCEPTED放宽标准，也不要无限寻找无关边界。

作者36条只包含7个静态正值、23个预期拒绝、一组五项match和五个mismatch，不是36项功能通过。保留check-01的READ_TIME失败和早期entry源码快照缺失限制；不能补造历史快照或将NOT_RETAINED恢复为通过。

禁止产品planner、DB、原生session、网络、浏览器、平台、profile、凭据、OCR、模型、依赖安装、提交/推送/集成或联系执行者/B/其他任务。旧被拒字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，不复跑、变形、委派或建议再次测试。

## 输出

只新增 `D:/1800/docs/tasks/A03-P2-R2-proposal-review-report.md` 和 `D:/1800/docs/evidence/A03/review/P2-R2-proposal/`。给exact输入/真实运行目录与摘要、静态命令和原始流/退出、必要正反样例、限制/残余选择、完整清单、自有进程结束；保留全部旧报告/材料，不改state或产品。完成后冻结结束，主调度依据独立结论裁定具体下一步；本轮不释放I01。
