# 第二课时五题实际交付

2026-10-23：五题已完成真实保存、独立读回、平台原生导出、题图和公式显示验收。A26 正式独立验收及根协调均通过；本次导出阶段保存次数为 0，未重做 A25 五次保存。

- [打开五题离线成品](D:/1800/.local/stages/a26-native-export-20261023/native-delivery-01/index.html)
- [完整离线交付包](D:/1800/.local/stages/a26-native-export-20261023/A26-lesson2-five-native-delivery-20261023.zip)：解压后打开 `A26-lesson2-five/index.html`。
- [正式验收报告](evidence/A26-independent/final-native-delivery-actual-review/report.md)
- [根协调收口](evidence/coordinator/a26-final-native-delivery-closure/receipt.json)

交付范围为书籍 `46007447` 的第二课时印刷第 1—5 题。A25 已接受五次保存和五次新鲜独立读回；A26 新增一次官方原生导出和五张精确题图读取，均成功，浏览器及持有进程释放完成。

官方 JSONL 原件共 14,167 字节、22 行，完整解析，无坏行跳过。仅目标五题被本次接受；原生记录不含稳定 node/info ID，因此以完整内容唯一匹配到 A25 已接受的五个稳定身份，并明确核对换行与选项数组转换。其他 17 行未重新验收。

5 张题图完整解码并显示，36 处公式及单位可读；正式独立查看了 5 张整题截图及 36 张公式近照。ZIP 共 59 个文件，58 个内部清单成员核验通过，内含原生数据、展示 HTML、题图、MathJax 本地资源及证据。包内 HTML 与实际观察的 HTML 字节相同，不依赖外部资源。

第 1、5 题原图自带部分题干，展示有文字重复，但图形、标签、正文及答案完整可读，保留原件未改图。结论限这五题及已观察的桌面显示；未作整书、打印或移动端验收。原父目录课时标注冲突仍保留，第 3 题原 strict FAIL 和第 4 题原关闭异常均未改写。

ZIP SHA256：`7b1718ff909b013e0426dad890189dfa22bea5c101a6535a166544cc7c0c0bfc`。

原生 JSONL SHA256：`0943e76f2dfcbd04fd4e47f644ebbc2ded54c045c031baac3bab7a969d94f3ef`。

正式结果 SHA256：`8d5e88464a379216d4f79d561d2ce04dc5d7d900a7de58a4d8f3ccc014c2b01e`。

并行 A27 稳定性修复已通过正式独立及根协调的有限离线验收，并将产品工作区快进至 `ebca4c71a70bdfb5fbccc023d00e0207ae532470`。首次发现的 Windows 等价 profile 路径占用漏判已修正，原 REWORK 与失败证据保留。此次接入没有重复保存或读回；新恢复流程的真实平台运行仍未执行，详见 [A27 收口](A27-stability-closure-20261023.md)。本交付包及其原实测基线保持不变。唯一 `1800-a` 保持 PAUSED，无远端推送或 B 消息。
