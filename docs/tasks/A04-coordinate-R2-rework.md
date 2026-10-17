# A04 coordinate-R2：完整原图解码与状态修订

2026-10-17，Asia/Shanghai。继续原执行对话，明确 `xhigh`；原目录/分支为 `C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800` / `codex/a04-headless-readonly`。基线是冻结交付 `a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39`，不合入浮动主目录。A01 geometry依赖保持已接受的精确版本。

[独立复验](A04-coordinate-R1-review-report.md)为REWORK，主调度已核对227份归档并独立[复现](../evidence/A04/coordinator/coordinate-R1-review/fresh-repro/result.json)：24字节截断PNG被公开offline入口发布，公共loader接受，pages_acquired=3，而完整解码拒绝。

本轮仅做一次有界离线修复：

1. 在 `src/annotation/source/usense/` 的公共来源入口检查完整图像可解码，格式/尺寸/摘要绑定保持。拒绝时使用可定位且脱敏的资源错误，不发布可被当作完整有效来源的最终包。覆盖截断PNG、至少一个具有有效头部但损坏像素的受支持格式、正常PNG/JPEG及原有拒绝行为。
2. 同一局部CLI内消除已过期的 `WAITING_ACCEPTED_COMMIT` 声明，明确“依赖已接受”与“这个离线包未做实际坐标验证”。禁止把字符串修正当作真实坐标PASS。
3. 原R1、旧失败和独立证据一律不改。新增 `tests/test_a04*` 的对应回归、新 `docs/evidence/A04/execution/coordinate-R2/`、`docs/tasks/A04-coordinate-R2-execution-report.md`；确需示例仅在 `examples/a04/coordinate-R2/` 新增。根依赖、公共合同、source/static、geometry、其他任务目录禁止改动。Pillow已存在于独立测试环境；根依赖由主调度D01处理，不由本轮合并。

验收要求：原最小反例在公开入口被拒绝且不产出有效最终包；完整解码层与纯摘要层分开证明；正常原图/可搬运包和既有A04离线回归保持；状态声明真实。给出确切实现/交付提交、复现命令、输入输出、失败记录、全证据清单和自有进程释放。

**本轮禁止真实平台/登录/profile/浏览器/网络/模型动作。** 不重试此前5次GET超时；真实平台六项仍BLOCKED，修好离线缺陷也不接受整个A04。不改调度state，不推送，不向B或验收者发消息。交付停在REVIEW，等待原独立验收对话由主调度续派。
