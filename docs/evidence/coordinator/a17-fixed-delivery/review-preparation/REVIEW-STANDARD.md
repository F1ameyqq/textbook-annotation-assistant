# A17 独立验收准备标准

阶段：PREPARATION_ONLY / WAITING_EXECUTION。本文件是待执行的验收标准，不是产品审查结果；全部控制当前 NOT_RUN。

本正式独立对话 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4` 与作者 `01a158fd-281c-7282-a3b4-db876697686c` 分离。workflow `811c3ac9e5913812bc71d74bc665eded96e23aa3`，产品基线 `003f862065a2d630e666323c0d158e33bcee91e9`，新 scope `CURRENT_BOOK_SOURCE_INVENTORY_EXCLUDED_STATIC_OBSERVATION_ONLY`。推理设置按派发为 xhigh、model 沿用，不另改设置。

标准来源为 `D:/1800/docs/tasks/A17-independent-excluded-static-review.md`（SHA256 `7cfe7f469d9f9d4bf6e9d6c3c49062ffb308e4238e29eb9309b03931c160106d`）及 `D:/1800/docs/tasks/A17-excluded-static-readonly-adaptation.md`（SHA256 `6a09a30a9b8464ed212e282a47ac196ba01fa26b2a44067d6e7b118599fc0091`）。两份任务已完整阅读并与派发摘要核对。已读取 AGENTS、coordination、development-plan 及调度 JSON；旧段落与新固定 JSON 冲突时按本轮任务、JSON、固定报告及 Git 取证。

## 进入正式复核的前置条件

调度必须提供作者确切 product/final commit、候选及完整依赖清单（包括包初始化文件）、原始运行结果和必要失败、REPORT、每成员字节数/SHA256 的 raw 清单、精确释放说明，并完成交付核证。随后另给新的 raw 隔离路径和本独立可写输出白名单。未齐备前保持 WAITING_EXECUTION，不自行搜索作者产物，不访问 `D:/1800-worktrees/a17-static-exclusion`。

正式复核先确认 raw 字节与固定 Git blob、mode/type/blob 及依赖闭包，再读源、import 或运行本轮相关 fake 控制。每条 Git 命令均先设置 `GIT_NO_LAZY_FETCH=1` 并带 `-c core.longpaths=true`；不 lazy fetch、不 reset/clean/stash、不全量 add、不推送。现有根工作区有未提交状态，不以工作树干净为前提，不修复或覆盖他人改动。

产品允许改动：`src/annotation/source/usense/current_readonly/gate.py`、`policy.py`；`tools/a16_current_state_probe.py`、`tools/a16_current_state_launcher.py`；确有需要的小型 `tools/a17_*.py`；新测试仅 `tests/a17_excluded_static/`；新候选/计划/报告/完整 raw/必要失败仅 `docs/evidence/A17/`。不允许新增另一套业务执行系统、改根依赖/公共合同或改写冻结 A16 native 参考副本。

## 待执行控制矩阵

每行是必要证据组，按固定产品实际 API 形成最小具体子例；本准备文件不规定作者内部 API，也未编写或运行产品测试代码。不能以作者通过数量替代独立控制。所有组当前 NOT_RUN。

| ID | 待核场景 | 通过判据与应留原始证据 |
|---|---|---|
| I01 | 固定交付、范围与闭包 | product/final/base/workflow、候选 SHA、scope 一致；raw 成员 bytes/SHA 与 blob 一致；包初始化依赖完整；改动在白名单。不能把 checkout CRLF/LF 差异当原 blob 被改写，也不能任意归一化所有证据。 |
| I02 | 历史保全 | 逐项核旧树 mode/type/blob、旧失败/报告/原运行标记和冻结 A16 native 参考文件；原 suite 不重跑。历史未改代码只准确引用此前有限证明，不把旧通过覆盖新代码。 |
| P01 | 已观察形态的分类 | 合成普通路径的有效 HTTPS、精确 `cdn.bootcdn.net`、有效端口443、GET、Script、非 redirect，且原页面/主框身份可信时，才可得到 `EXPECTED_EXCLUDED_STATIC_DENIAL`；实际 CDN 路径与必要性仍 UNKNOWN。 |
| P02 | 相邻来源/URL 结构 | HTTP、其他有效端口、子域/后缀/拼写诱饵、userinfo、fragment/control、畸形 URL 均不能获新排除继续资格。解析方案对精确主机、HTTPS 默认/显式443的处理需明确，不借规范化扩大来源。 |
| P03 | 方法/资源/路径优先级 | 非 GET、非 Script、Document/主导航、WS、redirect、API/login/sample 等始终走对应硬停止；一维变体及高优先级危险形态不能被新类别遮盖。 |
| P04 | 类别不可伪造 | 对未知域、身份缺失/不匹配、危险方法等传入伪造类别/自称预期拒绝，不能绕过完整受控请求字段推导。 |
| L01 | native-first / native-only | fake native fail 真正完成；无 continue/fulfill/body/evaluate/download/替代脚本；即便 context 永不到达也证明原页面/主框。 |
| L02 | context-first / context-only | fake context abort 真正完成；两层均不发送该 HTTP 请求；与 native 共享同一状态。 |
| L03 | 双层重复及身份负例 | 同一请求双层事件计两次；child、错误主框/页面、缺失或 UNKNOWN 身份在任一层均 fatal，native 不等 context 补判。 |
| L04 | 禁止出现排除脚本 response | 回调一旦看见该脚本 response，即记录排除边界未证明并停止，body 读取数为0，不能仍宣称零 HTTP 发送已证。 |
| Q01 | 共享16次边界 | 1至16事件分别完成拒绝且不因该类别停止；第17仍调用拒绝并硬停止。双层交错/重复均计入同一全轮总额，无每层16或每 URL16。 |
| Q02 | await 前扣额/竞争 | 用内存事件阻塞拒绝完成，交错触发两层；在首个 await 前已保守扣额，无竞争超额继续。纯 policy/capture/get_once 查询不扣此事件额，也不恢复额度。 |
| Q03 | 数量口径 | 报告区分守卫排除事件、不同请求/URL 和实际 HTTP 发送；未证发送总数为 UNKNOWN，不声称 DNS/TCP/TLS 活动为零。 |
| A01 | 拒绝失败/异常/未完成 | native fail 或 context abort 抛错、返回失败或悬挂，均进入最终 ERROR/UNKNOWN 并停止后继，不能凭预期类别吞错或记成功。 |
| A02 | 关闭与结清晚到 fatal | collect/导航后、关闭期间、回调结清期间或结果初拟后到达的真实 fatal，必须反映在最终失败/UNKNOWN；首错不被预期排除/后续关闭错误覆盖。 |
| A03 | 有界结清/未完成回调 | 两层所有在途回调有明确结清边界；悬挂/取消/未结清不等于成功，无无限等待，不延长原截止；结清超时后不能继续产生被认可的后继效果。 |
| C01 | 合成后继正例 | 仅在排除拒绝成功且导航、登录态、当前书身份、六业务读取和两原图全部所需事实真实满足时，fake collect 才完成其有限事实记录。该正例仅内存模拟。 |
| C02 | 导航/认证/书身份失败 | 分别注入导航失败、LOGIN_REQUIRED、目标书非46007447、源/目标身份或映射不符；首个失败后后继 NOT_RUN，无重试/刷新/第二导航。 |
| C03 | 六读取/两原图任一缺失 | 按固定清单逐一验证每个必需响应或原图/尺寸/摘要/解码/映射缺失或失败，不能因前面的预期排除而继续给出成功库存。固定清单由正式 raw 中的权威规则核出，不在准备时猜造端点。 |
| C04 | sample0/无资格提升 | 五个样题 GET 保持拒绝；伪配置/伪证据不能开启样题、自动schema资格或写入；内容/schema UNKNOWN，样题 NOT_RUN，production_ready/write_eligible=false，旧R02仍REWORK且能力停用。 |
| B01 | 原白名单/次数边界 | 六固定业务 GET 各一次、两绑定原图各一次、原同源session/static范围保持。无新增CDN下载、HTTP探针/客户端/source-discovery、刷新、第二导航、登录提交或业务写入。 |
| B02 | A17 全链绑定 | task/scope/workflow、候选及依赖、stage/run_id、decision/report、activation路径与输出一次性标记相互绑定；run_id绑定本轮正式执行ID。旧A15/A16决定、报告、scope、候选、activation或已耗标记不能匹配。 |
| B03 | 默认拒绝的未来模板 | 只能形成未获准的计划/门禁/模板，不生成批准决定；本次不得创建或激活 `.local/stages/a17-excluded-static-live` 或 `a17-excluded-static-activation.json`，不读原profile；未来适用TLS决定待调度另固定。 |
| R01 | 结果与释放真实口径 | 排除拒绝、实际完成后继、NOT_RUN/UNKNOWN及证据不足分别记录；所有本轮真实资源未获取时写未持有，不冒称证实launcher OS创建身份；不把离线通过写成认证/取数/写入/集成/live批准。 |

## 正式复核方法与结论

测试只使用合成请求/响应、纯内存 fake transport、可控制的异步任务/事件；禁止真实 native/browser/网络/profile/凭据/占用扫描、产品子进程及旧 suite。正式复核只写调度指定新 raw 隔离中的独立输出目录，输入原 bytes 保持；本准备目录不是已获准的正式运行目录。

先静态复核冻结调用链与守卫优先级，再运行作者新相关 suite（仅当已确认纯内存且正式调度允许）及独立必要控制。保留命令、退出码、原 stdout/stderr、逐项断言与未执行原因。若冻结产品有语义反例或范围/依赖缺口，保存最小固定证据并给出 REWORK 后释放；不自行改产品或修后重跑。由调度在同一 A17 明确修订和新冻结；新聊天不恢复旧额度。

完整独立 REPORT、机器结果、逐项实际控制记录、字节数/SHA清单和释放说明齐备后才给有限结论。允许接受的最高层仅本轮相关离线实现/控制；当前认证、当前书库存、正文/schema、真实首题保存及刷新重开读回均未证明。A16失败与已耗live1/余0、辅助发送总数UNKNOWN、launcher OS创建身份UNKNOWN保持；其他三例HOLD、Q22不重放、0B/外部联系人消息，无书级送交。

当前结论：WAITING_EXECUTION，正式产品复核 NOT_RUN。已完成标准准备，释放等待调度固定交付。
