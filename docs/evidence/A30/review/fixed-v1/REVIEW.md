# A30 v1 独立验收：普通数字答案分页仍需返工

2026-10-24；独立方 `01a16bf6-f61d-7f40-a4cc-2f1201f2ece3`。

**结论：REWORK（普通 TXT 分页配答），CUSTOMER_READY=false。** 固定产品为 `8ac7be97c104c4cc57004de691ba21e5d4b92b33`。这是一个具体输入适配阻断，不否定其已实现的来源保存、候选及本地审校结构；也不重验 A28/A29 九题和有限包。

## P2：独立答案页的“23. 7”不能配答，也不能在现有审校入口解决

独立方自建 UTF-8 普通 TXT，未提供候选、manifest、哈希、题框或接受标记。从公开 `tools/customer.py prepare` 入口输入新书号 `825719`、课时“跨页独立文字课时”，题目和答案各含两页，分页字符为换页符 `\f`。

- 题页 1：第 21 题问春季后的季节，第 22 题为四选一；对应答案为 `21. 夏季` 和 `22. A`。
- 题页 2：`23. 写出一周的天数。`；答案页 2：`23. 7`，以换行结束。
- 实际：公开命令退出 0，三题均被建立；前两题答案分别为“夏季”和“A”，第 23 题答案为空、含 `ANSWER_MISSING_OR_AMBIGUOUS`，任务为 `NEEDS_REVIEW`。
- 答案第二页产生全局 `UNASSIGNED_ANSWER_OCR_LINE`，详情为 `No trustworthy primary answer anchor in this semantic window.`。普通明确数字答案没有接入候选。

静态定位：`src/annotation/customer/prepare.py:204` 将本任务来源交给 B 组装；`src/annotation/recognition/answer_assembly.py:358` 记录未分配答案行；`src/annotation/customer/review.py:136`–137 禁止确认仍有此类全局问题的任务。没有执行强制确认、改状态或绕过 HOLD。用户只能返回修改/重制原材料，当前入口尚不能通过普通审校补充这条明确配答；不能把它算成普通输入完整闭环。

相关新增修复只需处理可靠 TXT 编号与数字答案的连接，或让普通审校补全来源绑定并重新校验；不要直接删除 HOLD，也不需要为此重跑旧 OCR、旧矩阵或平台保存。

## 固定来源与运行证据

根固定索引：`D:/1800/.local/stages/a30-customer-independent-20261024/root-fixed-v1/root-index.json`，SHA-256 `ba98f2ecf0f8eb4bcf6f8411304c12eb338404243d8cf2839cca7e4fdbf83d85`。独立复核并复制 203/203 输入，177 源文件与 Git/ZIP/原始副本相符，5 处声明差异仅为 CRLF/LF；23 证据副本哈希相符。作者原工作区及其活动证据未读取。

独立隔离目录：`D:/1800-private/a30-independent-review-20261024-v1/`。实际执行源为其 `root-input/raw-source/`；普通输入、完整命令、原始 stdout/stderr 和实际 SQLite/blob 状态位于 `checks/`。`semantic-result.json` 和 `review-manifest.json` 固定本结论及证据哈希。

首次辅助脚本错误为将 Windows 默认 GBK stdout 当作 UTF-8 解码；保留 `checks/result.json`、`checks/first-error.txt` 及原始输出。只做独立编码探测（`stdout=gbk, utf8_mode=0`），按该编码读取原输出并验证逐字节 roundtrip，**没有重跑准备调用**。据此发现上述语义阻断。后续查询另有一次 rg 引号/正则错误，修正查询后仅定位固定代码；两次辅助错误保存在 `helper-events.json`，不计产品失败次数。

实际产品准备调用 1 次，产品后继检查 6 项 `NOT_RUN`：本地导出、另一课时页范围、缺答确认阻断、未知保存阻断、原图无 OCR 导入、作者新增 25 项套件。作者宣称的 25/25 只保留为作者证据，本次未独立复跑。真实识别质量、GUI 操作、首次安装、平台/凭据/付费模型、保存/读回/原生导出均 `NOT_RUN`。模型页 0；完整客户总历时和实际客户介入次数 `NOT_MEASURED`。

本次只写独立报告和证据；不修改产品、根 JSON、AGENTS 或自动化。原始失败及后继未运行状态保留。收到修复后，从此普通输入反例继续相关增量验收。
