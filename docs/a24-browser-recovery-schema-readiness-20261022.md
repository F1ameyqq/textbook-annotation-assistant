# 浏览器只读恢复与A24格式接入加固

日期：2026-10-22，Asia/Shanghai。B输入 `2e43bcb58b02b7bab9b95b87671403cd259be1ab`；A24原固定提交 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`。用户授权继续排查连接、恢复后只读取46007447；不授予修改标注、保存或提交权限。

## 当前连接事实

来源成员重新检查Edge“用户配置1”的受支持浏览器库存：原独立标签1199071973已不存在。旧主页1199071786属于其他会话，未接管；两个登录页也未使用。

本轮只新建一个同配置的独立标签 **1199071977**，会话名“📖 A24只读恢复”。创建调用超时，但随后库存确认该标签存在，标题为“数据标注平台”，URL停留 `https://www.usense.com/qieti/home`。这支持登录状态可能被普通导航沿用；尚未通过DOM核实账号、46007447或API权限，不能把主页URL当成当前业务身份。

唯一一次标签绑定在30秒后超时并重置运行环境，没有取得DOM或业务响应。四个业务GET均NOT_RUN；新业务原件0，标注写入/保存/提交0。没有再次新开标签、重登、接管旧标签、读取Cookie/token、修改profile/权限/扩展、重启浏览器，亦未用native、shell HTTP或CDP绕过此前停止规则。

