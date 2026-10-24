# A24 / 46007447 当前平台只读基线核验

日期：2026-10-22（Asia/Shanghai）
目标：book `46007447`，叶目录 `dir-1792063578574-g0n3ulsni`，仅一个普通选择题。
边界：网站与交接仓均只读；未登录、未编辑、未保存、未提交、未送审。

## 结论

1. **当前没有连上可供本会话使用的独立登录会话。** Edge 中存在三个登录页和一个旧 `/qieti/home` 页；旧主页已归属浏览会话 `01a1445e-2f9f-7c73-8a2a-1f16b0f341fb`，本会话的一次附着尝试被拒绝。按会话归属和认证停止规则，没有抢占、重新登录、创建新配置或重试。
2. 本轮由本会话实际产生的平台数据请求为 **0**，平台写入为 **0**。浏览器动作仅为标签清单读取和一次本地标签附着尝试；没有导航到书、目录、框或导出接口。因此本轮没有获得 2026-10-22 的当前 book/directory/frames/export 响应。
3. 本机的 A24 `selected` 交接树已完成独立文件系统校验：522/522 发布成员、111/111 `src` 文件和四个冻结子清单全部通过字节数与 SHA256 核对。`tree.json` 将该提取包绑定到固定发布树 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`，且 `truncated=false`、远端树条目数 15,632。
4. 上述 PASS 只证明**离线发布包完整**，不证明当前平台连通、当前网页内容、保存资格或页面可写。`selected` 本身不是 Git checkout，不能以 `git status/show` 验证提交图；固定提交号来自同批 `tree.json` 元数据。
5. A 侧 2026-10-21 的四个 HTTP 200 仍只能作为历史固定证据：book 4,186 bytes（仅长度/哈希，原 body 未保留）、directory 14,019、frames 46,219、natural export 11,625。后三份原始响应、候选、请求草案和六裁片都未发布进 Git；本机按交接给出的七个精确 D 盘路径逐项检查均不存在。没有进行全盘扫描，因此不得推断它们在整机不存在。
6. Chapter 1 的 Q9 来源缺口未变化：目标“☆问题解决策略：反思”的 `question_id=null`，固定六张题页未包含目标完整题干；只有 `viewer-173 → resource-173` 两张答案来源已核实。状态继续为 `PARTIAL/HOLD`。

## 旧证据与本轮新证据分界

| 类别 | 证据 | 能证明 | 不能证明 |
|---|---|---|---|
| A 侧旧实际轮 | actual final `d3c8abcf0c1fa89af123e4b242964f818f1a011c`；四个 GET 的长度和 SHA | 2026-10-21 有界采集曾返回 HTTP 200 | 2026-10-22 当前平台状态；完整 schema；保存资格；fresh readback |
| A 侧旧私有原件 | directory/frames/export 三原件及候选、草案、六裁片的 D 盘索引 | 原机若按索引取得，可离线分析真实响应 | 本机当前可读；Git 中已发布；当前网页等同旧响应 |
| 本轮新浏览器检查 | Edge 标签清单；旧主页附着被会话所有权拒绝 | 当前没有可附着的独立已登录标签 | 网站下线；账号无效；书或目录不存在 |
| 本轮新离线校验 | 522/522 成员、111/111 `src`、4/4 冻结清单通过 | `selected` 提取树与发布清单一致 | 平台当前内容；历史私有原件正文；全 frames 完整性 |

## 固定旧响应记录（未在本轮重新取得）

| 响应 | 字节 | SHA256 | 本机原始 body |
|---|---:|---|---|
| book | 4,186 | `5cb2c703…` | 未保留（A 侧原轮也仅保留长度/哈希） |
| directory | 14,019 | `724059d435270a50c40e56a9de31970bbd08ed426a44c147eaf9ea028e6de34d` | 未取得 |
| frames | 46,219 | `6c3fad1aeee1d20623c9f4d3d4baef3981713cd6cfa775242f71a03bfcb0fdab` | 未取得 |
| natural export | 11,625 | `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c` | 未取得 |

`page-visible` 不能替代 `full-frames` 原始响应及其字节级完整性证明；本轮没有把页面可见状态表述成全框完整。

## 本轮离线校验结果

- 选择发布清单：`A24BSelectivePublication/v1`。
- 分支元数据：`codex/a24-b-takeover-20261021`；parent `edf125961be9cdc1642652c038d99872b1c8cdc7`；author source `aeb830aacdd333265451082dd2071751c1c00903`。
- 主成员：声明 522，观察 522，缺失/哈希不符 0。
- `src`：声明 111，观察 111，缺失 0，额外 0。
- 冻结清单：321、26、20、11 个成员分别全部通过；四个清单自身 SHA256 也通过。
- 交接声明保持：`private_raw_bytes_published=false`，`old_evidence_not_rewritten=true`。

复核脚本：`outputs/verify_a24_selected_tree.py`。脚本只读取发布清单及其声明成员，不访问网站、不修改交接树。

## 恢复条件

要建立真正的“当前平台基线”，需满足以下任一条件：

1. 用户在一个**未被其他自动化会话占用**的独立 Edge 标签中完成登录，并保持该标签打开在目标平台；本会话再按只读边界读取 book/directory/frames/natural export，保存新日期原始字节并计算 SHA256；或
2. 从 D 盘原机受控转交三份旧原始响应、候选、请求草案和六裁片，并附精确字节数/SHA256 清单。该路径只能恢复 2026-10-21 旧基线，不能替代 fresh 平台读取；或
3. 用户直接提供目标 Q9 完整题页/相邻页原图或 PDF，以闭合 Chapter 1 的具体来源缺口。

即使只读会话恢复，也不会自动获得保存授权。A 侧旧 authority、activation、profile、lock、预算和线程 ID 均不复用；实际保存、refresh 和独立 reopen 仍是 `NOT_RUN`。

## 本轮操作计数

| 项目 | 数量 |
|---|---:|
| 平台数据 GET / 页面导航 | 0 |
| 平台写入 / 保存 / 提交 | 0 |
| 登录、凭据、Cookie、profile、lock 操作 | 0 |
| 浏览器标签清单读取 | 1 |
| 旧主页附着尝试 | 1（被会话所有权拒绝） |
| D 盘精确路径存在性检查 | 7（均不存在） |
| 离线发布成员校验 | 522（全部通过） |

最终状态：**LIVE_NOT_CONNECTED / OFFLINE_RELEASE_TREE_VERIFIED / PRIVATE_RAW_UNAVAILABLE_LOCAL / CHAPTER1_Q9_PARTIAL_HOLD**。
