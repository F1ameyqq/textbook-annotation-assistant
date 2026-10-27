# A 提交层契约速查（pageRun.mjs / lib.mjs / config.mjs / config.example.json）

> 只读这 4 个文件的静态结论。`restore()` 在 restorefn.mjs（未读），其行为以调用点为准，下文标 ⚠。

## 1. 入口与参数

`pageRun.mjs` 只导出 `main(coordFile, opts)`，无顶层执行（ego 每个 `-e` 是新进程）。调用：

```bash
ego-browser nodejs -e "const m=await import('file:///<目录>/pageRun.mjs'); await m.main('<目录>/pages/p33.json',{from:5})"
node -e "import('./pageRun.mjs').then(m=>m.main('pages/p33.json',{dry:true}))"   # dry 不需要 ego
```

| 参数 | 默认 | 含义 |
|---|---|---|
| `coordFile` | 必填 | 一页一个坐标 JSON；纯数组，或 `{qPage,aPage,_check,items:[...]}` |
| `opts.from` / `opts.to` | `items[0].n` / `items.at(-1).n` | 只跑 n 落在区间的题（续跑靠它，无断点文件） |
| `opts.dry` | false | 只解析+打印计划与 `_check`，不碰浏览器（pageRun:56-68） |
| `opts.fileId` | `P.fileId` | 回读用书号 |
| `opts.noCheck` | false | 跳过服务端回读 |
| `opts.qPage` / `opts.aPage` | 28 / 174 | 传给 `restore({qPage,aPage})`；坐标 JSON 顶层同名可覆盖 |

| item 字段 | 说明 |
|---|---|
| `n` | 题号，用于区间过滤与日志，不直接下发平台 |
| `type` | 题型，逐字匹配下拉项文本（无独立类型 JSON，类型是 item 字段） |
| `q` / `w` / `a` | box 数组，`[x1,y1,x2,y2]` 源图像素；题目区 1220×1693、答案区 1145×1620 |

读取文件仅两处：坐标 JSON（pageRun:45）+ `config.json`（config.mjs:9-16，缺失即抛错，不入库）。

## 2. 一次提交流程（每题一轮，pageRun:73-92 → lib.run）

| # | 动作 | 函数 / 行号 | 等待/判据信号 |
|---|---|---|---|
| 0 | 加载配置 | `config.mjs` 9-21 | `config.json` 存在且 `url/fileId/dirNode` 非空 |
| 1 | 恢复页面到新建态 | ⚠ `restore({qPage,aPage})` pageRun:77 | 返回 `ctx.cur`（当前题目号） |
| 2 | 取 task space / page | `taskSpace(P.taskSpace)`→`task.page(P.page)` lib:9-10 | 无信号，ego 内建 |
| 3 | 快照 | `st()` lib:15-38 | `canvas.pdf-canvas` 矩形≥2；按钮中心点；正文 regex `题目框 N 答案 N 选项 N 解析 N 知识点 N`、`当前题目[:：] N` |
| 4 | 两道前置闸门 | lib:94-97 | `s.cur == expectCur`；counts 全 0（有残留框即中止） |
| 5 | 装 XHR 钩子 | lib:102-115 | 抓 `batch-ocr-task` 与 `commit_unified_submit` 的 req/resp 到 `window.__cap2` |
| 6 | 画题框 | `clk("题目(Q)")`→`drag(gq,·)` lib:117-121 | 每框 move 200ms / down 200ms / move 16 步 / 250ms / up / 800ms |
| 7 | 画选项框 | `clk("选项(W)")`→drag lib:122-126 | 同上；选项框画在题目 canvas 上 |
| 8 | 画答案框 | 点答案 canvas(350,620)→`clk("答案(A)")`→1600ms→drag lib:127-133 | 同上（先点 canvas 激活答案区） |
| 9 | 计数校验 | lib:136-139 | `counts.question/choice/answer` 精确等于框数 |
| 10 | 选题型 | 点首个可见 `.el-select`→下拉项 `mousedown/mouseup/click` lib:141-157 | 800ms / 600ms，无回显校验 |
| 11 | 一键识别 | `clk("一键识别")`→轮询 lib:160-167 | `__cap2.ocr` 出现，40×500ms=20s |
| 12 | 归属闸门 | lib:169-186 | OCR `results[].question_order` 去重后必须唯一且 == 期望；不符重试 1 次，仍不符 throw |
| 13 | 提交 | `clk("提交修改")`→轮询 lib:190-197 | `__cap2.commit` 出现，≤20s |
| 14 | 提交校验 | lib:199-212 | `data.inserted === true` 且 `data.question_order == order` |
| 15 | 服务端回读 | `readback()` pageRun:21-41,98 | `page.fetch /qieti/api/annotate_pic/get_manual_annotations_unified/{fileId}`，按 order 聚合 q/w/a 三类计数与 want 逐项比 |

## 3. 安全检查：已内置 / 缺口

