# A03 P2-R7：产品只读 codec 独立验收

2026-10-17。继续原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`。保留用户当前模型与思考设置，续发消息省略 thinking/model；不委派，不修改执行工作树、冻结输入或调度 state。

## 冻结输入

| 项目 | 固定值 |
| --- | --- |
| base | `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4` |
| target | `8ad45dd07214ae406a3fab28d76a4b5abd6eef03` |
| 执行 workflow | `5a69df310517f0ca22708262c737db9a5676be32` |
| 执行任务 | `docs/tasks/A03-P2-R7-readonly-codec-implementation.md` |
| 执行任务 SHA256 | `fc32fe579d2131cb38a9682b6497060cc3469b604507a9dde9bb145919d7766c` |
| 执行报告 | `docs/tasks/A03-P2-R7-readonly-codec-delivery.md` |
| 执行报告 SHA256 | `24ae0a28230da26458d6dc6427587e932788d7b8d71e1eceded771001028b2ad` |
| 执行清单 | `docs/evidence/A03/execution/P2-R7-readonly-codec/sha256-manifest.json` |
| 执行清单 SHA256 | `92361002a2fad609255a7954fabef9f0ffa45082962811ca41b27aaf43a5c8d3` |
| 固定七例及源规则 pins | `docs/evidence/coordinator/heartbeat-20261017-1144/R7-input-pins.json` |
| 固定 pins SHA256 | `4ba6e0a646f403f552d71c091b62d0a53623f5ea90728ffea7dd2bab8ec172b1` |

审阅 workflow 和本单 SHA256 由调度消息给出。按 raw Git 读取本单、[执行范围](A03-P2-R7-readonly-codec-implementation.md)、固定 pins，以及[调度交付前检](../evidence/coordinator/heartbeat-20261017-1229/A03-R7-delivery-preflight.json)。执行工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` 已清洁冻结到 target；执行对话已 completed。不要合入浮动分支。

前检独立核对了 339 个清单条目和清单自身、170 项原始输入 pins 加 1 项 C01 兼容输入、28,410 个旧路径 mode/type/blob，以及 13 个父进程和 10 个嵌套子进程的登记/退出/原日志摘要。唯一已有文件变更是 pyproject 的显式 package-data 附加项，依赖未改。前检未导入或运行候选产品，不能代替独立功能验收；释放依据是自有进程历史记录，未扫描系统或 profile。

## 验收范围与方法

本轮验收实际新增的 `annotation.contracts.a03_bridge` 只读产品模块，接受范围为 `A_INTERNAL_READONLY` / `STATIC_INSPECTION`。不会批准原生 PRE、CURRENT 资格、SQLite 恢复或写入。原 profile 的 STATIC_UNIMPLEMENTED/implementation_authorized=false 及 1.3 proposal/Schema/API 必须保持原字节；检查新采用记录准确表达这一区别。

1. **独立代码与数据核对。** 核对 target 的允许路径、原始字节和所需输入 pins；只提取本轮必要文件，旧证据只读。核查 R2 完整 Package、R3 正式 EvidenceRecord 闭包、R5 登记上下文迁入的对应关系，不能仅相信作者映射表或通过数。确认新产品正常 import，不执行 examples/AST/exec、旧 main/session/conversion/oracle，不使用源码目录 fallback、绝对工作树路径、硬编码样例答案。固定 Schema 方言遇未知断言须拒绝。
2. **实际完整入口。** 以冻结七例及原资源，经新产品公开 API 各执行一次：registration-positive 完整成功；Source、Snapshot、canonical target 负控分别在登记语义层拒绝；原 R3 未声明正式证据、全局 Resource hash、R6 修正混合环各在原约定层拒绝。独立核对完整 data、Artifact/ref、UNKNOWN/登记历史保留及出错 code/path，不能以更早无关异常视作对应负控通过。确认真实 Artifact/frame 的 book/scope 和 found/declared 闭包独立，资源访问缓存不得替代消费者上下文，不能制造 None-book 消费者。
3. **冻结 API 的直接契约检查。** 核查选择描述的具体类型和全部 pins、显式 asset_root、CURRENT/未知角色与未知版本拒绝；伪造或更改 profile/schema/选择字段不能得到有效 context。检查返回快照不可变、原输入和 model_dump 副本变化不污染已验证对象，Resource path/raw SHA 与实际消费字节一致。只用 R7 已授权的有限角色/pins/版本/快照检查，不扩展为原 P2 变体矩阵。
4. **路径与打包。** 对普通测试临时文件做 R7 约定的相对/绝对/解析后根边界检查；不访问 .local、凭据或 profile。保留作者 Windows 1314 symlink 跳过事实，并核对仅用目录 junction 完成的补证。独立环境如同样无 symlink 权限，可仅使用等价的普通临时目录 junction；记录实际行为、退出和范围，不声称跳过的分支已执行。检查冻结 wheel 原字节 SHA256 `c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7`、分发代码与内置数据和源 pins 一致；在仓库外临时目录清除 PYTHONPATH，解压该 wheel 导入，记录真实 __file__，运行正包及 target 负控两例。不得依赖原仓库 examples/docs/Git 或联网安装。无需重复构建 wheel。
5. **兼容性与过程证据。** diff 证明旧 C01 默认入口和产品文件未改，独立运行原 C01 合同测试入口一轮，结果据实记录。核对作者 freeze-01/prepare-01 预备失败、原始日志与 wheel 空白检查调整均保留，区分预备脚本更正、平台权限跳过和产品语义修复。不得重跑这些失败预备命令。每次实际运行保留脚本/输入摘要、argv/cwd、限时、PID、原 stdout/stderr、退出/timeout/alive；只证明自己启动的进程退出，不做全系统进程扫描。

可编写直接验证本单契约的独立最小检查，不能只调用作者 archive 检查器或照抄其布尔结论。七例、wheel 两例及 C01 兼容范围各一轮；静态检查发现确定缺陷即可给出证据并停止受影响动态项。审阅期间不修产品、不修包、不放宽标准、不新增候选或无限复跑。任何功能缺陷给最短定位、实际影响、必要依赖，冻结为 REWORK；未运行项明确 NOT_RUN。

## 输出与后续依赖

只新增 `docs/evidence/A03/review/P2-R7-readonly-codec/` 和 `docs/tasks/A03-P2-R7-readonly-codec-review-report.md`。保留根工作区他人改动。精确输入索引、独立判断及必要原始输出、进程退出证明和完整新增文件 SHA 清单（只排除清单自身）齐备后冻结交付；避免复制历史全集或重复巨型保全清单。报告给出 ACCEPTED 或 REWORK，但清楚限定为 **R7 只读产品 codec**。最后由调度核对和有限复现后登记，执行者/验收者不自行记 INTEGRATED。

原 A03 P2 持久化与 UNKNOWN 恢复尚未通过，R4 原生 PRE producer、INITIAL/POST_HOLD 生命周期、creation-input anchor、单动作 UNKNOWN→只读对账→迟到回执→新 POST/Batch 真实链路均留给后续确切任务；I01 不因此释放。跨侧合同未共同确认。

禁止运行旧 36 矩阵、旧 A03 main/session/conversion/oracle、DB/native/PRE ABI/planner，禁止网络/浏览器/平台/OCR/模型/付费 API、安装、推送或联系 B/执行者。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。
