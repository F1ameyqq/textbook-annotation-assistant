# A12-R1 正式独立差量验收

结论：**ACCEPTED_PREPARATION_FOR_ONE_REUSE_ONLY_OBSERVATION**。仅有限离线准备通过；本验收不启动或授权 live。

真实验收对话 `01a157a5-495a-7bf3-bc17-299ad85c48a7`，封存时间 `2026-10-20T13:18:25.131030+08:00`。

产品/作者驱动 `d45ed25a98361002ddb28985c1d27687c4421a17`；最终交付 `81fab23e3e7e9e32a36d3857a253afc69b5bd3e1`。
workflow `4e300c8d7c544a0f802425827906783efb1344e8`；来源 `0c30b365ed18b006bcab32bed4acb60869ff9f92`。

候选清单 SHA256 `38eb3f836f14b44db77ce516f461bd4f3934df71807c1fac962560603a210920`；交付清单 SHA256 `b615681648be2ce5c35c5e7e6502733b135c26be4d0e070b5c6838eb4094ded7`。
独立冻结 SHA256 `e1570981a0e99395df55683aa396bced6e3b795976457d72f9978e8fe7e87898`；独立驱动 SHA256 `6a512ed978897cee212f4b00cc22f22be29454a5c02ddbdc94213660b0a5b544`。

独立 raw 核验：53 输入逐一匹配固定 Git blob；31 新增、31,181 旧成员保全（含原 A12 22 文件），0 旧路径变化。网络 allowlist、发送前 Fetch/WS/子目标边界、TLS、profile、原共享 live 输出/启动标记、期限及精确 Job 释放未放宽；受保护实现通过 AST 对比。

唯一一次独立 D1–D8，**8/8 PASS，562 ms**，首意外失败为 null。独立 fake 仅替代外部 page/context/runtime，真实产品观察、错误处理、最终化及序列化路径均未修改。输入和独立驱动已先冻结；原作者 suite 及 N1–N3 均未运行。

| 项目 | 结果 | 实测 |
| --- | --- | --- |
| D1 | PASS | Windows binary PIPE 实收 `7b22636f756e74223a307d0a`，产品父协议接受零计数；exit0。 |
| D2 | PASS | 恰好八个固定异常输入全部拒绝，无扩展矩阵。 |
| D3 | PASS | 正常受保护 viewer 观察；shutdown-only stopped 未变成真实失败。 |
| D4 | PASS | LOGIN_REQUIRED，零登录动作。 |
| D5 | PASS | 密码 await 内实际 guard.block_seen，failure=None，最终 ERROR，viewer 未继续。 |
| D6 | PASS | viewer await 内首次错误保留，关闭期间后续错误未覆盖。 |
| D7 | PASS | 预存原错误保留，导航与 DOM 均未运行。 |
| D8 | PASS | DOM 暂定成功后关闭 await 内出现错误，最终 ERROR；再次关闭错误未覆盖首次错误。 |

唯一合成协议子进程 PID70780，创建 FILETIME134369469928825883 前后相同，exit0、退出时间已观察，双管道及精确保留句柄均关闭。六项内存 fake 各关闭 context/runtime 一次。运行后重核全部 53 输入及冻结独立文件，原 bytes 均不变。

R01/R02 仅在当前固定 R1 和该有限差量范围关闭；旧产品/交付及原 REWORK 报告保持。原 N1–N3 网络证明仅在未变实现范围有限沿用，没有新浏览器流量证明。

仍未证明真实专用 profile/占用/认证、平台书籍/源/框/保存读回、全部 worker/popup/iframe 动态分支、强制期限和异常释放分支、全部异步交错、B 采用或集成。未运行作者封装工具。本轮无浏览器、服务器、平台、真实占用扫描、profile/凭据访问、登录或业务写入。

独立差量及合成子进程额度均剩余0，已停止并释放；不能修后重跑、增加候选或恢复旧额度。后续仅主调度可另行登记同一个尚未使用的至多一次 reuse-only 观察，并核实际 profile、占用、标记和精确期限。其他三例 HOLD，Q22 不重放，0 B 消息。

证据：[固定 raw 与保全](raw-preflight.json)、[独立冻结](independent-freeze.json)、[逐项原始结果](run/suite-result.json)、[精确释放](run/independent-release.json)、[运行后保全](postrun-integrity.json)、[完整报告](report.json)、[raw 输出清单](raw-output-manifest.json)。
