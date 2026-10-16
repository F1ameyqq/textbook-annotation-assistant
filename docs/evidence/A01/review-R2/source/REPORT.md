# A01 R2 来源子复验

子结论：**REWORK**。R2-03 观察索引绑定在本次有界检查中为 **ACCEPTED**；R2-02 的固定反例已拒绝，但 URL 查询/片段可掩盖真实路径中的书籍或源索引矛盾，仍为 **REWORK**。R2-01 的广泛分区矩阵由另一验收子任务负责；本子任务只复放其固定 P01。

固定交付 `c3aff9598b6705ab4122062615a13ae3774698b2`；实现 `63ac5a184798326d629a43d1dfed25fa73a1a27e`。使用父代理已按 974 Git blob 校验的 `D:/1800/.local/stages/A01-review-R2/c3aff9598b6705ab4122062615a13ae3774698b2/snapshot`，实际导入的 importer/consistency/contracts 路径及摘要见 [environment.json](environment.json)。`-B`、`sys.path[0]`、`PYTHONPATH` 均固定；CPython 3.9.13、Pillow 11.3.0、Pydantic 2.12.5。未使用其他 editable 实现。

## 实际命令与结果

实际工作目录 `D:/1800`，以下主命令退出 **0**。退出 0 仅表示取证脚本跑完，不代表被验功能通过。重跑时须使用不存在的新 stage 名：

```powershell
python -B D:/1800/docs/evidence/A01/review-R2/source/probe.py --snapshot D:/1800/.local/stages/A01-review-R2/c3aff9598b6705ab4122062615a13ae3774698b2/snapshot --stage C:/Users/ASUS/AppData/Local/Temp/A01-review-R2-c3aff959-__n2y2in/source/run-01
```

TMP/TEMP/TMPDIR 全部设为上述独占 stage，所有包输出都在普通系统临时目录；新证据只写 `docs/evidence/A01/review-R2/source/`。未改源码、合同、依赖、调度状态或旧材料，未集成或释放 A04。

独立构造 **50 项**，全部先实际通过 `load_bundle(..., verify_assets=True)` 的公共资源/摘要校验，然后调用 A01 加载器。47 项符合预期，3 项不符合预期；实际为 34 拒绝、16 接受，其中 3 个接受为残余失败。逐项输入、资源变更摘要、URL 解析组件、公共加载结果、code/location/异常栈与原始日志见 [results.json](results.json)、[stdout.txt](stdout.txt) 及 `cases/<ID>/`。

| 检查组 | 结果 |
| --- | --- |
| legacy / R1 / R2 两书六个冻结正常包 | 6/6 接受；直接读冻结样例，未重建或重写 |
| R1 P01–P04 确切整包 | 4/4 按预期定位拒绝；完整输入另存 `replay-inputs/`，复制包与旧证据逐文件摘要相同 |
| URL U01–U25 | 22/25 符合预期；U23–U25 错误接受 |
| 观察索引 O01–O15 | 15/15 符合预期 |

974 份冻结文件以及原 R1 正式反例目录前后摘要不变，见 [preservation.json](preservation.json)。这些新结果不覆盖原首轮/R1 的报告或证据。

## 冻结反例复放

| 原输入 | 公共加载 | A01 code | A01 location |
| --- | --- | --- | --- |
| P01-acquired-also-missing | ACCEPT | SCOPE_PARTITION | provenance.selected_missing_source_indices |
| P02-page-response-cross-book-url | ACCEPT | BOOK_CONFLICT | history.docs/evidence/A05/review/independent-source-page14.json.pages[0].image |
| P03-page-response-index-url-conflict | ACCEPT | MAPPING_CONFLICT | 同上 image |
| P04-observation-index-digest-conflict | ACCEPT | OBSERVATION_SOURCE | provenance.observation.observation_index_source.sha256 |

原输入来自 `D:/1800/docs/evidence/A01/review-R1/primary-source-confirmation/`。未运行其固定输出脚本，未更改原包；整包复制到新目录后重放，并保存独立的新输出。

## R2-02：路径绑定残余失败

U23–U25 均从冻结 R2 新书包完整复制，仅改历史响应 `image` 字符串的业务含义。`file_id=46007447`、响应 `page_index=13`、保留映射 source13 均未改。随后同步历史原件引用的 input-integrity before/after 与公共资源 SHA256，并用公共 `seal_artifact` 重新封装。因此三包均实际通过公共校验，且 `unchanged=true`、before=after；不是 HISTORY_BYTES 提前失败的无效反例。它们各有新内容身份，不冒认原冻结 artifact 摘要。

