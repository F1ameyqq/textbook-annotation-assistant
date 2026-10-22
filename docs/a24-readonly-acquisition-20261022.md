# 用户登录后的只读采集与A24采集器修复

日期：2026-10-22，Asia/Shanghai。B输入提交 `78096509ce57244667a2298205054907edc46a05`；A24固定基线 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`。用户明确已登录并授权只读采集、真实格式适配与旧题保全验证，网站标注不得修改。

## 本轮平台事实

用户在来源成员创建的独立Edge标签 `1199071973` 完成登录；随后标签清单显示 `https://www.usense.com/qieti/home`。本次阻断不是账号未登录，也不是旧标签被其他会话占用：

- 浏览器DOM绑定报 `Debugger unattached`。
- 原生Windows回退报 `Computer Use could not determine the current browser URL on Windows with enough confidence to enforce policy` 并强制停止。
- 来源成员依工具停止规则结束网页动作，未通过其他会话、Cookie/token、CDP或shell HTTP绕过；主会话也未接管浏览器继续尝试。
- 当前book、directory、fullframes、natural export均 **NOT_RUN**，没有平台业务原件增量；网站编辑/保存/提交均0。

[来源原始报告](reviews/a24-logged-in-readonly-block-20261022.md)与机器记录分别归档。`/home`只证明登录重定向完成，不证明书籍身份、API权限、全量旧题/框或当前schema已取得。A的旧四GET/旧私有摘要不作为本次新来源。

恢复条件是现有标签的受支持浏览器调试连接恢复，并能可信识别目标URL；不要求用户重新登录或反复新开标签。本轮没有改变浏览器扩展、安全设置、profile或锁，也没有恢复旧自动化/旧authority。主会话曾尝试读取官方排障资料，但文档搜索/页面连接失败，没有据此编造受支持的修复步骤。用户手动取得的平台导出文件也可作为离线输入；必须标明文件来源及完整性，不能自动当成四份当前响应或fresh读回。

## 已实际集成的采集器修复

此前 `owner.acquire_current_schema`只保存directory/frames/export正文，book仅有长度和哈希。原book正文无法靠哈希补回。本轮修复未来采集行为：

1. 既定四个GET的路由、顺序、参数、次数均不变，成功路径仍为4次。
2. 四份成功正文均以 `xb` 写入owner私有目录；新增 `private/book-snapshot.bin`，旧文件存在即拒绝覆盖。
3. 所有槽的观察记录及私有引用标明 `capture_representation="UTF8_REENCODED_RESPONSE_TEXT"`；这是fetch响应文本的UTF-8重编码，不宣称网络原始压缩/传输字节。
4. 不持久化认证头、Cookie/token或查询值；未知业务字段只在私有正文，公开引用仅含槽位、路径模板、查询键、长度/摘要及采集类型。
5. 非200先停止，不落盘失败正文、不继续后继请求；未知schema仍 `write_allowed=false`、`successors=NOT_RUN`。未改变鉴权/guard或任何写入资格。

主会话已应用到隔离工作区 `../a24-takeover-20261022/source/`，与此前测试夹具修复叠加。没有覆盖原A固定发布树；[作者报告](reviews/a24-book-capture-producer-20261022.md)、[独立差量审查](reviews/a24-book-capture-independent-20261022.md)与[机器记录](../evaluation/a24-readonly-acquisition-20261022.json)保存原件/发布件摘要。

|当前变体文件|固定摘要/用途|
|---|---|
|`src/annotation/runtime/live_pilot/owner.py`|基线SHA `fb5bcd815d075f425d97845da13b64c2e06f62ecb990f41924377dadea8aeaaf`；本轮LF文件SHA `dc5113d1984c58d63ea3a26b95d45664aed60a0915a31b9f4afab592169e1318`|
|`tests/a24_book_snapshot_fix/test_book_snapshot.py`|作者3项测试加独立第3次GET失败负例；最终SHA `3af68d67fe779c1b054a2b4b2a2277577c55b6c32956544166b319251a6f1210`|
|`tests/a24_first_save_current_body/test_minimum_gate.py`|沿用上一轮已集成的10项夹具修复，SHA `e040411bbbf2881470c99aec0589bfa5558e6a9d70c4085abf2eafc27040977e`|

