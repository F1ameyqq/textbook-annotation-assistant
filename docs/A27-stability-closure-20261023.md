# A27 稳定性修复收口

2026-10-23：产品 `ebca4c71a70bdfb5fbccc023d00e0207ae532470` 已获正式独立及根协调有限离线接受，并快进接入 `C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800`，工作区干净。

正常批处理现在先做严格比较，仅对已证的新建题干/答案区三个直接字段的键序差异使用有限兼容结果。它不会生成标准 accepted marker，也不会自动取得后续 revision 前驱资格。

关闭处理保留成功业务回执、框架释放及操作系统释放各自的证据，并约束可协作关闭的等待。独立只读恢复需要原成功回执、意图、计划、请求记录与外层进程释放链，随后最多运行一个新 reader；入口没有保存分支，不重发 POST。同步阻塞和运行时线程仍需要现有外层 supervisor 保障。

独立验收首先发现 Windows 等价 profile 路径可绕过占用检查。R1 改为解析 Windows 命令行参数并比较实际目录身份；原反例现返回 `RECOVERY_PROFILE_IN_USE`，在 configure/capture 前停止，调用数均为 0。原候选 `23591811` 的 REWORK 和失败原件保留。

验证包括初版新增 20 项、受影响 9 项，以及 R1 新增 8 项、受影响 2 项。独立验收先得到 6 项通过和 1 个阻断反例；R1 再通过原反例及 3 项补充控制。未重跑无关旧套件或已有成功实测。根核对 R1 的 23 份报告、109 组原件副本、79 份新合成证据及 34 个 Git 原始依赖。

本结论为 `ACCEPTED_OFFLINE_ONLY`。新恢复流程的真实平台、真实 Edge 进程枚举与线上验证均未执行；不将这次修复当作新的实测成功。第 3 题原 strict FAIL、第 4 题原关闭异常及历史 ledger 不变，旧关闭根因仍为 UNKNOWN。

- [正式独立结果](evidence/A27-independent/r1-review/result.json)
- [正式独立报告](evidence/A27-independent/r1-review/report.md)
- [根协调收口](evidence/coordinator/a27-final-stability-closure/receipt.json)
- [产品接入记录](evidence/coordinator/a27-product-adoption/receipt.json)
- [已完成的五题实际交付](A26-five-native-delivery-20261023.md)

原五题交付包及 151 份根冻结实际/成品材料保持不变，根历史 102 份脏文件保全。`1800-a` 保持 PAUSED；未推送远端、联系 B 或授予新线上轮次。