[官方扩展排障说明](https://learn.chatgpt.com/docs/chrome-extension#troubleshooting)建议检查扩展侧边栏、同一浏览器配置和连接状态。本轮已让用户仅确认现有标签的ChatGPT扩展侧边栏是否能加载；截至本记录尚未回复，没有把等待当作连接恢复。无需再次登录或查看导出入口。后续只在出现新的受支持连接状态后绑定此现有标签，成功读取实际host/账号/书籍身份后再做限定只读采集。

来源库存及单标签恢复的原始报告位于[本轮证据](evidence/a24-schema-readiness-20261022/browser-new-tab.json)。

## 已独立完成的代码增量

质量成员复现了空分母、自洽空ID/正文、未投影extra变化、身份多对一映射四类风险；[原审计](evidence/a24-schema-readiness-20261022/initial-preservation-audit.md)保持。原schema未绑定入口仍会阻断写入，这不是已经发生线上写入的报告。

本轮修订固定补丁为[readiness-v2](../handoffs/b/a24/a24-schema-readiness-v2-20261022.patch)，28,904字节，SHA-256：

```text
c0b36d24cdd8c29ad1f02c4194cd445c1dda26b3300921c9b3f0589607d63f7c
```

四文件差量在独立新工作区实际应用，与作者和独立复核的LF字节摘要完全一致：

- `quality/live_pilot.py`拒绝总体questions/frames/question_content空清单及无效题、框、目录ID；保留已有重复与引用约束。**允许单个旧题没有框**，不猜真实平台的逐题框规则。
- `delivery/live_pilot/wire.py`收紧两种export codec的规范ID、重复rect ID和parts对象骨架；多响应profile中的book直接取源，已知身份字段及其容器禁止literal/lookup合成。容器直接复制和非身份题型等lookup保持合法。实际完整内容仍未由骨架校验证明。
- `runtime/live_pilot/schema_capture.py`接收明确UNBOUND的四槽记录，检查顺序、固定路由、私有文件长度/摘要和UTF-8表示，返回仍不可写的字节集合；不猜字段、不创建profile/qualification、不生成权威metadata。
- 新增14项聚焦回归。

这份补丁交付的是临时接管变体，未覆盖原A发布、[旧固定离线ZIP](a24-offline-replay-20261022.md)、B内容包、图谱、账本或公共合同。隔离最终源码目录为 `../a24-takeover-20261022/source-readiness-v2/`，有效文件525项；旧固定树523项另存不动。最终四文件原字节也随[机器记录](../evaluation/a24-browser-recovery-schema-readiness-20261022.json)归档，可独立核查。

## 从旧固定ZIP应用补丁

先按旧交付说明核对ZIP并重建一个全新的523文件有效树；再在该树根目录运行：

```powershell
git -c core.autocrlf=false apply --check --whitespace=error-all C:\path\to\a24-schema-readiness-v2-20261022.patch
git -c core.autocrlf=false apply --whitespace=error-all C:\path\to\a24-schema-readiness-v2-20261022.patch
```

显式关闭此次apply的自动换行转换，不修改全局Git配置。主审和独立成员曾复现普通apply退出0却写出CRLF，四个SHA不等于作者LF；原始变体和拒绝事实已保存。实际最终运行的是与固定摘要逐字节相同的LF文件，不把规范化SHA冒充实际运行字节。

不要把补丁应用到已修改树、旧A运行目录或旧activation。实际线上依赖和配置未来仍须重新冻结；本轮未运行live启动器。

## 回归事实与首版撤回

首版补丁 `981c4569…`误加“每题必须有框”集合等式：35项小组通过，但旧R1出现6个新增FAIL和3个ERROR。主审在原523固定树实际运行同组得到17 PASS、0 FAIL、3 ERROR，证实6个FAIL是新回归。已撤回该业务假设并以原R1期望复验；没有改旧测试期望让补丁通过。首版、原失败、祖先容器旁路证据和基线对照全部留存。

|最终实际检查|结果|证据边界|
|---|---|---|
|主审新增14 + controlled-capture 7 + current-body 10 + book-snapshot 4|35/35 PASS|实际最终LF变体|
|主审旧R1二十项|17 PASS、0 FAIL、3 ERROR|与原固定树相同，不是全绿|
|主审合计|52 PASS、0 FAIL、3 ERROR，命令退出1|原始退出码/traceback不改写|
|质量成员独立复验|新增14、独立入口/codec 9、受影响R1 6，共29/29 PASS|未代报完整R1，也不是独立人工验收|

R1三个既有ERROR分别是旧WindowsBackend夹具缺bootstrap_steps、旧reopen夹具缺外层证书、`D:/1800`私有请求文件缺失。本轮未修旧夹具或补造私有文件；比较的是相同错误测试集合、零新增FAIL。详见[原始主审回归](evidence/a24-schema-readiness-20261022/main-final-regression.json)、[兼容差量](evidence/a24-schema-readiness-20261022/main-compatibility-delta.json)和[独立最终复审](evidence/a24-schema-readiness-20261022/independent-final-report.md)。有限Python入口防护不是OS全IO沙箱。

## 恢复后真正还要完成的工作

1. 保存本次四响应的私有正文、SHA/长度/时序和表示方式；从实际响应核实书号和字段，不能沿用旧四GET摘要或从候选数推分母。
2. 独立证明目录、题和框的当前完整成员范围及分页/状态。非空门只防零分母，不能防非空但缩减的清单。
3. 对question/frame/directory保留完整原始记录的可信摘要，纳入保存前后比较，覆盖未映射extra字段；以显式新profile版本提出，不静默升级旧格式。
4. 将同次snapshot与export的state/version、source_refs/evidence_refs和实际受控字节绑定。两种codec仍接受`parts=[{}]`，不能据骨架声明正文完整。
5. 快照读取器的词法root alias检查目前依赖上游owner路径验证；helper单独调用不是完整anti-reparse证明。新增身份门仅覆盖已知身份字段与容器，非全部身份安全。
6. 据真实格式验证五区正文、question_info、原图/显示页/保存页及裁图，再准备保存请求和独立读回。四响应本身不证明六阶段读、保存回执或平台保全。

以上均保持 `CURRENT_SCHEMA_UNBOUND/HOLD`、`write_allowed=false`、后继NOT_RUN。无新OCR/外部模型API调用，团队使用现有Codex会话。章节分母、Q9题页、独立内容验收与网站保存状态不因本增量改变；未替A填写接收通过。
