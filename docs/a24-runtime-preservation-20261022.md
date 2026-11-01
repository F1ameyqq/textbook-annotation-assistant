# A24运行时旧数据保全：限定范围修复与可重放交付

2026-10-22晚间；B输入`9d4c0fc78ca5176d30d2661283a60897748740e8`，A24接管基线`c5aefbc8e995c410b3babf74a251f05a7724a1c2`。本轮将旧题原始字段保全接入实际`UsenseTransport.observe → check_preservation`链，并保留此前误放行的独立反例。当前网站完整正文和native格式仍未取得，不启用网站写入。

## 修复后的行为

- 原始题、框、目录和内容记录按稳定身份保留；格式投影丢掉的未知字段仍进入比较。缺少原始实体绑定时拒绝，不能从已丢字段的标准化副本补造“原始数据”。
- JSON类型、对象键序及未知字段的增删改均参与检查，`0`与`false`不再被Python相等语义混同。reopen/reconcile内的两个比较也改用严格规则。
- 已声明业务子树使用有类型的占位保留包装结构，检查未投影包装层变化。合法新增一题六框仍可通过；不会通过比较整份响应而误拒合法追加。
- 不明确的根路径、数组索引、重叠/重复路径、过滤数组和未消费请求拒绝；递归`children_path`仍明确不支持，未伪造当前目录结构的支持证明。
- 业务读取保留的是`UTF8_REENCODED_RESPONSE_TEXT`，不称原生HTTP字节。上传签名及其凭据不进入业务原始观测；哨兵测试只使用合成值，未请求真实签名或上传。

旧v2虽然自测10项通过，独立固定预期为8通过/1失败，包装层与合法追加的另一反例失败，因此未采用。v3修复后独立28项核心检查通过；[独立报告](evidence/a24-runtime-preservation-20261022/independent-report.md)和[失败历史](evidence/a24-runtime-preservation-20261022/v2-rejection.json)保留不同版本事实。

## 直接运行

```powershell
python tools/replay_a24_runtime_preservation.py --out data/runs/a24-runtime-regressions-new
```

入口先核代码包及127个成员的字节/SHA，再在新目录提取并隔离A/B Python命名空间，实际运行5个suite、56项合成回归，0失败/错误/跳过。损坏代码包在落盘前拒绝；已有输出目录拒绝覆盖。需要已有Python/Pydantic 2/Pillow环境，本轮未声称全新依赖安装验收。

公开代码包：`handoffs/b/a24/a24-runtime-preservation-v3-20261022.zip`，506,731字节，SHA `2f97801dc13bc040b1eefb97b02932c2c7cbfee887297eedf579cd6998c52638`，128成员含清单；仅115个运行源码/资源及合成测试、夹具。无私有正文、原图、浏览器状态或凭据。旁边同名`.patch`是对上轮有效A24树的审阅差量；使用代码包入口无需手工叠补丁。

[独立公开包消费](evidence/a24-runtime-preservation-20261022/public-consumption-report.md)再次核127个成员长度/SHA、0额外或缺失成员，并从新目录真实运行同一入口56/56通过、0跳过。两次执行不累加为112项覆盖；唯一PGM为100×100全白合成夹具。

原`tools/run_a24_archived_preservation.py`已接入该运行包。主会话用固定解析归档、历史19行和当前Q1 DOM证据实际执行，5个输出与上轮逐字节相同；22题/68框、独立历史19行及canonical=null保持。它验证归档读写保全，不证明全部当前题文已采集。

主会话另以私有历史原件运行7项回归，无跳过；schema14、归档8、只读6均通过。规范TMP/TEMP目录下，旧controlled-capture7项及current-body10项在原版和v3均通过；R1两版仍同样17通过/3错误，没有称全绿。默认短路径TEMP下的旧1失败/7错误记录保留。确切结果、输入与代码摘要见[机器记录](../evaluation/a24-runtime-preservation-20261022.json)。

## 支持范围与下一步

独立结论为`PASS_OFFLINE_ENGINEERING_INCREMENT_BOUNDED`，限定于已验证的snapshot/request包装层及身份绑定的原始题/框/目录/内容记录。条件性`A24CompleteExportCodec/v1`的metadata未知字段尚未进入保全；[两项范围证据](evidence/a24-runtime-preservation-20261022/test_complete_export_metadata_scope_boundary.py)演示该缺口，不能计作功能验收通过。实际OBSERVED owner要求NaturalExport，资格仍UNBOUND；未补metadata保全或明确拒绝该路线前，不能激活CompleteExport进行真实操作。

本机解析归档已有121目录、22题和68框，但不是完整native响应：缺原包装层、原始`image_path`/`user_id`，22题正文全部UNKNOWN，`append_after_order=null`，观察顺序没有证明为保存顺序。历史19行没有稳定题ID，不能按行号与22题连接。Q16/三阅读任务仍为free_response、共享材料/公式/图片及UNRESOLVED关系，超出当前普通单选六文本框准入。[逐字段缺口审计](evidence/a24-runtime-preservation-20261022/native-format-gap-audit.json)已绑定固定ZIP原件，原印刷号16不能连接不同分支的同号节点。

下一有效输入是同一当前状态下的目录及完整框原始响应、稳定题ID绑定的全旧正文、服务端追加顺序、原图页到savepage及回执/读回格式。取得后在已有读取/保全链内适配并核对；不新增重复的归档工具，也不以生成`complete=true`或目录候选解除缺口。第一章来源、Q9真题、独立人工处置、平台保存及接收仍未完成。网站修改、识别/验证按钮、保存、提交、上传、模型及付费调用均0。
