# 续页正文的行内数学补读与可恢复交接

2026-10-17，基线 `c89e38c933c6676d3d73a82cea1c8e1f906a79a1`。本增量服务于长期 L1 内容正确性、L2 可恢复处理及 L5 交接；整书终点及验收见 [长期目标](b-long-term-goal.md)。公共合同仍是草案，A 接收验证为 PENDING_A，网站标注未修改。

## 实际解决到哪里

对 resource173 已续接答案中的全部9行正文执行固定3倍/4倍普通CPU OCR，共18次调用、20条原始检测结果。逐行保存完整原始返回、字符数组、低分项及源像素/变换。普通OCR的字符框来自CTC时序和平均宽度估计，不能充当精确字形框或已证明的数学角色。

按固定规则保留59个数学片段及18个整行后备区，共77个单元。数学片段包含变量、数字和运算符；原文`十`只标记为可能混淆的运算符，不改成`+`。纯字母、单位及纯数字保留但不调用公式模型；整行后备也保留，尚未自动推理。其余23个片段，各有紧裁片和上下文两种范围、原始大小和3倍两种canvas；精确同源范围去重后84次公式调用、92个单元绑定。

逐调用SQLite保存意图、attempt、事件和不可变对象。实际先完成8次、保留76次PENDING，随后复用8次并补完76次；再次显式运行84次全缓存、encoder-decoder入口0次。显式运行仍初始化一次本地模型；默认缓存CLI完全不导入模型。原始token ID、解码字符串、后处理LaTeX、失败、尺寸调整和源像素回执均保留，不选择候选、不修改旧OCR或图谱。

| 实际开发观察 | 当前结果与限制 |
|---|---|
| 第3行 `20+5=25(cm)` | 紧裁片有完整候选；上下文路径仍有中文诱发的未知命令和幻觉 |
| 第3行 `AB²=10²+25²=` | 新候选找回10的上标，但两次相同输出均多出末尾`1`；等号后的725在下一行，尚未组装正确 |
| 第4行 `10+5=15(cm)` | 有加号候选；另一变体输出`\mp`，原普通OCR的`十`完整保留 |
| 第5行 `AB²=20²+15²=625` | 原始大小有完整候选；3倍变体误读为20的四次幂及13，未取代旧结果 |
| 第6行 `AB²=30²+5²=925` | 有完整候选；另有被拆成两段、幂误为字母等结果，没有跨段混拼 |
| 第7行 `625=25²` | 紧裁片有正确形状候选；上下文仍误读次数和符号。开发参考曾看错，修订见下 |

84条结果中43条受当前语法支持、41条不支持。此数字是语法覆盖，**不是43条内容正确或准确率**。未知命令、尾部内容、根号与幂、比例与整数保持区分。新语法采用显式INLINE profile，旧默认公式语法不扩张。所有候选未选择，HOLD、complete=false、transcription_verified=false、business_acceptance=false。

普通OCR漏掉的运算符可能导致片段范围不全；CTC框也可能切开一个完整等式。整行后备区尚未送公式模型，故不能据84次均执行成功声称正文全覆盖或重建了完整答案。当前补读仍是独立入口，尚未串入持久pipeline或选择性回填图谱。

## 来源参考的更正

此前MODEL_VISUAL开发参考把第7行看成`√625=25`。重新查看原JPG及右上小字形后，当前观察修订为`625=25²`。旧 `continuation-content-review.json` 的字节、引用和原始OCR未变；新增 `continuation-content-review-v2.json` 保存旧参考完整档案、原引用及两字段更正。当前包显式绑定v2，生产者与独立消费者分别核对迁移。

v2仍是未人工核准的开发参考，未作为期望文本传给OCR或公式模型。原始行仍缺上标，新公式候选也未覆盖它。新E6引用与旧运行不同；当前9阶段重新检查仍为115项问题/HOLD，19条UNASSIGNED不变。历史评估按历史版本保留，不能拿v2重解释旧运行。

## 独立检查和交接材料

普通OCR审计重建源裁片、预处理和字符投影；公式审计独立重建全部片段及调用范围、像素、canvas trace、token/AST结构、journal、缓存来源和当前运行回执。审计不调用生产者、解析器或模型。布局头部伪造人工核准/精确定位字段也拒绝，即使协调重签档案和SQL记录；实际84条按修复后的审计再次通过。

这种通过只证明可核对的来源和数据结构一致；没有独立证明模型实际执行的密码学签名，也未凭tokenizer重新认证token到字符串转换，更未证明转写正确。实际入口计数另由code-object profiler观察，并与运行记录比较。

冻结包 `tests/fixtures/book46007447/inline-observed.zip` 保留117个实际文件：E6、行范围、普通OCR全部原始返回、布局、公式逐次不可变对象、真实SQLite只读backup、partial/resume/warm原始观察及回执、两次探索的全部结果。逐成员SHA及包SHA在 `inline-observed-manifest.json`。没有模型权重、原图、登录态或凭证；原JPG需另按SHA提供。包内旧QA回执是历史记录，当前CLI会重新审计并生成新回执，不覆盖旧文件。

```powershell
python -m unittest discover -s tests -v
python -m zipfile -e tests/fixtures/book46007447/inline-observed.zip data/runs/inline-saved
python tools/run_inline_math_b.py --evidence data/runs/inline-saved/evidence.json --source C:/sources/46007447_resource_173.jpg --asset-id resource-173 --rows data/runs/inline-saved/rows.json --workdir data/runs/inline-replay --ocr-observations data/runs/inline-saved/observations.json --formula-workdir data/runs/inline-saved/formula --formula-observations data/runs/inline-saved/formula-observed-trials/formal-warm-observations.json --formula-report data/runs/inline-saved/formula-observed-trials/formal-warm-report.json
```

原图SHA：`8380f9a1872c830b1cf4fba12fa00e3b6d9c50ddaed357587de7333086e9cdbf`，1145×1620。回放输出必须位于journal之外；会只读检查真实SQLite及对象。默认不推理、不下载、不访问网络。新普通OCR必须显式 `--collect-ocr`；只准备行/数学区域可配 `--prepare-only`。新公式需显式 `--collect-formula --models <本地已锁定权重目录>`，可用 `--max-items 8` 续跑。参数组合与失败、PARTIAL/READY、HOLD均有独立CLI回归。

当前正式及探索调用合计：普通OCR19次（探索1+正式18）；公式encoder-decoder104次（探索20+正式8+续跑76），缓存重放0次。尺寸调整模型调用另计，不与encoder-decoder计数混用。无网站请求或标注动作、原图上传、模型下载、额外付费调用。冻结包内仅包含本地派生观察数据，随代码同步仓库。

## 下一阶段

将内容候选以明确来源跨度接入持久链，针对换行等式、CTC分段遗漏和中英文混排检验完整性；保留冲突与失败，不能靠两次一致自动通过。接着扩大已授权原图覆盖、解决19条公共身份，建立独立人工标注的留出集，再做A离线消费者联调。整书来源与页号映射、独立验收和平台测试授权仍是外部依赖，清单见 [给A的需求](a-side-request.md)。

最终干净Git导出807项完整回归通过（原671+新增136）；实际缓存和当前9阶段流水线在两个依赖环境下禁止模型导入/网络仍重放一致。正式公式内部尺寸推理524次，与84次encoder-decoder分别记录。确切源码摘要、Git快照及双运行时实际回放见 `evaluation/book-46007447-inline-math.json`。本页与评估所在PR提交是交付版本；发送成功、A接收验证及联调通过分别记录。