| ID | `urlsplit(image).path` | query / fragment 中的伪装尾部 | 预期 / 实际 |
| --- | --- | --- | --- |
| U23 | `/upload_images/46006966/46006966_page_13.jpg` | query=`ignored=/upload_images/46007447/46007447_page_13.jpg` | 应拒绝两处路径书籍与 file_id/本包冲突；公共/A01 均 ACCEPT |
| U24 | `/upload_images/46007447/46007447_page_172.jpg` | fragment=`/upload_images/46007447/46007447_page_13.jpg` | 应拒绝路径 source172 与响应/映射13冲突；公共/A01 均 ACCEPT |
| U25 | `/upload_images/46007447/46007447_page_172.jpg` | query=`ignored=/upload_images/46007447/46007447_page_13.jpg` | 同上，应拒绝；公共/A01 均 ACCEPT |

三项均用 `https://archive.example.invalid` 作为归档主机文本；没有发起任何请求。URL 的 path/query/fragment 是本地标准解析得到的不同组件，本反例不要求主机认证、外部真实性或网络信任。R2 文档声明“绝对 HTTP(S) 地址的目录书籍、文件名前缀书籍和源索引须与响应字段及保留映射一致”，当前路径已明确违反该声明。

根因定位：`src/annotation/source/static/importer.py:102–107` 用 urlsplit 检验 scheme/主机，但 **108 行仍在整个 `url` 原字符串上运行尾部正则**；最终得到 query/fragment 中伪装的 book/index。`consistency.py:240–243` 正确核对响应页索引与保留映射，却消费了这个错误的 URL 索引。故原直接路径错误能拒绝，带伪装尾部仍可通过。

最小复现选 U24：在仍声明 source13 的历史页14响应中，image 设为：

```text
https://archive.example.invalid/upload_images/46007447/46007447_page_172.jpg#/upload_images/46007447/46007447_page_13.jpg
```

完整变异包保留在本任务 stage 的 `U24-fragment-masks-wrong-path-index/bundle/`；证据目录 `cases/U24-fragment-masks-wrong-path-index/changed-inputs/` 保存历史 JSON、同步的 input-integrity 和 exchange。其余资产可直接取冻结 R2 新书包。每份新文件摘要和实际输出已纳入最终清单。

恢复条件限定在 R2-02：从真正 URL path 判定两处 book/index，不能让 query 或 fragment 提供或覆盖路径身份；保留现有合法直接 JPEG 地址及两书兼容。这里不要求新增一般 URL 功能或网络认证，也未修改实现。

其他 URL 邻近项已经符合预期：两处书籍标识单独/同时错误、source12/14/172、错误 JPEG 扩展、FTP/file/相对/无主机地址、非字符串 image 均被定位拒绝。raw page_index 为 True、13.0、字符串13 均报 MAPPING_CONFLICT；第二份 viewer173 历史响应的 source172 正常接受，错误 source13 被拒绝。HTTP、HTTPS、大小写 scheme，以及主机文本包含另一书籍 ID 但路径正确的直接 JPEG 地址正常接受；这仅证明主机字符串未被当作书籍真实性认证。

## R2-03：有界接受

`validate_observation_source` 在 `consistency.py:63–77` 检查 source 身份、观察索引字典/便携路径、新书指定索引路径、同路径在 input inventory 中存在、SHA256 格式以及与保留 before/after 摘要一致。

本次独立验证 P04 和 O01–O15：零摘要、空/错误类型索引、不存在路径、路径越界、非 SHA256/错误类型摘要、错误归档 source、索引 inventory 缺项、指向其他保留输入并带其正确摘要、使用其他输入摘要但保留网络索引路径，均定位拒绝。输入清单仅重新排序仍可接受；旧书没有强制 index 的正常包保持兼容，加入与其保留 session 输入一致的可选 index 接受，错误摘要拒绝。所有语义拒绝均先通过公共资源/摘要校验，非资源损坏冒充语义检查。

在这些已授权关系内未发现 R2-03 残余矛盾或正常六包误拒绝。此结论不证明归档索引的外部真实性；若全部相互保留记录被一致替换，无签名包仍不能自行认证来源。

## 范围限制

本子任务没有扩展 N15 precision 认证、S01 公共自动资格或 D01 根依赖，三者仍按已有边界记录；没有公共 coverage PASS、全书分母、平台、浏览器、凭据、网络、OCR 或模型动作。未重新安装依赖或验证文件 symlink、A04/CSS-DPR、识别/配答、B 确认。作者套件、资源搬运、完整分区矩阵和整体验收由父代理/其他子任务负责，不在这里代记通过。