发布可应用文件位于 `docs/evidence/a24-readonly-acquisition-20261022/`：`owner-book-snapshot.patch`、`book-snapshot-third-get-negative.patch`和完整最终 `test_book_snapshot.py`。对固定A24应用owner补丁、加入最终测试文件即可形成这项变体；测试夹具补丁沿用上一轮交付。变体修改owner代码，**旧候选依赖哈希和历史activation不能用于运行此变体**。将来真实读取前需按实际字节重新冻结依赖和新鲜精确范围；本轮未生成/激活live配置。

独立成员的Windows补丁副本因CRLF产生不同原始SHA，报告同时保留CRLF原SHA和LF规范化SHA，仅作语义差量承接。主会话实际文件逐字节等于上表LF摘要，不用规范化摘要冒充实际运行字节。

## 有限回归与失败保留

主会话在修改后变体实际完成 **21项相关回归**：

- 4项快照测试：四正文落盘/摘要回读、已有文件拒绝覆盖、首个HTTP失败停止、第三个GET失败时仅保留book与directory并停止后继。
- 7项受控捕获集成，10项现有正文/重开门禁回归；均为合成对象和禁止真实IO的测试。

作者原先3项通过后，质量成员独立扩展至4项并通过，主会话再实际运行最终4项。7与10项也在修改owner后重跑，不借用改动前结果。

主会话第一次禁网复测脚本误拦了Windows asyncio本地唤醒socket，造成4项失败且协程未进入被测业务；该失败回执保留。随后使用仓库已有 `noio_loop.MemoryPolicy` 的内存事件循环，保持禁网及原产品断言，4/4通过。未通过放松网络拦截或改预期让测试变绿。这是复测框架配置错误，不改写成产品或平台失败。

本轮复用内置Python3.12.14/Pydantic2.14.1/Pillow12.3.0和规范长路径TEMP；没有新安装/下载，没有运行项目OCR或外部模型API。团队会话消耗现有Codex额度，不表述为免费或零模型推理。未进行原A环境的干净安装或真实浏览器兼容性验证。

## 旧题保全：具备条件门，实际效果仍未证明

[独立保全审计](reviews/a24-old-preservation-20261022.md)核查当前wire/quality/runner的条件性门：五区正文、question_info和额外业务字段、题/框ID、order、目录、删除/upsert、新题去重、savepage及保存后get/refresh/reopen相对同一baseline的保全比较。6项有限负例均按预期拒绝：

- 没有权威完整性记录；natural export无路线资格；五区缺键；题清单缺旧正文分母；旧question_info被篡改；裁片savepage与来源不符。

这6项使用固定A24 checker，是独立的合成拒绝检查，不是本轮实际旧题保全。当前仍无真实完整book/目录/题/框/导出输入、原生请求和六裁图，不能核准实际格式或分母，不能填写VERIFIED、伪造metadata或用旧22题/68框放行。

## 接续安排

来源成员已按工具停止规则结束；内容成员完成最小修复，质量成员完成保全代码审计和补丁差量审查。实际状态以会话回执核对，不把派工写成永久后台工作。

收到可验证的新来源或用户手动导出后：先保原字节、SHA、媒体/采集方式和当前书身份；建立独立题/框分母；再据实际字段做schema/profile/request/plan/guard/savepage最小适配，由另一成员核旧题全量覆盖与字段不变。来源不全保持明确缺件，不以模型或JSON自填核准顶替。网站仍只读，实际保存/refresh/独立reopen均NOT_RUN。
