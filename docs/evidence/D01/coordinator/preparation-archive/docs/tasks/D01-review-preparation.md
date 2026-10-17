# D01 独立验收准备

2026-10-17（Asia/Shanghai）。状态：**PREPARED / WAITING_EXECUTION**。本轮是一次静态准备，全部功能项 **NOT_RUN**，不产生 D01 的 ACCEPTED、REWORK 或集成结论。派发要求为 `xhigh`；未另派子智能体。

## 固定输入与授权边界

| 身份 | 固定值 |
|---|---|
| workflow | `f15f7bc03fac8994ade1642fa7547cbd823c6d43` |
| workflow tree | `050165b1f1b00ab1a5a4a6ae3a357157c18ec482` |
| 产品 base：已实际集成 A01 | `c6bebdf43eb93f7a6ae21e96ec07ed155686777d` |
| 产品 base tree | `e6f8d89bceccd639d9d8cf4e5fd2766899dff59b` |
| 执行对话（仅身份，未读取/联系） | `01a14831-6b32-7372-9d9c-b5dd46d3d4c2` |
| 正式实现 / 冻结交付 / 执行报告 / 清单 / 会话释放 | **尚未接收主调度正式目标**；均不从浮动分支或未来作者日志推断 |
| 本准备独立目录 | `C:/Users/ASUS/.codex/worktrees/d01-review-preparation/1800` |

从 workflow Git 对象读取 AGENTS、架构、合同、协调约定、[执行任务](D01-dependency-implementation.md)、[独立验收任务](D01-independent-review.md)、依赖准备单，以及 A01 R3 接受、integration-R2 独立接受与[实际集成收口](A01-integration-R2-coordinator-acceptance.md)。只从产品 base 读取根依赖、公开 consumer、既有来源实现/相关测试与两书 R3 文件身份；没有读取 D01 浮动实现或执行对话内容。

旧记忆中 A01 R3 尚无最终结论的记录已被上述固定 Git 文档更新。本轮引用的是这些固定接受材料，未重新运行 A01；历史记录使用既有 Pillow，不能充当 D01 的新环境安装证据。旧失败、LF/CRLF 表示限制、I04 标签限制及文件 symlink 权限跳过仍保留。

[输入清单](../evidence/D01/review/preparation/input-index.json)记录 **47 项**输入的 commit、blob OID、原 Git 字节 SHA256 和长度。其中 18 份静态文档/代码原件保存在 `preparation/inputs/`，两书 R3 的 **29 份文件只建身份索引，未物化、消费或解码**。输入清单 SHA256：`0ec3377b293c6ded8a7d339877e3842df5bd132e7a9a67d2dacde33f07b733e7`。字节通过原生 stdout 字节流取得，不以文本重定向或换行归一化冒充 Git 原件。[源码树索引](../evidence/D01/review/preparation/base-source-tree.txt)仅作为后续静态保全参照。

## 正式复验启动门

以下材料须由主调度一次明确绑定后才启动功能工作；本轮全部留空，不自行查询执行者进度：

1. 确切实现提交、冻结交付提交/树及产品 base；明确冻结提交包含哪些执行报告和辅助文件。
2. 固定执行报告、输入/脚本/输出 SHA 清单及它们的摘要；失败记录也须可取得，不能只给成功计数。
3. 执行者自有同步进程全部返回、会话已释放的证据。此任务不需要浏览器/profile，释放证据不能据此省略；不借用其他任务会话。
4. 主调度正式唤醒及此次独立复验允许的输入/输出范围。若其中有未知或不一致，先记录具体缺项，不以分支名或作者未来日志替代。

正式报告为 `docs/tasks/D01-review-report.md`，正式证据另建 `docs/evidence/D01/review/` 下的新目录。本准备目录保持原字节，不覆盖为运行结果。当前不存在被验目标，因此不宣称产品失败或接受。

## 条款 → 独立验证 → 必要证据

下表与[机器清单](../evidence/D01/review/preparation/verification-matrix.json)对应。表内方法和证据路径是正式唤醒后的计划，**本轮均未执行**；不能以准备脚本成功或既有作者结果填充。

