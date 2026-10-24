# 46007447 第一章 Q16 与三个阅读任务来源内容复核

日期：2026-10-21（Asia/Shanghai）
复核性质：第二模型直接来源核查；**不是独立人工验收**
技术结论：在本次明确范围内未发现候选内容与可见原图像素之间的实质差异
业务结论：**HOLD**

## 1. 输入身份与停止门

摘要停止门通过后才继续内容核查：

|对象|实际 SHA-256|预期 SHA-256|结果|
|---|---|---|---|
|`B-46007447-Q16-reading-C01-HOLD-2026-10-21.zip`|`f96b59dc0bccb171eb43daa03a47478d44452bc1d8eb3e2fffb4800f517c7a93`|同左|MATCH|
|`delivery/bundle.json`|`e347e6eef8a87a60bcf314816a0b5ff7a9f3cf24b60109891f844d998fd5e39d`|同左|MATCH|

共享仓库只读 HEAD 为 `d48b066ad2620d7f1a2e902b2b28e3139390a721`。本会话未修改共享仓库，未提交或推送。

其余直接核对文件：

- `SOURCE-REVIEW.md`: `d7535473368385bcf5ae9077e97fe9edbd9bff6490199302c4bc44d5969161ed`
- `delivery/current-review.json`: `4dd4425140620ef37a289df29206c2f04734c082badd2c73b238851d8031cada`
- `delivery/delivery.json`: `d137e66e975d1ecf531c95977c10e701abf6c1a42ba63c4cb32e2887184a13b3`

`delivery.json.current_review_sha256` 与实际 `current-review.json` 摘要一致。

## 2. 核查方法与证据等级

我直接查看了以下三幅原图，而没有把旧 OCR、`current-review.json` 或 `delivery.json` 当作 gold：

