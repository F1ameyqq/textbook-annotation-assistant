# A07 修复后源码与验收材料发布回执

2026-10-18 22:05（Asia/Shanghai）。按用户“把修复后的A07和验收材料整理好推送上去”的明确授权，已完成非强制、单引用推送并独立查询远端确认。

- 分支：[codex/a07-q1-handoff](https://github.com/F1ameyqq/textbook-annotation-assistant/tree/codex/a07-q1-handoff)。
- 远端提交：`e37606d74d7e538052c563d02df11c6c961b742f`。
- 内容树：`1790b851c8015ad98aa2e91dd1ac9fea9e60a8af`。
- 唯一父提交：阶段二 `37089f9e0229da76ae1c45461b7e63929590be56`；相对父仅一个发布提交。
- 固定内容来源：本地 `23c9caa57fb3ec602bc3498b02b3819558ab4251`；获验运行产品仍为 `3d22524ff626fc7b0376b7312be6fe75f2e73aab`，发布身份不替代运行身份。
- 交接入口：[修复后的A07](../a07-q1-handoff.md)；[完整可转发消息](../handoff/a07-q1/message-to-b.md)。

## 发布范围与核验

本次275新增路径，仅更新父分支的 README、AGENTS 和追加 .gitattributes 保护规则，0删除；父分支其他路径原字节保持。包含6个A07新源码文件、固定政策/两份授权、历史脚本与测试、215条A07新旧证据、14条任务记录和对应调度证据。旧作者清单中的两条旧源码另存原字节快照，不改旧错误回执，不将旧摘要指向新源码。

[发布清单](../handoff/a07-q1/manifest.json)覆盖270来源成员（268固定源路径及2个历史快照）、7生成成员和清单自身。[发布检查](../evidence/coordinator/a07-publication-20261018/audit.json)确认全源码与固定获验产品一致、公共依赖保持，四份冻结作者/独立清单共230成员闭合，154相对链接有效，未发现禁止路径或常见敏感凭据模式。归档只读脚本核对277个非自指发布成员及230个历史成员通过，见[完整性结果](../evidence/coordinator/a07-publication-20261018/archive-check.json)。

[独立静态复核](../evidence/coordinator/a07-publication-20261018/independent-publication-review.json)通过同一确切树；[依赖复核](../evidence/coordinator/a07-publication-20261018/dependency-review.json)确认40模块保守依赖闭包中新增6个、继承34个，根依赖及公共资源原字节保持。未重新执行A07正常业务、prepare/execute、旧测试矩阵、B生产者或平台操作。本次不新增wheel安装、跨机器业务复现或B联合验收结论。

历史脚本仍绑定旧本机路径和历史Git对象；这些提交不会随选择性单父发布自动可达。当前发布HEAD不可冒充原运行候选，不能改pins或绕过守卫复跑。新文档提供的命令只核验发布完整性。

## 远端结果和边界

[机器回执](../evidence/coordinator/a07-publication-20261018/publication-result.json)记录 push exit0，独立 `ls-remote` 返回相同发布SHA；本次实际推送前后main、B分支、架构分支及阶段一/阶段二分支均未变化。本地工作分支未切换；未强推、未合并main、未覆盖其他分支。

固定Q1当前有效离线结果仍为 Q/W/W/W/W/A，内容/坐标保持，F01已关闭；旧接受记录按历史身份保留。用户此前的“暂不推送”已被本次明确发布请求覆盖；**不连接平台**仍保持。A未向B发送消息，用户可转发已整理消息；远端可用不等于B已经读取或共同采用。B原件HOLD、旧Check、生产题答关系及账本保持，A04真实平台阻断未解除。

本回执和调度状态在本地调度分支记录；已发布内容以远端SHA和该分支清单为准，不为补发回执再制造一次推送。