| ID / 任务条款 | 正式独立验证方法 | 必要证据 | 本轮 |
|---|---|---|---|
| G01 / 固定交付与释放门 | 主调度目标逐项核对 commit、tree、报告/清单 SHA、释放证据和允许范围；记录依赖基线 | `handoff/target.json`、固定原件、输入索引 | NOT_RUN |
| S01 / 唯一产品差异 | 比较产品 base 与冻结交付：根默认 dependencies 仅增加 `Pillow==11.3.0`；Python `>=3.9`、Pydantic pin、包名、版本、其余配置/源码保留；辅助文件限执行任务指定目录。继承的 workflow 文档单列来源，不混作产品改动 | 完整差异、逐文件 OID/摘要、根配置前后原件、范围核对 | NOT_RUN |
| S02 / 独立源码与旧材料保全 | 从固定 blob 构造新源码副本；导出后验证 OID/长度/SHA256；旧实现、配置、样例与历史证据逐项按基线核对。记录实际文件表示，不扩大旧 CRLF 容差 | `snapshot/` 索引、范围/保全报告、运行前后摘要 | NOT_RUN |
| E01 / CPython 3.9 新 venv | 在不存在的独占路径新建 venv；记录解释器真实路径/版本、`pyvenv.cfg`、prefix/base_prefix、site 路径；禁止 system-site-packages、宿主 PYTHONPATH 和用户包满足依赖 | 新路径不存在的前置记录、创建 argv/cwd/回执、配置、环境探针 | NOT_RUN |
| E02 / 非 editable 构建安装 | 用自有环境 `python -I -m pip` 从固定副本构建 wheel，记录实际 wheel SHA；再安装该 wheel。只在独占环境安装必需公开依赖；检查 pip 是否支持安装报告，缺能力则记录并按任务范围处理，不用日志猜来源 | 源 commit/tree → 构建 argv/原始输出 → wheel SHA/文件 → 安装报告的完整关联 | NOT_RUN |
| E03 / 安装来源关联 | 核对安装报告中的本地 wheel 来源和 archive SHA、wheel 内元数据/代码摘要、安装 METADATA/RECORD、存在时的 direct_url.json；实际导入文件与 wheel 对应代码字节一致。缺失 direct_url 如实标记，不单凭版本/路径认证源码 | wheel 索引、安装报告、分发元数据、逐模块安装字节关联 | NOT_RUN |
| E04 / 公开依赖来源 | 保存实际公开来源、解析版本和各下载/缓存制品 SHA；包括所需构建工具。脱敏但保留足够的无凭据来源身份；允许正常缓存 | 依赖制品清单、相关安装/构建原始回执；不转储全局 pip 配置或秘密 | NOT_RUN |
| E05 / pip check 与依赖声明 | 自有环境 `python -I -m pip check` 实际退出 0；已安装 annotation-contracts 的 Requires-Dist 包含 Pillow 指定版本；记录真实安装版本，不将单一 pin 称为全锁定 | 完整 argv/cwd/退出码/stdout/stderr、METADATA、已安装版本清单 | NOT_RUN |
| E06 / 仓库外隔离导入 | 在仓库、源码和包目录之外的 cwd 以 `-I` 导入 contracts、source.static、geometry、PIL；记录实际 `__file__`、sys.path 和安装分发归属，均定位自有 venv，不能插入源码或借宿主 PIL | 独立探针、实际导入路径/摘要、解释器/环境、原始回执 | NOT_RUN |
| C01 / 冻结两书样例与 consumer | 将正式基线 consumer 及 R3 两包逐文件绑定 Git blob/SHA；与本准备产品 base 索引比较。复制到另一含空格的独占目录，复制前后保持字节 | consumer/29份包文件的原件索引、源/目标/运行后哈希、实际复制路径 | NOT_RUN |
| C02 / 安装后搬运消费 | 在仓库外、区别于搬运包位置的 cwd，以 `-I` 调用冻结 consumer；公开资源检查及来源完整解码均完成。实际 annotation/PIL 来自自有安装分发；若用观察器须记录包装 argv，保持 consumer 原字节且不注入源码路径 | 两次实际消费原始回执、实际导入、输出、8个原图尺寸/摘要/解码结果 | NOT_RUN |
| C03 / 有限来源边界 | 旧书 6 资源 / metadata 250 / 14参考；新书 2 / 214 / 1参考。分别核对书 ID、REFERENCE_ONLY、coverage_eligible=false、独立分母 UNKNOWN；不把元数据页数当取得数 | 两包输出、limitations/来源字段断言、书籍分列记录 | NOT_RUN |
| N01 / 坏资源拒绝 | 各建受控新副本做缺失资源与摘要损坏，记录唯一变更和预期可定位拒绝；保留原始非零消费者回执。预期失败由外层分类，不改写为消费者成功 | 突变清单/前后 SHA、异常 code/location 或明确路径、原始 stdout/stderr/退出码 | NOT_RUN |
| N02 / 完整解码而非仅哈希 | 对新副本做摘要已更新的截断图像，明确先通过相关资源摘要层，再由安装代码拒绝 IMAGE_DECODE；可用固定 A01 来源测试的既有该方法并记录实际导入，或独立有界探针。若停在更早层，单列该层而不声称已证明解码拒绝 | 突变与重封引用记录、前置资源校验、真实解码错误；不修改冻结原件 | NOT_RUN |
| R01 / 最小相关回归 | 从固定源码运行相关合同/来源检查，记录计数、失败、skip 与实际导入；关注资源缺失、摘要损坏、正确新摘要截断图像及两书区分。包含自设 PYTHONPATH 的测试子进程单列为源码回归，由 E06/C02 补足隔离安装证明 | 确切测试/夹具版本、命令、原始结果、实际导入归属、安装证明与源码测试的分层表 | NOT_RUN |
| F01 / 证据闭包与退出 | 统一清单包含报告、脚本、输入/输出及所有原始日志（包括被忽略日志），明确排除自身；核对链接/摘要、固定输入运行后不变、自有同步进程返回且无待释放自有会话 | SHA清单、文档/范围审计、进程回执/任务路径核对、正式结果和限制 | NOT_RUN |

