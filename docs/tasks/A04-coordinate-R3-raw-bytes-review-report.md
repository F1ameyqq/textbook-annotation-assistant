# A04 coordinate-R3 原始Git字节独立补充报告

2026-10-17（Asia/Shanghai）。**原字节补证PASS；限定OFFLINE_R3=ACCEPTED；A04_OVERALL=BLOCKED。** 本次在逐文件核对的`cat-file`原始blob上，原样重放精确反例、70项相关回归和26项独立检查，均符合预期。主调度收到本冻结补充后再决定有限接受与集成，本报告不回写state或释放下游。

## 更正原来源声明

原R3报告把`git archive`导出的212项称为“全量原始Git字节”，**该描述错误，是验收者没有把archive内容再与各原始blob逐项比较**。原清单准确绑定了当时实际archive/运行输入，但不能证明其全量等于Git原字节。原70项和26项结果保留为此前archive表示的一次运行，不追改为本次原字节成绩。

本次独立确认212项中有59项archive字节与目标blob不同：55个Python、1个`.gitattributes`、3张ASCII PGM，均仅CRLF/LF差异。文本归一只用于解释差异，**没有用于本次接受判定**。详见 [59项逐文件差异](../evidence/A04/review/coordinate-R3-raw-bytes/archive-vs-cat-file.json)；[主调度首次失败原件](../evidence/A04/review/coordinate-R3-raw-bytes/inputs/workflow/docs/evidence/A04/coordinator/coordinate-R3-acceptance/archive-preflight-failure.json)也已按固定workflow保存。

原报告SHA256 `ce6bc599c0b1533e58095366c4f8b499248079aa6c571e8569e1b585d4a82e61`、原清单SHA256 `d756ab8d28d49350883fdf47289497451833818bfb76649568dbb8467e9f4002`及其355项、tar、脚本、原始流和旧材料全部保持字节不变。本补充纠正旧报告的来源声明；没有覆盖旧证据或掩盖失败。运行前后均核对**355项＋原清单自身＝356份记录**，见 [前](../evidence/A04/review/coordinate-R3-raw-bytes/old-preservation-before.json)、[后](../evidence/A04/review/coordinate-R3-raw-bytes/old-preservation-after.json)。

## 固定目标、逐blob运行输入

| 项目 | 固定值 |
|---|---|
| 目标 / 实现 | `6c8137a4fadddc01a47906d564ab3460277c8958` / `81d62255b545b88f344849d08011a2a859c49c5e` |
| 补充workflow | `9317efcdb734b081075c56f6557838d591959e8f`，明确xhigh，不用ultra |
| 任务 | [固定补充任务单](../evidence/A04/review/coordinate-R3-raw-bytes/inputs/workflow/docs/tasks/A04-coordinate-R3-raw-byte-supplement.md) |
| 原复验workflow | `d834bf531f95abac7ed30b89b3ca55105fa6f491`，只作前次运行来源 |
| 新实际产品目录 | `D:/1800/docs/evidence/A04/review/coordinate-R3-raw-bytes/inputs/raw product with spaces` |

路径集合沿用原212项，**内容重新从固定目标的`git cat-file --batch`二进制协议提取并用`write_bytes`落盘**，不使用archive、checkout、工作树换行转换或浮动主树。逐项读取object ID/type/size，重算Git的`blob <size>\0<data>` SHA1与object ID一致，再记录SHA256/大小；实际运行前和结束后均逐文件比较，212项全部精确一致。证据：[cat-file命令/查询记录](../evidence/A04/review/coordinate-R3-raw-bytes/cat-file-export-command.json)、[运行前](../evidence/A04/review/coordinate-R3-raw-bytes/runtime-inputs-before.json)、[运行后](../evidence/A04/review/coordinate-R3-raw-bytes/runtime-inputs-after.json)。二进制payload本身保留在上述新产品目录。

精确反例、70项回归、26项独立检查及所需`process_identity`/guard均从旧355项中逐字节复制；**原检查代码和期望值未改**，复制摘要见 [脚本绑定](../evidence/A04/review/coordinate-R3-raw-bytes/replayed-scripts.json)。旧`run_jobs.py`硬编码原stage/output，不能直接使用而不改动旧目录，因此新增的`run_supplement.py`仅负责新路径、参数、stdout/stderr和PID记录；没有替换检查逻辑。临时额外`sitecustomize.py`是原guard副本，单列于 [harness记录](../evidence/A04/review/coordinate-R3-raw-bytes/runtime-harness-bootstrap.json)，不属于目标212项，也未替换产品文件。

实际加载的parser、PNG门禁和公共loader均来自新目录，其文件SHA256与对应cat-file blob精确匹配，绝对导入路径和环境见 [实际导入](../evidence/A04/review/coordinate-R3-raw-bytes/actual-imports.json)。未安装/升级依赖。

## 本次独立运行结果

