# A01 R1 来源独立复验子报告

来源子结论：**REWORK**。原 S12–S20 九项已修复；新增邻近场景仍可让有明确包内矛盾的来源包被 A01 加载器接受。本结论只覆盖来源加载一致性，不替代父代理的 A01 总结论或集成决定。

被验交付为 `03c1af41a134945c406a52a48e3d4f6f0da33eb2`，实现为 `0ee7e836e3bc1849f91840b4271d233bbd8e72dd`。使用已由父代理按全部 890 Git blob 校验的副本 `D:/1800/.local/stages/A01-review-R1/03c1af41a134945c406a52a48e3d4f6f0da33eb2/snapshot`，固定 `sys.path[0]` 与 `PYTHONPATH` 为该副本 `src`。实际 importer/consistency/contracts 文件位置、摘要、CPython 3.9.13 / Pillow 11.3.0 / Pydantic 2.12.5 环境见 [environment.json](environment.json)。

主反例脚本实际退出 0，仅表示完成取证，不表示被验功能全通过。32 项包括 4 个正常冻结包接受、22 个非法包拒绝、6 个邻近非法包接受；原九项均匹配预期错误码。另对 N17 做一次保持原 URL 主机名的最小化复跑，仍接受。主结果见 [results.json](results.json)、[stdout.txt](stdout.txt)，最小化结果见 [minimal-url/result.json](minimal-url/result.json)。

所有变异都是从**冻结提交内固定样例整包复制**，未重建或改写正常基准包；没有将重建基准当作冻结交付原字节。变异后的资源摘要和 artifact 摘要使用公开 API 重算，具有新内容身份，检验保留记录之间的一致性，不要求 unsigned bundle 自证外部真实性。全程离线；无网络、浏览器、凭据、OCR、模型或平台动作。

## 命令与隔离

实际工作目录 `D:/1800`。实际 stage 分别为：

- 主反例：`C:/Users/ASUS/AppData/Local/Temp/A01-review-R1-03c1af41-v5hlrfgb/source/run-01`
- 最小化：`C:/Users/ASUS/AppData/Local/Temp/A01-review-R1-03c1af41-v5hlrfgb/source/minimized-url`

脚本同时把 TMP/TEMP/TMPDIR 固定到各自独占目录，并使用 `-B`。重跑时最后目录名必须换成尚不存在的新目录：

```powershell
python -B D:/1800/docs/evidence/A01/review-R1/source/probe.py --snapshot D:/1800/.local/stages/A01-review-R1/03c1af41a134945c406a52a48e3d4f6f0da33eb2/snapshot --stage C:/Users/ASUS/AppData/Local/Temp/A01-review-R1-03c1af41-v5hlrfgb/source/reproduce-main
python -B D:/1800/docs/evidence/A01/review-R1/source/minimal_url.py D:/1800/.local/stages/A01-review-R1/03c1af41a134945c406a52a48e3d4f6f0da33eb2/snapshot C:/Users/ASUS/AppData/Local/Temp/A01-review-R1-03c1af41-v5hlrfgb/source/reproduce-minimal
```

两命令均实际退出 0。新证据仅写 `docs/evidence/A01/review-R1/source/`；890 份冻结文件和四套正常固定包前后摘要不变，见 [snapshot-integrity.json](snapshot-integrity.json)。旧准备、正式报告与证据均未修改。

## 原九项复放与兼容性

| 原案例 | 实际 A01 错误码 | 实际定位 | 子项 |
| --- | --- | --- | --- |
| S12 origins 空 | SOURCE_ORIGINS | provenance.origins | ACCEPTED |
| S13 origin 清单摘要冲突 | SOURCE_MANIFEST | provenance.origins[0].manifest_sha256 | ACCEPTED |
| S14 无依据 printed_page | MAPPING_EVIDENCE | provenance.mappings[0].printed_page | ACCEPTED |
| S15 已知 missing_sources 删除 | MISSING_SOURCES | limitations.missing_sources | ACCEPTED |
| S16 unchanged=false/摘要冲突 | INPUT_CHANGED | input-integrity.unchanged | ACCEPTED |
| S17 历史书籍/原件字节矛盾 | HISTORY_BYTES | history/01-manual-annotations.json | ACCEPTED |
| S18 升格 REVIEWED | HISTORY_QUALITY | history[0].quality | ACCEPTED |
| S19 COMPLETE/UNKNOWN 矛盾 | DENOMINATOR_UNKNOWN | limitations.scope_manifest_status | ACCEPTED |
| S20 参考 ID 矛盾 | REFERENCE_RECORDS | provenance.reference_records | ACCEPTED |

