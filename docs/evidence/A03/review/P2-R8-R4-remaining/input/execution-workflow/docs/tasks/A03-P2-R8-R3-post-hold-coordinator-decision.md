# A03 P2-R8-R3 调度结论

2026-10-18（Asia/Shanghai）。target `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f` 的 **POST_HOLD 修复及 local、N1–N5 有限范围 ACCEPTED**。A03 整体仍为 REWORK；native 产品尚未整体集成，I01 依赖未释放。

依据：[独立报告](A03-P2-R8-R3-post-hold-review-report.md)，SHA256 `a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17`；[调度复核](../evidence/coordinator/heartbeat-20261018-0356/review-audit.json)。独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 的 turn `01a14b31-db89-79f0-846d-640f65cd48bb` 已完成，cursor `abdea222-4697-4046-86b1-a5dc48889fac:42`。

## 已关闭的缺口

POST_HOLD 现在能在合法 owner/generation 下启动只读预检、核对当前性并正式接纳；INITIAL、pending 和普通写入的禁令保留。独立 N2 在同一真实 hold 下产生两个不同 generation/head 的 ADMITTED 运行，旧证明及真实 60 秒超时被拒绝，hold 未清除，效果仍为一次。不同 hold 替换、合格解除 hold 后恢复写入没有由本例证明。

独立 local、N1–N5 各一次通过。N1 完整单动作恢复保留原 UNKNOWN/null 原回执；正式晚到 receipt、两个 material progress、fact、intent 一致，新 POST/Batch 使用新观察，内容 PENDING、NOT_SUBMITTED。N3 证明五项合法输入确实到达语义比较层并分别 FAIL；它只是比较器负控，不宣称完整接纳路径负控。N4 缺失/序列化/他属凭据与观察拒绝且无效果；N5 保留历史/静态角色边界，未证明旧 1.1 归档转换能力。

调度核验 manifest 1,137 条及清单自身，共 1,138 个文件；678 份输入与 1 份补充依据共 679 份 raw Git 导出吻合。19 个审阅父进程及 10 个嵌套进程的登记、原输出和 wait/退出记录吻合；三个审阅元数据脚本失败及更正原样保留，产品组没有重跑。调度另建自有 immutable 双库副本做 SQL/正式资源交叉检查，确认 25 个正式 artifact、3 个 ADMITTED PRE、7 次目标观察和唯一效果；未调用产品、未重跑测试、未连接原库。先前摘要的“1,137 文件”少计了清单自身，此处以实际清单计数为准。

## N7 原失败的处理

原 N7 在旧入口拒绝原生目标时，新增断言要求外层错误码 `TARGET_STORE_VERSION_UNSUPPORTED`；实际 `ContractError` 继承 `ValueError`，被外层捕获并包装为 `TARGET_STORE_CORRUPT`，消息保留版本不支持原因。冻结的 V08/R14 要求 fail closed 和可定位错误，没有约定这个精确外层符号。已审源码/合同/测试中未见依赖该符号的其他消费分支。

因此本调度采用独立分类：**这是新增驱动断言过严，本轮不要求修改 persistent.py，也不重跑这个失败路径**。原 FAILED 与 stderr 永久保留，不能改成 PASS。该差异对外层诊断可见；没有原 N7 专用前后摘要对，不补称所有 I/O 完全未变化。初始化中断分支当时尚未到达。

## 剩余工作与派发

继续原执行对话补 [N6 与初始化中断的有限验证](A03-P2-R8-R4-remaining-validation.md)：只增加验证驱动和证据，当前没有已确认的第二个产品修复。使用全新 N1 作为 N6 的必要前序，完整历史不能裁剪；初始化中断使用已有 before_completion 钩子。遇到新独立产品失败即冻结，不同轮不断修补。交付后由原独立验收对话审查，保留用户手动思考强度。

原 P2 V01–V10/R01–R18 仍按覆盖表逐项处理；本次未用有限单题样例替代整体验收。之后才核定 native 本地集成及 I01。B 包只读/HOLD 小切片可独立准备，双方版本映射仍未确认。归档是本地证据提交，未推送、未通知 B。

字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。没有平台、浏览器、凭据、OCR、付费模型或 A05 题22操作。
