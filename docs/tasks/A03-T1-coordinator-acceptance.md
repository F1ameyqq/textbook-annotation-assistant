# A03-T1 调度接受

2026-10-18。**ACCEPTED，限取证模块及 L1/U1–U5 六个固定离线场景**。被验 target 为 `ed90664ab15afd1938725441e2bc86db7884f784`，产品基线仍为 `1330047dd29890dea0e433ff01b991f615bf78f4`。

[独立报告](A03-T1-review-report.md)完成且作者、验收者均已释放。调度核对797项独立证据摘要、37个登记Popen完成记录、六组owner释放；在自有immutable副本查询六组终态，核对五组恢复前后原action/intent/permit及目标效果不变、native报告读取为0。调度另以固定raw helper运行一次最小SQLite同步夹具成功，业务调用0；没有重跑六个业务场景或全套测试。完整检查见[调度记录](../evidence/coordinator/heartbeat-20261018-0252/checks.json)。

允许T2消费的唯一工具文件为 `examples/a03/T1-capture/capture.py`，raw SHA256=`3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b`。在同步业务返回、所有写者已登记的独占场景调用；LeaseBoundary须stop/join后顺序复制，最终调用当前boundary.stop()。不声称双库原子，不修改lease/renewal。T2自己的固定产品raw执行视图另建，不带入T1业务驱动或运行产物。

作者seal.py的legacy表假设及报告view计数偏差保留；T2不消费该入口，不因修文档或汇总脚本重跑已通过六例。首次失败流的保留限制、旧U2/F2/F3缺件仍保留。A03整体REWORK，I01未释放；无平台或B共同确认。本决定允许下面明确的本地工具子集集成，实际提交及检查另记coordination-state.json；不表示完整T1历史或A03产品已合入主目录。
