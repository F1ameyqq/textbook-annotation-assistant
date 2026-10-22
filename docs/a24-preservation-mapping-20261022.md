# 当前导出阻塞、历史原件保全与身份映射增量

2026-10-22，Asia/Shanghai。B输入 `16b2c6bb7e0983d3a34385d8c6d5f267461b4ab0`；原A24 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`。整体进度见[项目现状](project-status-20261022.md)，本轮精确字节、命令及证据见[机器记录](../evaluation/a24-preservation-mapping-integration-20261022.json)。

## 真实读取的新结果

来源成员保存了当前DOM原件，提取143个已渲染树节点、8个顶层章节条目及22个“插题”标签。它不是服务器全量目录或题目分母，没有证明稳定question_id。

上轮“导出试题”的UNKNOWN在同一标签页出现明确的可见结果：“导出试题预检未通过”，9错误、0警告；没有重复导出。本轮只将UI结果收敛为PRECHECK_FAILED，不声称已取得HTTP回执或下载路径。“导出整套书籍JSON”仍UNKNOWN。

|界面字段 importShitiID|可见预检错误|
|---|---|
|1、2|选择/多选需要choice|
|7|question、answer为空，choice缺失|
|19、22|question、answer为空|

这是平台当前导出预检报告的字段缺失，不代表源图片里没有题目，也不证明这些数值等于本地Q1/Q7或服务器主键。历史JSONL的option与当前预检的choice也不能未经适配证据直接视为同字段。有旧框不代表导出正文完整。

读取停止点：唯一一次后续题目选择使控制工具强制终止，完成状态未观察，成员遵守停止要求，没有再点击或读取。两个新私有原件长度/SHA已由主会话重核；账号标签及原DOM不入库。[来源v3](evidence/a24-preservation-mapping-20261022/source-v3.md)记录具体恢复入口。当前没有可核验的新导出、服务器稳定题ID或完整题/框集合，网站编辑/保存/提交/上传均0。

## 不等当前导出的离线成果

基于10月16日真实19条原件，新增历史原件旁路读取与保全层：整文件SHA/长度、逐行原始跨度与换行、完整字段/extra、选项顺序、HTML/TeX、空串/空数组/null保持；逐字节重建和完整对象比对均通过。公开清单只含字段名、字节引用及摘要，不含题文。

身份账本19条分别固定文件/原始行身份，canonical及selected全部null，实际DOM逐题连接数0。行号、内容指纹及可选DOM候选均为局部证据，多对多歧义HOLD，不选第一个。不能据19与22相减推断漏题。

独立复验发现首版数值精度/溢出和内部_value可变两个问题，已采用最小修补：拒绝JSON浮点/指数（HISTORICAL_JSON_NUMBER），记录值从冻结record_bytes重解析；真实19条没有浮点，不受该限制。NaN/Infinity字面仍拒绝。叶文件reparse检查不宣称父路径全面防护。作者Decimal变体及probe保留为未采用实验，禁止叠加到正式版本。

这解决历史原件的保留和独立读取，**没有接入当前natural codec或保存路径**。natural codec完整raw/extra值承载、权威身份来源、当前catalog/state绑定仍OPEN，现有准入不变，write_allowed=false。

## 固定补丁与实际复验

[组合补丁](../handoffs/b/a24/a24-historical-preservation-adopted-v2-20261022.patch)：16,928字节，SHA-256 `524467067bc0f33d976e8dd1c41a46bc45809d0a863d3c65266f3cf6ac02d820`。只新增两个A24文件，不把A/B两个annotation命名空间混装：

- `src/annotation/runtime/live_pilot/historical_preservation.py`，SHA `636707c2fec0889627220657ef7099ea2a135ce8263165a2987e14e9d40ccf27`。
- `tests/a24_historical_preservation/test_historical_preservation.py`，SHA `295263cc873af9e247edf79d26c6793c5ffb621305631cf448d293228dbac380`。

在[已固定离线ZIP](a24-offline-replay-20261022.md)重建的523文件树上先应用[schema-readiness-v2补丁](a24-browser-recovery-schema-readiness-20261022.md)，得到525文件；再在独立副本应用本组合补丁，得到527文件。主会话实际应用质量成员等效组合补丁，最终两源码与发布补丁/作者采用版SHA一致，原525文件全部不变；没有覆盖A原树或旧B内容包。

在525文件干净副本中可执行：

```powershell
git apply --check --whitespace=error-all <本补丁绝对路径>
git apply --whitespace=error-all <本补丁绝对路径>
$env:PYTHONPATH = "$PWD/src"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:A24_HISTORICAL_EXPORT_PATH = '<私有历史JSONL绝对路径，先核对源SHA>'
python -m unittest discover -s tests/a24_historical_preservation -p test_historical_preservation.py -v
python -m unittest discover -s tests/a24_schema_readiness -p test_schema_readiness.py -v
python <本仓库docs/evidence/a24-preservation-mapping-20261022/independent-tests.py绝对路径> -v
```

实际主会话7+14+6=27项通过、0失败/错误/跳过，三命令退出0；质量成员另独立7+6+14=27项通过，不把两次相加当54种场景。相关反例包括错SHA、源字节篡改、重复嵌套键、数值拒绝、解析对象修改、伪造canonical输入及多对多候选。原有完整R1的3项历史ERROR没有在本增量重跑或宣布关闭。

本次首轮发布整理因将wire.py误定位到runtime目录而FileNotFoundError，修正为实际delivery路径后通过；它是发布脚本路径错误，保留于主会话记录，不算产品回归失败，也没有变更代码以放宽测试。

## 后续工作与限制

下一项业务推进是从受支持只读入口取得预检缺失字段的真实值、当前全量成员集合与稳定身份，再把原记录保全接入实际适配/比较层。不能靠补写网站、合成完整metadata、旧行序号或自填权威资格绕开导出预检。受支持控制恢复前，不继续碰强制停止的网页动作；现有离线保全代码与负例可交接使用。

三原成员本轮已分别交付；这是模型团队交叉核查，非独立人工内容验收。第一章来源/身份分母、18项Q16/阅读人工处置、全章冷运行及真实平台保存验收仍未完成。公共合同继续提案状态，固定输出范围兼容性只按已实际消费者结果声明。
