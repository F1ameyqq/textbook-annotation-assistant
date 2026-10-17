# A02 portability-R2 独立验收准备

日期：2026-10-17（Asia/Shanghai）。阶段：**WAITING_EXECUTION**。本轮完成一次有界准备，**无正式验收结论**；未执行 R2 实现或任何功能测试。

| 项目 | 固定记录 |
|---|---|
| 工作流提交 | `6b77c436742cf2826083b109d8ed86b85539cba6` |
| 执行基线 | `38aca9dcc8d027409b95193e9cc142c2336b76d3` |
| 执行对话 / 工作树 | `01a144cc-23e9-7c80-9a90-02162ef99b64` / `C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800` |
| 原独立验收对话 | `01a144cc-2eae-7a23-b299-03f533e30951` |
| R2 补丁/最终冻结提交 | 未交付；不以主目录 HEAD 或执行分支名替代 |
| 当前任务 | [portability-R2 派发](A02-portability-R2-dispatch.md)，只修来源身份工具无 Git 环境处理 |
| 既有功能事实 | 原 [A02 R1 ACCEPTED](A02-review-R1-report.md) 及主调度本地集成保留，不回写旧结论 |

已读取主目录 AGENTS、当前调度说明与 A02 状态、R2 任务单、[A01 固定集成 R1 复验失败](A01-integration-R1-review-report.md)、[主调度单例复现回执](../evidence/A01/coordinator/integration-R2-preflight/coordinator-check.json)及确切基线的 `examples/a02/R1/identity.py` / 对应旧单例。仅静态查看已冻结代码，未访问或执行未交付的工作树实现。

当前失败证据表明：固定 raw 集成副本中 PATH 无 Git 时旧 A02 单例退出 1、PATH 有 Git 时退出 0。该失败来自旧 `git_identity` 首次启动 Git 时未捕获 FileNotFoundError；现有基线第二次取 HEAD 同样需要有限负例检查。以上为已读取的冻结证据，不冒称本轮重新实测。

已准备 [14 项独立场景与取证方法](../evidence/A02/review-portability-R2-preparation/scenario-matrix.md)，全部 **NOT_RUN**。核心检查为：

- 真实 Python 子进程、真实无 Git PATH、无 `.git` 原字节副本，记录 `which('git')=null` 与实际 OS 无法启动证据，要求 `git_identity` 返回明确 UNKNOWN/null。
- 正常有 Git checkout 先核 toplevel 再取真实 HEAD；嵌套 raw 导出不借父 HEAD。
- `source_binding` 在缺 Git/无效仓库/源码字节不符时失败关闭；有 Git 且外部仓库合法时仍逐 blob 成功绑定，导出 checkout 身份保持 null。
- 第一次真实 Git 成功后令第二次启动缺失，核对 UNKNOWN；模拟异常单元负例另记，不能替代真实无 Git 实测。
- 只复现原失败单例和受影响 A02 测试，保全旧输入/报告/失败日志；不运行未改 C01、登录、630 几何矩阵或完整 A01 入口。

冻结交付到达后先核对补丁/最终 commit、报告、清单、范围和必要 raw 字节，正式输出只用 `docs/tasks/A02-portability-R2-review-report.md` 与 `docs/evidence/A02/review-portability-R2/`。唯一可改既有文件应为 `examples/a02/R1/identity.py`；新增白名单以任务单为准。A01 来源/geometry、原固定验收资料及任何旧证据不改，验收者不代作者修复。

本轮只写本准备记录与 `docs/evidence/A02/review-portability-R2-preparation/`。实际读操作、来源摘要、调度观测和文档检查见 [preparation-observation.json](../evidence/A02/review-portability-R2-preparation/preparation-observation.json)、[preparation-validation.json](../evidence/A02/review-portability-R2-preparation/preparation-validation.json)，统一摘要见 [sha256-manifest.json](../evidence/A02/review-portability-R2-preparation/sha256-manifest.json)。准备检查仅验证文档/记录，不等于功能检查。

本轮不轮询、不向执行者/B或其他 Codex 对话发消息、不修改状态或代码，不做网络、平台、浏览器、凭据/profile、OCR或外部模型调用。完成后结束等待主调度另发确切冻结交付；R2 独立通过也不自动释放 A01/A04/D01，后续固定集成入口由原 A01 验收对话另审。