九项全部先通过公共 `load_bundle(..., verify_assets=True)`，然后由 R1 A01 加载边界拒绝；逐项输入、公开加载结果、错误栈保存在 `cases/S12-*` 至 `cases/S20-*`。

冻结 `examples/a01/bundles/` 旧格式与 `examples/a01/R1/bundles/` 新格式中的 46006966、46007447 共四包均正常接受。未发现这四个既有合法包被误拒绝。其他邻近校验也实际拒绝：单个 origin 丢失/重复、清单与 input inventory 摘要冲突、所需 history inventory 缺项、unchanged=true 但前后摘要不同、目录投影冲突、历史越界清单擦除、workspace 摘要冲突、参考位置冲突、历史日期冲突、新书响应 page_index/book_id 矛盾，以及历史总页数与来源总页数冲突（N01–N12、N19）。

## 仍接受的包内矛盾

| ID | 最小语义变化与保留矛盾 | 实际 | 对应代码缺口 |
| --- | --- | --- | --- |
| N13 | 旧书 source7 的图像/映射/selected_source_indices 均保留已取得，另写 `selected_missing_source_indices=[7]` | 公共/A01 ACCEPT | importer.py:445–448 核对 acquired 和 selected，却未核对 selected_missing；consistency.py 未读取该字段 |
| N14 | 在 `outside_selected_scope_unacquired_indices` 原列表追加已选择、已取得的 source7 | 公共/A01 ACCEPT；已取得 6 + 外部未取得 245 = 251，超过元数据 250 且集合相交 | 同上；未验证分区、不相交或补集 |
| N15 | 旧书观察记录仍只有历史 session 日期，`precision=LIVE_OBSERVATION` | 公共/A01 ACCEPT | consistency.py:161 只核对 date，未约束 precision；本例作为较低风险标签缺口，不单独支撑 REWORK |
| N16 | 新书历史响应 `file_id=46007447`、page_index13 不变，但 image URL 路径为书46006966 | 公共/A01 ACCEPT | consistency.py:175–179 只核对 file_id 和 page_index，未核对 URL 自带书籍 ID |
| N17 | 新书同一历史响应 `page_index=13`，image URL 却声明 `_page_172.jpg`；provenance/source mapping 仍为13 | 公共/A01 ACCEPT | 同上，未检验历史响应自身 image URL/source_index 一致性 |
| N18 | `provenance.observation.observation_index_source.sha256` 改全零；同 archive_path 的 input-integrity before/after 仍保留原真摘要 | 公共/A01 ACCEPT | consistency.py:186 只核对 archive boundary，未交叉核对观察索引来源摘要 |

N13、N14、N18 不涉及改动历史字节，一个侧车字段即可造成保留记录之间的矛盾。N16/N17 为了真正到达历史语义校验，同时将修改后的历史文件摘要写入对应 `input-integrity` before/after 和资源引用；两份摘要保持相等，`unchanged=true`。因此不是只改历史文件而被 HISTORY_BYTES 提前阻挡的伪反例，也不是替换所有来源记录的自洽伪造。矛盾留在同一历史响应或相互保留的索引记录中，不需要访问网络/原仓库来判定。

最小化 N17 保持原官方主机名，仅将 `history/00-independent-source-page14.json` 的 image 字符串尾部 `_page_13.jpg` 改为 `_page_172.jpg`，其余业务字段不动；重算关联摘要后仍接受。`importer.py:96–101` 已有纯字符串 `url_index` 检查，首次导入在 prepare 阶段使用它，R1 历史加载侧遗漏等价一致性检查。此处引用 URL 只是本地文本解析，不代表真实网络访问或网站行为。

建议优先最小复现 N18（一个摘要声明与保留 inventory 直接冲突）及最小化 N17（同一响应 image URL 与 page_index 直接冲突）。恢复条件是执行者补齐对应加载一致性检查，保留四个正常旧/新包兼容性，并复跑原九项与这些相邻反例；本验收未改实现或合同。

## 未解决范围

S01 公共完整性/PRE_APPLY 门禁与 D01 根 Pillow 依赖声明继续属于已知未解决的集成限制；本次来源修复没有使它们通过，也未再次构造公共 PASS。没有做全新安装、Windows 文件 symlink 分支、A04/CSS-DPR、算法质量、独立全页/全书分母或平台验证。作者套件、两书搬运及原件保全由父代理另验。未集成、未释放 A04、未修改调度状态。