## 复验方法的静态风险记录

产品 base 的公开 `examples/a01/consume.py` 没有源码路径注入，依次调用公共 `load_bundle(..., verify_assets=True)` 和 `load_static_bundle(...)`。来源实现的 `decode_image` 执行 `verify()` 后重新打开并 `load()`；这些是静态源码事实，尚不是本轮实际安装/解码结果。consumer 的 `full_image_decode="OK"` 文本单独不足以证明安装出处，须结合固定源码字节、真实调用回执与 E03/E06。

`tests/test_contracts.py` 部分子进程会主动设置 `PYTHONPATH=ROOT/src`。正式复验应记录这些实际导入，不把全套测试退出 0 泛称为全套安装包测试。可在 `-I` 下由 unittest discovery 只加入测试目录，父进程使用安装分发；子进程中的源码注入须单列，不能改现有测试制造“隔离通过”。

本轮不预写功能成功日志、不创建 venv、不探测/安装宿主 PIL、不构建 wheel、不运行 consumer 或测试。正式命令须在目标冻结后落盘，至少包含：新 venv 创建、环境内 `python -I -m pip wheel/install/check`、仓库外 `python -I` 导入、两书搬运消费和坏资源拒绝。每条保存 argv、cwd、解释器、选定无秘密环境、退出码及原始 stdout/stderr；不能用未来作者日志补齐。

## 本次已做与结束条件

实际仅做固定 Git 对象读取、原字节摘要/文档快照、验收矩阵与文档链接/差异核对。[静态采集脚本](../evidence/D01/review/preparation/capture-static.ps1)及[99条同步 Git 回执](../evidence/D01/review/preparation/static-git-commands.json)可审计；这些退出 0 仅说明静态读取完成，不是功能成绩。[静态文档收口](../evidence/D01/review/preparation/static-closeout.json)及[准备文件 SHA 清单](../evidence/D01/review/preparation/sha256-manifest.json)单独记录最终归档。

本验收只新增本报告与 `docs/evidence/D01/review/preparation/`，未改产品代码、根依赖、调度 state 或其他旧证据。未安装/测试、未读取浮动实现、未轮询或联系执行者；平台/浏览器/凭据/付费模型/B访问均为 0。未提交、合并或推送。自有静态同步命令均已返回，无启动的后台执行会话。

完成此次准备后结束，等待主调度正式唤醒。D01 仍未验收、未集成；主调度独立复现并集成后才能关闭。S01、B 确认、平台、识别质量、成本和部署全流程继续保持各自边界；未来成功最多证明明确记录的 CPython 3.9 环境。
