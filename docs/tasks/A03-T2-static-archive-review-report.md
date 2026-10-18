# A03-T2 新归档清单的一次静态复核

2026-10-18（Asia/Shanghai）。最终结论：**ACCEPTED，仅固定target的C12/H1归属、历史报告链及此次新归档清单**。本轮依据此前已完成的独立四文件审查、C12一批和唯一H1实测，另作本次明确授权的一次静态复核；不重跑业务或旧封存器。

| 固定身份 | 值 |
| --- | --- |
| 被验归档workflow | `94c376914db82942ceb0246f338e5caa574cfb42` |
| 唯一新补证对象 | `docs/evidence/coordinator/heartbeat-20261018-0337/T2-archive-inventory.json` |
| 清单raw SHA256 | `55d35f4724962fd6e7de0878976aa2de92c5c5849c6c7886d3a31c9a02d3dcd2` |
| 产品完整target | `699f748a124162b3118e3996c03757725daac363` |
| 候选 / 产品基线 | `f111eb609d065a2506da52007c3b283928d537aa` / `1330047dd29890dea0e433ff01b991f615bf78f4` |
| T1工具集成 | `86ae44b27e7d4825bd05d54701072f4068151bb9`，工具/pins/输入不变 |

本次一个只读`git -c core.longpaths=true cat-file --batch`进程从固定workflow读取清单及其267个raw成员，逐项核对长度/SHA，并同保留的旧工作文件字节比较；没有读取移动HEAD。检查结果、实际Git PID/退出、流摘要和成员明细见[静态复核JSON](../evidence/A03/T2/review/static-archive-recheck.json)。未生成自引用manifest。

267项raw Git长度/SHA均匹配，267份保留工作文件摘要均相同；262个调度source/archived摘要关系均指向已核对成员。本轮没有重复散列262个原隔离源或24条外部大流；调度对此的既有核对仍按新清单引用。原24条外部流索引本身已作为成员核对，流继续留在原隔离目录。

七阶段14份raw SQLite作为普通字节核对，与此前完成审计记录逐一绑定；本轮没有导入sqlite3、打开SQL或重做5118项静态全审。已保留的11个验证进程退出均为0、无timeout，三个keeper已join，最终owner/PID为空、lease=0、phase=RELEASED、generation=3。这里只复核这些冻结记录的归属和字节，不冒称本轮重新运行或重新取得当时的观察。

因此，新workflow中的可核对清单补齐“缺最终清单”这一唯一归档阻断，正式有限接受固定target的原C12/H1及本次归档；不是在旧目录补造manifest。此前本对话亲自完成的C12/H1独立实测结果和四文件/历史consumer审查沿用，不以调度清单代替功能证据。

必须保留的限制：作者三次静态Git的PID/start/预登记及部分raw流缺口，实际退出2/0/0，仍未补齐；第一次验收静态审计失败及唯一纠正、第二次seal失败均保留。第二次失败只有工具解码trace，没有单独raw stderr/PID记录，不伪造补证。原最终验收报告继续为REWORK、原manifest继续不存在，旧字节全部未改；旧局部检查器的FINITE_T2_ACCEPTED也不改写。这里的新结论只对应本次被授权的新归档复核，不把历史流程改成当时完整。

本轮仅新增本报告和`docs/evidence/A03/T2/review/static-archive-recheck.json`，不操作旧目录、主Git索引/提交或协调JSON；一次静态进程完成后无自有后台资源待释放。零C/H1重跑、产品导入、SQL、旧audit/seal、安装、网络/平台/browser/profile/凭据、模型/OCR、推送或书级提交/A05题22，无作者/旧A03/B联系或委派。Python使用`-X utf8`；field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

A03整体仍REWORK，T3产品/K组合、I01和B共同确认未通过；D-M仍等待调度固定K与范围。本次完成后结束等待，不自动派发或扩大验证。
