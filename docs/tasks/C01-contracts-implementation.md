# C01 合同实现与固定样例

类型：A 侧离线开发，执行和独立验收各用一个新对话。源任务见 coordination 的 C01，架构语义见 `docs/architecture.md` 与 `docs/contracts-v1.md`。

## 目标与范围

把设计中的 SourceBundle、EvidenceBundle、QuestionGraph、CheckReport、ApplyPlan、ExecutionReceipt、ReviewPatch、BatchReport 及 PlatformSnapshot 变成可导入、可校验的单一权威 Python 类型与 JSON 交换格式。提供一个最小命令行验证入口、完整固定样例、可跨目录运行的消费者示例和具体错误位置。该实现是 A 内部可用的 v1 提案，不能标成 B 已确认或共同冻结。

本任务不启动平台浏览器、不读取登录文件、不调用付费模型、不运行 A05 写入脚本。不要实现 recognition/assembly 算法、真正平台 executor、runtime 恢复或复杂工作台；这些有独立后续任务。工作目录由主调度派单给出，使用隔离 Git worktree，分支使用 `codex/` 前缀，精确 base_commit/workflow_commit 写入交付报告。

允许修改：`src/annotation/contracts/`、最小包入口、`tests/fixtures/contracts/`、`tests/test_contracts*.py`、`examples/contracts/`、`config/policies/`、必要的根依赖/打包配置、`docs/contracts-implementation-v1.md`、`docs/tasks/C01-execution-report.md`。根依赖和公共类型本阶段由你唯一写入。原始研究工具、旧证据、AGENTS、coordination-state 与 B 模块不改。

## 必须落实的语义

- 统一信封与版本/依赖引用；确定并解释可重复的摘要规则，避免 content_hash 自指，拒绝被改动的输入引用或版本冲突。
- 内部题目和片段身份独立于平台题序，原图框绑定 asset、尺寸和摘要；检查有限数值、正面积、边界及可定位引用错误。
- 资源路径使用可移植相对路径，不把账号、本机绝对路径或平台登录状态塞进业务产物。
- 通用角色与 Q/W/A/E 平台映射分离。选择题 W 独立/合并政策仍标 unresolved，不擅自选规则作为业务定论；框保存已验收与 OCR 未验收分别记录。
- CheckReport 必须有依据、输入版本、范围和决策，不能用一个浮点置信度代替通过标准。计划引用内容与目标两份 PASS 且绑定正确版本；缺少或不一致不能校验成可执行。
- 回执 APPLIED / NOT_APPLIED / UNKNOWN 不混用；UNKNOWN、CONTENT_PENDING、NOT_SUBMITTED 不能通过非法状态组合进入 COMPLETED 或可直接重放。
- Patch 绑定基线，不覆盖旧修订；批次报告保留异常/跳过的分母及提交/内容两个独立状态。
- 需要补充设计未明确的字段时，记录为具体实现提案和待共同确认项，不冒充既有双方决议。当前 Python 3.9.13 环境须可运行；不要要求用户升级才能读固定样例。

## 样例与验收

提供正常、EXCEPTION、UNKNOWN 三组完整串联产物和必要的小型资源，明确 synthetic/真实来源及预期结果。消费者只通过公共 contracts API 使用产物，不读取其他模块私有结构。样例引用相互闭合、可复制到不同目录后验证；同一个文档定义应自动生成或验证 JSON Schema，若提供 schema 则避免手写双份权威。

有意义的失败测试至少覆盖：缺失实体/资产引用、越界/NaN/无穷 bbox、版本或摘要冲突、只有一份 PASS 的计划、目标版本变化、UNKNOWN 被伪装成成功/可重试、未提交或内容待验证却标为完成、patch 基线错误、绝对路径或路径逃逸。测试不要只是逐字段复制实现。

交付最短安装/运行步骤、实际测试输出、正常和失败的可复现命令、依赖取舍、B 消费接口说明和待确认语义。产物构造不算实际平台或算法成绩。

## 结束与交接

在隔离分支提交仅本任务文件，写 `docs/tasks/C01-execution-report.md`，给出精确提交、工作目录、命令、样例版本、实际通过/失败项和限制。交付后停止修改被验工作树，转 REVIEW，等待独立验收；不能自行宣布 ACCEPTED 或推送到远端。主调度负责整合和后续派发，B 侧独立决定采用与反馈。