| 已内置 | 位置 |
|---|---|
| config 必填字段校验 | config.mjs:20-21 |
| 坐标文件非空、n 区间非空 | pageRun:47,54 |
| dry run（含 `_check` 几何自检告警透传） | pageRun:56-68 |
| 期望题号闸门（防页面加载了别的题） | lib:94-95 |
| 画框前残留框拒绝 | lib:96-97 |
| 画框后 counts 精确校验 | lib:136-139 |
| OCR order 归属闸门（防上一题缓存结果） | lib:174-186 |
| 提交结果 `inserted===true` + order 校验 | lib:211-212 |
| 服务端回读 counts 比对 | pageRun:94-114 |
| 首错即 break，不带病跑下一题 | lib:86-91 |

| 缺口 | 后果 |
|---|---|
| **无「画框模式已进入」直接断言**：`clk()` 只判按钮存在（lib:59-64），不读 active/选中态 | 只靠 counts 事后兜底；一旦漏点/误点，报错定位差；框跨 canvas 归错 zone 但数量巧合相等时会漏到回读 |
| **目录跑掉无任何断言**：`pageRun` 不调 `syncDir`（lib:85），页码校验（lib:89-90）只在显式传 `qPage/aPage` 且 `sync` 时生效 | 整条 pageRun 路径完全信任 ⚠ `restore()`，自身不验证目录节点/页码 |
| OCR 结果只验归属，不验 zone 数 == 框数、不验 OCR 文本非空 | 少框/空识别仍可提交成功，脏数据入库后回读才暴露 |
| 无坐标 schema 校验（box 长度 4、n 重复/跳号、type 枚举、坐标越界） | 坏坐标变成运行时「no button / counts bad」，非启动期失败 |
| 提交无幂等键；响应丢失（20s 超时）即抛错 | 实际已入库却被判失败，重跑会重复插入 |
| 无失败现场截图 / DOM dump / 日志文件 | `failed[]` 只在 stdout 的 RESULT 行 |
| `_check` 几何自检只在 dry 打印，真实跑不读 | 有警告也照提交 |
| counts 依赖中文文案 regex | 平台改版即静默 `counts=null`，跳过校验 |

## 4. 重试 / 恢复

- 逐题 `try/catch`，首个异常 `break`（lib:86-91）→ **提交失败即中止整页**，后续题不再提交，已入库的题不回滚。
- 唯一自动重试：OCR order 不符重试 1 次（lib:174-184）；commit 无重试。
- 轮询上限 20s（40×500ms），超时按失败处理；`restore` 失败也直接 break。
- 恢复手段全靠人工参数：`from/to` 续跑 + 每题全量 `restore`（设计约束 #1）；`noCheck` 可跳回读，`dry` 先看计划。
- 无断点文件、无自动续跑、无事务/幂等，重跑边界需人工按回读结果判断。

## 5. ego 依赖点（换 playwright 的改动面）

| ego 专有 API | 位置 | playwright 替换 |
|---|---|---|
| `taskSpace(name)`（全局） | pageRun.mjs:22；lib.mjs:9 | 删掉，直接持有 `page`（或 `browser.contexts()[0]`） |
| `task.page(name)` | pageRun.mjs:23；lib.mjs:10 | `context.pages().find(p=>...)` 或注入 `page` 参数 |
| `page.fetch(url,{headers,timeout})` | pageRun.mjs:25 | `context.request.get(url,{headers,timeout})`，或 `page.evaluate(()=>fetch(...))` |
| `page.evaluate` / `page.mouse.*` / `waitForTimeout` | lib 多处 | 与 playwright 同形，保留 |

需重写的函数只有 **2 个**：`readback()`（pageRun.mjs:21-41，含 fetch 与取 token）整体换实现；`run()` 仅改 lib.mjs:9-10 两行取页头（`run(conf)` 改为 `run(page, conf)`）。其余 evaluate/mouse 代码零改动。⚠ 第三个 ego 点是 `restore()`（restorefn.mjs，未读）。`window.__cap2` XHR 钩子在页面侧，playwright 同样可用。

## 6. config 字段（config.example.json）

| 字段 | 示例 | 含义 | 必须 |
|---|---|---|---|
| `platform.url` | https://qt.lingshubao.cn/qieti/annotateUnified | 平台地址；本 4 文件未直接引用（restore/run_ego 用） | ✅ 校验 |
| `platform.fileId` | 46007447 | 回读接口路径参数，`opts.fileId` 可覆盖 | ✅ 校验 |
| `platform.dirNode` | 部分失败 64 插题 | `syncDir()` 按文本全等查找并点击的目录节点 | ✅ 校验（实际只走 sync 路径） |
| `platform.taskSpace` | usense2 | `taskSpace()` 参数 | ⚠ 未校验但运行必需 |
| `platform.page` | p1 | `task.page()` 参数 | ⚠ 未校验但运行必需 |
| `paths.srcDir` | srcpages | `SRC_DIR = HERE/srcDir`（导出常量，本 4 文件未用） | ❌ 默认 srcpages |
| `paths.egoExe` | "" | ego 可执行文件路径，供 run_ego.ps1 | ❌ 本 4 文件未用 |
| `_说明` | 复制为 config.json… | 纯注释字段 | ❌ |

`HERE` 为 config.mjs 所在目录；config.json 缺失/字段缺 → 启动即抛错（config.mjs:10-14,20-21），不会带着别人的书号跑。