- `viewer-15.jpg`，1219×1703，SHA `7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd`
- `viewer-173.jpg`，1148×1621，SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`
- `viewer-13.jpg`，1219×1691，SHA `997b37d35fca57f73ab71e53f6721be145d10c436deab5fab38bf1ae0d31dc1e`

先查看完整原图，再按候选坐标查看题块、答案行、公式槽和图形。另从原始 JPEG 重新裁切并逐像素比较候选裁片：Q16 题块、11 个公式槽、阅读共享材料块、三个任务题块及答案/图形共 **34/34** 个窗口完全一致。

这只能证明“候选窗口确实来自这些原图字节”和本模型的视觉读法；不能替代独立人工内容验收，也不能批准平台分框策略。

## 3. Q16 核对

### 3.1 题面、三小问与空值

|内容|原图坐标（viewer-15）|核查结果|
|---|---|---|
|题干及数列|`[627,120,1142,348]`|MATCH；“勾三、股四、弦五”，数列 `3,4,5; 5,12,13; 7,24,25; 9,40,41…`，勾为奇数且从 3 起无间断。装饰 `A` 可见，但不是选项。|
|小问（1）|`[665,350,1140,430]`|MATCH；`11` 后两个答案线均为空，两个 blank 的 `value` 均为 `null`。|
|小问（2）|`[665,432,1140,779]`|MATCH；`a` 为奇数且 `a≥3`；`4=(3²-1)/2`、`12=(5²-1)/2`、`24=(7²-1)/2`、第二个数 `(a²-1)/2` 均可见；第三个数答案线为空且 `value=null`。|
|小问（3）|`[665,780,1140,855]`|MATCH；要求说明（2）中三个数为勾股数，无额外 blank。|

候选对题面空值的处理正确：未用答案倒填三条题面横线。

### 3.2 11 个分式槽

逐一查看 `viewer-173` 右上 Q16 答案的 11 个分式窗口：

|槽|原图坐标|候选 LaTeX|第二模型核对|
|---|---|---|---|
|F1|`[765,268,802,294]`|`\frac{a^{2}+1}{2}`|MATCH|
|F2|`[917,267,954,295]`|`\frac{a^{2}-1}{2}`|MATCH|
|F3|`[994,269,1070,296]`|`\frac{a^{4}+2a^{2}+1}{4}`|MATCH|
|F4|`[619,301,656,329]`|`\frac{a^{2}+1}{2}`|MATCH|
|F5|`[686,301,761,329]`|`\frac{a^{4}+2a^{2}+1}{4}`|MATCH|
|F6|`[823,302,861,330]`|`\frac{a^{2}-1}{2}`|MATCH|
|F7|`[900,303,938,330]`|`\frac{a^{2}+1}{2}`|MATCH|
|F8|`[681,338,718,364]`|`\frac{a^{2}-1}{2}`|MATCH|
|F9|`[727,337,764,364]`|`\frac{a^{2}+1}{2}`|MATCH|
|F10|`[884,339,922,365]`|`\frac{a^{2}-1}{2}`|MATCH|
|F11|`[930,339,969,365]`|`\frac{a^{2}+1}{2}`|MATCH|

每个窗口的分子、分母、分数线、平方或四次方上标均与候选一致，未见 `+1/-1`、分母 `2/4` 或指数混淆。

### 3.3 外围符号与三小问配答

Q16 答案三行原图窗口为：

- `[579,263,1084,299]`：`（1）60 61`、`（2）(a²+1)/2`，随后 `（3）∵a²+((a²-1)/2)²=(a⁴+2a²+1)/4，`
- `[579,299,1084,334]`：`((a²+1)/2)²=(a⁴+2a²+1)/4，∴...`，并有 `又∵a为奇数，且`
- `[579,334,1084,367]`：`a≥3，∴...都是正整数。∴...是勾股数。`

可见的 `∵`、`∴`、括号外平方、`又∵`、奇数条件和 `a≥3` 均被候选保留。`delivery.json` 的映射 span 实际切片为：

|任务|映射内容|结果|
|---|---|---|
|`q16-task1`|`（1）60 61`|MATCH|
|`q16-task2`|`（2）\frac{a^{2}+1}{2}`|MATCH|
|`q16-task3`|三行完整证明，含全部 11 个分式及外围条件|MATCH|

未发现跨小问串接、漏行或将题面 null 横线提前填值的问题。

## 4. 阅读共享材料核对

`viewer-13` 中共享材料从标题到“任务”完整可见。标题、导语、赵爽方法、图 1、达·芬奇方法、图 2 及三个任务均与 `current-review.json` / `SOURCE-REVIEW.md` 一致：

- 标题 `[275,553,930,598]`：`漫话勾股世界——教材P6“阅读·思考”变式`。
- 图 1 `[431,838,573,1000]`：ABDE、CFGH 及 `a,b,c` 标签可见。
- 图 2 `[137,1177,504,1335]`：剪开、右边部分上下翻转及两侧图完整。
- 共享材料说明的 `S₁`、`S₂` 含义与候选一致。

未见材料身份串到上方隧道题或其他章页。

## 5. 三个阅读任务与答案

|任务|题面原图坐标（viewer-13）|答案原图坐标（viewer-173）|逐内容结果|
|---|---|---|---|
|任务（1）|左栏 `[56,1393,582,1596]`；同页跨栏续文 `[655,617,1140,807]`|`[54,1012,282,1044]`|MATCH。面积等式为 `S正方形ABDE=4S△ABC+S正方形CFGH`；三空顺序为 CFGH 边长、△ABC 面积、CFGH 面积。答案依次 `a-b`、`\frac{1}{2}ab`、`(a-b)^2`。|
|任务（2）|`[621,810,1140,890]`|`[282,1012,548,1044]`、`[54,1044,548,1084]`、`[54,1084,228,1104]`|MATCH。完整推导保留 `S_1=a²+b²+2×1/2ab=a²+b²+ab`、`S_2=c²+2×1/2ab=c²+ab`、`∵S_1=S_2`、消去 `ab` 后得到 `a²+b²=c²`。|
|任务（3）|`[621,1135,1140,1378]`|恒等式 `[228,1084,548,1104]`；括注续行 `[54,1104,154,1124]`；图 `[225,1118,372,1240]`|MATCH。恒等式为 `(a+b)^2=a^2+2ab+b^2`；`（答案不唯一）` 虽跨行但重组正确；图中外正方形、内分割线及上下/左右 `a,b` 标签均可见，候选框未见可见内容截断。|

任务（1）的三项 `blank_responses` 顺序正确；任务（2）和（3）本身不是填空题，`blank_responses=[]` 正确。

## 6. 差异表与修订建议

|核查项|差异|处置|
|---|---|---|
|Q16 题面、答案、11 分式、外围符号、任务映射|null|无需内容修订；保持 `MODEL_SOURCE_CANDIDATE` / HOLD。|
|阅读共享材料、图 1/图 2|null|无需内容修订；来源窗口不等于平台框。|
|阅读任务（1）跨栏、三空及答案顺序|null|无需内容修订。|
|阅读任务（2）完整 `S_1/S_2` 推导|null|无需内容修订。|
|阅读任务（3）恒等式、括注、整图|null|无需内容修订；图形精确平台边界仍未获人工批准。|
|中文标点、空格、换行、LaTeX 上下标|存在呈现规范化，不构成来源冲突|继续保留候选中的 normalization 声明；不能称逐字编码人工签核。|

本轮没有足够图证支持任何修订建议，因此不提供内容补丁。若后续人工发现标点编码、空格宽度或平台分框政策差异，应新增独立修订，而不是把本模型的 MATCH 升级为人工确认。

## 7. 实际命令和工具操作

实际摘要与 HEAD 命令：

```powershell
$repo='C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant'
$zip=Join-Path $repo 'handoffs\b\46007447\B-46007447-Q16-reading-C01-HOLD-2026-10-21.zip'
$ex='C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\q16-reading-handoff-20261021\final-extracted-v2'
Get-FileHash -Algorithm SHA256 -LiteralPath $zip,(Join-Path $ex 'delivery\bundle.json')
git -C $repo rev-parse HEAD
Get-FileHash -Algorithm SHA256 -LiteralPath @(
  (Join-Path $ex 'SOURCE-REVIEW.md'),
  (Join-Path $ex 'delivery\current-review.json'),
  (Join-Path $ex 'delivery\delivery.json'),
  (Join-Path $ex 'delivery\assets\viewer-13.jpg'),
  (Join-Path $ex 'delivery\assets\viewer-15.jpg'),
  (Join-Path $ex 'delivery\assets\viewer-173.jpg')
)
```

实际使用本地图片查看器以 `original` 细节级别打开三幅原始 JPEG，以及 Q16 题块、三行答案、F1–F11、阅读题面/答案/图形裁片。未调用 OCR。

逐像素来源复核实际执行了以下逻辑（Python 3，Pillow；只读，无 OCR）：

```python
root = Path(r'C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\q16-reading-handoff-20261021\final-extracted-v2\delivery')
review = json.loads((root / 'current-review.json').read_text(encoding='utf-8'))
delivery = json.loads((root / 'delivery.json').read_text(encoding='utf-8'))
images = {name: Image.open(root / 'assets' / f'{name}.jpg').convert('RGB')
          for name in ('viewer-13', 'viewer-15', 'viewer-173')}
rgb_hash = lambda image, bbox: hashlib.sha256(image.crop(tuple(bbox)).tobytes()).hexdigest()
# 实际逐项比较：4 个 Q16 题块、11 个 Q16 公式槽、8 个阅读材料块、
# 4 个阅读任务题块和 7 个阅读答案/图形窗口；结果 34/34。
```

另实际读取 `delivery.json.q16_task_map`，用其 `text_span` 切片 `current-review.json` 三行 Q16 答案，结果见第 3.3 节。

## 8. 结论边界

- **模型目视来源核查**：本次范围内 MATCH；未发现需修订的内容差异。
- **结构/字节检查**：ZIP、bundle、三幅原图和 current-review 绑定摘要一致；34/34 来源窗口逐像素一致。
- **独立人工验收**：未进行，不能声称通过。
- **A 自行接收或业务验收**：未进行，不能声称通过。
- 网站请求、标注写入、OCR、付费模型调用、平台动作：均为 0。
- 章节完整分母仍未知，结论只覆盖包内 Q16 与三个阅读任务。

最终状态：**HOLD**。
