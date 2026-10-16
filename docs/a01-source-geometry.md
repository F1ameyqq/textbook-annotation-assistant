# A01 静态来源与几何规范

状态：A 内部提案 / 执行交付待 REVIEW。合同沿用 C01 `1.0.0-a-proposal`，未取得 B 确认。

## 几何规范 `a01-geometry-1`

原图连续像素**边界**坐标：左上 `(0,0)`，右下 `(width,height)`，x 向右、y 向下。框是半开 `[x1,y1,x2,y2]`；点允许落在图像外边界。像素 `(i,j)` 的中心为 `(i+0.5,j+0.5)`，不把中心索引当边界坐标。

显式 `Transform` 绑定公共 `ImageBinding`（asset_id、尺寸、SHA256），操作严格按以下次序：

1. `crop=(left,top,right,bottom)` 在**原图域**选择正面积矩形；省略为整图。平移 `(x-left,y-top)`。只接受裁片内的点或框。
2. 乘独立正尺度 `scale=(sx,sy)`，单位为处理图像素/原图像素。缩放后边界宽高必须为整数，不隐式取整或改尺寸。
3. 补边 `padding=(left,top,right,bottom)` 是非负整数处理图像素，平移 `(left,top)`；补边画布宽高为 `W,H`。
4. 在补边画布绕左上原点作**顺时针**90°整数倍旋转，再平移使画布左上为 `(0,0)`：90° `(H-y,x)`，180° `(W-x,H-y)`，270° `(y,W-x)`。90/270°交换输出宽高。

这等价于围绕画布中心旋转后重新放置画布，但本规范明确使用上述边界公式；不能使用 `H-1-y` 的中心索引公式。逆向严格倒序；补边区没有原图内容，逆向点/框落在补边区时报错。框变换四角后取轴对齐包围框；仅支持正尺度与直角旋转，因此本支持域内框正逆可逆。

输入、输出和中间值必须有限。边界检查严格，不裁边、不用容差接纳越界。缩放结果的边界宽高须在浮点表示中恰为正整数；即使差值小于 `1e-9`，也拒绝非整数尺寸，不隐式修改尺度或取整。数值比对/手算测试容差为 `1e-9`，不扩张合法坐标域。浮点极端值、不可表示的逆矩阵被拒绝。反射、任意角度、透视、非线性变换和直接输入未说明语义的矩阵不属于支持域。

公共入口：`annotation.geometry.ImageBinding`、`OriginalBox`（均重用 C01 类型）、`Transform`、`GeometryError`、`invert_affine`。`forward_point` / `inverse_point`、`forward_box` / `inverse_box` 均要求显式图像绑定；处理图绑定通过 `processed_binding(asset_id,sha256)` 建立，摘要须由调用者对实际处理图计算。此模块不生成处理图像。

`a01-geometry-1` 是具名 A 内部语义提案 G01。C01 `CropTransform` 缺少偏移域、补边次序和旋转定义；`from_contract_crop_transform` 显式拒绝自动解释。A04 只能在主调度接受并释放确切版本后按此具名规范消费，不应复制变换实现。

## 静态来源

入口：`annotation.source.static.import_book(repo_root, book_id, destination, revision=1, previous=None)`；`load_static_bundle(path, expected_book_id=...)` 在公共 `load_bundle` 资源校验之外执行完整图像解码与来源交叉核对。消费无需仓库原件、网络或凭据。依赖已安装 Pillow 11.3.0；根依赖未修改，打包依赖声明需主调度单独整合。

输出新目录，已存在目标一律拒绝，原资料目录也禁止作为输出位置。资产身份为书籍 ID 加图像完整摘要；原件不改写。目录身份绑定书籍及外部目录 ID 摘要；历史题目引用身份绑定书籍、归档摘要及记录位置，独立于印刷题号和平台题序；源归档变化会得到新引用，不能宣称已匹配旧实体。新修订必须显式提供上版交换文件并递增 revision，在摘要保护的 provenance 记录前版身份及交换文件摘要。C01 禁止 SourceBundle 根使用 input_refs，因此保持空 input_refs，前版是归档依赖记录，不伪造公共引用；旧版不覆盖。

旧书取得六个不同原图，四张归档副本按摘要去重但保留十条来源关系。只确认 viewer 8/9/10/234→source 7/8/9/233；另外 source 10/234 的 viewer、所有印刷页码均未知。新书取得两图，review/execution 两份副本保留四条关系，确认 viewer14/173→source13/172。资产挂在具名书级容器目录下，不猜实际章节；实际目录树另行保留。

`provenance.json` 记录相对原始位置、清单摘要、映射、历史观察时间、缺页和缺失来源。带绝对路径的原清单留在原仓库，只生成脱敏投影，不复制个人路径。目录、标注和导出等安全原件逐字节拷贝到 history，始终 UNVERIFIED；历史越界单列且不变成 OriginalBox。旧派生错误映射的更正原件一并保留，不重新运行 OCR 或映射推断。

expected 明确选择本次六页/两页，acquired 与实际资产一致；本范围缺页为零。250/214 仅为元数据总量，其余244/212源索引列为未取得，不能称本次范围内缺图。缺失四份原始 JSON 和五条不可用外机来源保留为独立限制，不拿脱敏副本冒充原件。

## 完整性限制与最小合同提案 S01

两包 `scope_manifest` 仅为**参考记录清单**：旧书14行历史导出，新书 A05 单条目录记录。`scope_manifest_basis` 与 `limitations.json` 声明它们不是整页/全书独立题目分母；来源消费者始终输出 `coverage_eligible=false`，不生成 CheckReport/PASS，不提供完整性或识别质量结论。

C01 强制非空 scope_manifest，且下游把它称为独立分母，无法机器表达独立分母未知和缺失来源。最小失败样例是 SourceBundle 的 `scope_manifest=[]`，公共 API 拒绝。提案 S01：由合同唯一负责人在新版本增加 `scope_manifest_status=UNKNOWN|REFERENCE_ONLY|INDEPENDENT_COMPLETE`、允许 UNKNOWN 空清单，增加结构化 missing_sources；PRE_APPLY PASS 要求 INDEPENDENT_COMPLETE。现有包保留文本限制，**不可直接用于自动放行**；需迁移或先建立独立分母。未修改 C01，也不把本提案视作双方接受。

最短复现及真实结果见 [执行报告](tasks/A01-execution-report.md)。本任务没有浏览器、网络、OCR、模型或平台动作；不证明 A05 内容正确、全书采集或 B 已确认。