| 本次命令/观察 | 结果 |
|---|---|
| [未改精确反例](../evidence/A04/review/coordinate-R3-raw-bytes/jobs/exact/command-result.json) | wrapper退出0，产品CLI退出2；原180字节/37×29/hash不变；无输出目录、历史或最终包 |
| [4模块相关回归](../evidence/A04/review/coordinate-R3-raw-bytes/jobs/regression/command-result.json) | **70/70**，无error、failure或skip |
| [原26项独立检查](../evidence/A04/review/coordinate-R3-raw-bytes/jobs/independent/command-result.json) | **26/26**；输入、输出、原始stdout/stderr和20个Python子进程记录全部为新目录 |
| 原始PGM公开来源与搬运 | 三张cat-file PGM直接发布，经含空格目录搬运后由未改公共loader/完整解码器消费，原字节资源绑定通过 |

新结果见 [70项](../evidence/A04/review/coordinate-R3-raw-bytes/regression-result.json)、[26项](../evidence/A04/review/coordinate-R3-raw-bytes/independent-cases/results.json)。[两次运行对照](../evidence/A04/review/coordinate-R3-raw-bytes/separate-run-comparison.json)明确旧archive运行和新cat-file运行，不合并或双计成绩。没有发现输入表示差异引起的新产品缺陷；原R3的受限静态PNG行布局、发布复查、正常格式搬运及资源限制结论在本次原字节输入上得到补证。

实际命令逐项包含完整argv、cwd、创建时间、返回码、stdout/stderr原始文件及摘要，位于`jobs/`。可使用新目录重放精确反例，例如：

```powershell
python -B D:\1800\docs\evidence\A04\review\coordinate-R3-raw-bytes\inputs\replay-scripts\exact\repro_incomplete_rows.py `
  --root 'D:\1800\docs\evidence\A04\review\coordinate-R3-raw-bytes\inputs\raw product with spaces' `
  --output 'D:\1800\.local\stages\A04-review\coordinate-R3-raw-bytes\fresh exact output'
```

该命令wrapper预期0，内部产品拒绝码2。生成型控制器不在已存在的证据目录反复运行；本轮只进行这一次表示差异补证，没有扩大旧完整矩阵。

## PGM原字节与资源绑定

三张PGM的旧archive和新原blob尺寸/像素均相同，但字节与SHA256不同。公共来源产物、搬运后的资源及公共loader绑定的是**新的原blob摘要**，没有沿用旧archive摘要或以归一摘要替代。

| 页 | 新原blob字节 | 旧archive字节 | 新SHA256前缀 | 解码尺寸 |
|---|---:|---:|---|---|
| 14 | 91 | 98 | `ea3dfc631e55` | 4×3 |
| 15 | 93 | 100 | `03c2c3c403f3` | 4×3 |
| 173 | 92 | 99 | `5f20420e50bd` | 4×3 |

完整object ID、SHA256、旧摘要、发布/搬运摘要、MIME与解码像素摘要见 [PGM绑定](../evidence/A04/review/coordinate-R3-raw-bytes/pgm-resource-bindings.json)。这是合成离线fixture，不是当前平台原图或书籍状态。原始CLI流见 [发布](../evidence/A04/review/coordinate-R3-raw-bytes/jobs/raw-pgm-cli/stdout.txt)，搬运后的未改消费者流见 [消费](../evidence/A04/review/coordinate-R3-raw-bytes/jobs/raw-pgm-consumer/stdout.txt)。

## 范围、释放与交付

本次沿用R3限定支持/兼容边界，不重新设计功能或扩展格式。Node deadline、Windows junction、旧完整浏览器/合同/坐标矩阵、配置上限极端压力、D01安装和真实R01～R06均未运行，不计本次通过。S01仍未通过。主树尚无source/usense，整分支合并还会带入未接受代码；本轮没有进行合并、拆包或集成方案设计。

[自身进程结束证明](../evidence/A04/review/coordinate-R3-raw-bytes/self-release.json)按PID＋创建时间核对28个原自有进程身份，全部结束；27份guard退出记录无越界事件。只查询记录的自有身份，不扫描全系统、他人会话或profile，不终止被复用PID的新进程。自有子进程均已等待回收，无后台服务。

浏览器、网络、平台、profile、凭据、登录、OCR、模型及书籍动作0，付费模型调用/花费0；未重试GET或题22，未修改产品、依赖、state或旧材料，未提交、推送、集成或联系执行者/B/其他任务。

[最终检查](../evidence/A04/review/coordinate-R3-raw-bytes/closure-checks.json)与 [新完整清单](../evidence/A04/review/coordinate-R3-raw-bytes/sha256-manifest.json)冻结本补充、真实运行输入、未改脚本、新结果和旧356份保全证明。结论为**限定OFFLINE_R3=ACCEPTED / A04_OVERALL=BLOCKED**，不代表主调度已集成或真实平台依赖已释放。本轮冻结后结束。
