# A10：获准的一次自有句柄清理差量

2026-10-19。用户已明确回复“允许这一次清理差量修复与验证”。依据[授权](../approvals/A10-owned-handle-cleanup-delta-approval.json)及[具体建议](A10-owned-handle-cleanup-correction-proposal.md)，本次追加范围只用于固定候选 `5543aba6fdcc146a5b1439a539ba0046e5f11cda` 的清理段，不恢复旧额度。原候选23项离线通过及清理缺口、首个A10本地失败和原启动标记全部保留。

## 唯一实现范围

只新增 `docs/evidence/A10/cleanup-delta/` 与 `docs/tasks/A10-owned-handle-cleanup-delta-execution-report.md`。在新目录保存原 bounded_checker.py 的修订副本，唯一源码差异限原第97–104行清理段：每个流独立尝试关闭；Popen原始句柄无论此前流关闭是否异常均尝试关闭；handle_closed只表示句柄实际关闭成功；任一清理异常仍拒绝。原退出身份未证明不得因清理成功而变为成功。

原 process_check.py、native_windows.py、session_delta.py、ProfileLease、枚举/匹配/20秒有效期限/额外2秒退出确认均按原候选raw摘要引用。不要复制整包、改旧源码/报告/证据、改根依赖、触碰真实profile、运行native/CIM/浏览器/平台或登录。新副本导入时明确引用原冻结依赖，不做monkeypatch，不用新任务名掩盖旧候选。

## 冻结及唯一验证

先准备补丁、固定五例伪资源驱动及有限静态语法/逐字差量核查，再冻结实现及驱动候选；冻结后作者仅一次运行五例差量：正常、stdout.close异常、stderr.close异常、handle.Close异常、两流均异常。验证全部适用close均被尝试、handle_closed准确、失败不返回占用数、成功仍返回原计数。使用原来明确的伪子进程/伪API思路，不真实创建检查子进程，不重跑旧23项或旧业务矩阵。失败立即保留并停止，不改后重跑，无第二差量候选。

独立审查在固定交付与释放后进行：先核原字节依赖及仅清理段差异，自己的一次相同五例离线验证，核实际关闭调用轨迹和失败状态。独立只新增 `docs/evidence/A10/cleanup-delta-review/` 及 `docs/tasks/A10-owned-handle-cleanup-delta-review.md`。不得启动平台。两方均给确切实现/最终提交、raw成员清单及释放；调度核证后才决定进入原计划中尚未发生的最多一轮平台只读访问。

当前真实平台写入、OCR、送审、题22重放、推送、B消息均为0。平台连接和书46007447许可已明确，无需再次确认；新写入清单和次数仍待平台现状核对后固定。
