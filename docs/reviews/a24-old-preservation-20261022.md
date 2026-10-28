# A24 旧题保全链路独立审计（第一阶段）

## 结论

当前实现具备较完整的**条件性保全门**：只要输入确实是权威完整清单、全量旧题正文/框/目录的同一状态快照，`wire.py`、`quality/live_pilot.py` 与 runner 会把旧题逐对象冻结，并在 get、refresh、独立 reopen 三阶段相对保存前 baseline 检查不变。

但本机尚没有新鲜真实私有输入、权威导出路线资格、全量旧题分母和实际适配器观测，因此当前只能判为：

`HOLD_FRESH_PRIVATE_DENOMINATOR_AND_LIVE_ADAPTER_EVIDENCE_MISSING`

不能把旧的“22 题/68 框”、网页肉眼可见、JSON 行数或文件名当成完整性证明；也不能据此声称旧题已经实际保全。

## 支持 / 未证明矩阵

| 维度 | 代码中已支持的门 | 仍未由当前真实证据证明 | 当前判定 |
|---|---|---|---|
| 五区正文 | 导出要求每个旧题恰有 `question/choice/answer/analysis/knowledge_point` 五个键；保存前检查所有旧题五区键；保存后旧 `question_content` 逐项相等；新题三段提交并把 analysis、knowledge point 明确限定为新题空区操作 | 尚无当前权威全量导出与路线资格；只检查值为字符串或 `null`，不证明每区业务语义、非空性或服务端路线确实覆盖全书 | 条件支持，真实分母 HOLD |
| info / meta | `question_info` 必须存在且为字典；完整导出保留整条 `raw_record`，自然导出保留整条记录哈希；保存后旧正文对象（含 info/meta 保留项）严格相等 | 标准字段映射只显式抽取固定字段；“所有业务字段已覆盖”依赖外部 route qualification；当前没有真实 qualification 与原始响应证据 | 条件支持，字段完备性 HOLD |
| frames | 快照声明 complete/read OK；题 ID、框 ID 唯一；框必须关联现有题；导出 `rect_ids` 必须逐题等于快照实际框集合；保存后旧框字典逐项相等，只允许新增题所属框 | `complete`、框字段映射和实际响应路线尚未由新鲜私有证据校验；允许合法的零框旧题，代码不会凭常识补造框 | 条件支持，实际全量 HOLD |
| ID / order | 旧题 ID 与框 ID 唯一；旧题 order 为正整数且全局唯一；保存后旧题对象（含 ID/order）逐项相等；新回执必须给出新 ID、`inserted=true`、order 大于旧最大值 | 不要求 order 连续；“该字段确为平台全局顺序”的语义来自当前适配器/证明，尚未实证 | 条件支持，平台语义 HOLD |
| directory | 目标目录集合必须与 `directory_details` 一致；每题目录必须在集合内；目标目录必须是叶目录；保存后目录细节、目录集合完全不变 | 当前目录清单和叶节点关系尚无新鲜完整私有快照 | 条件支持，真实目录 HOLD |
| delete | 框删除列表被硬编码为空；write-set 声明 frame delete 为空；仅 analysis/knowledge point 两个空区操作，且合同标注 `NEW_QUESTION_ONLY` | 实际统一提交接口是否把 `ocr_delete_zones` 严格限制到新题，依赖当前 joint-policy / schema 观测证明；无真实证明时不能声称零旧题删除 | 负向约束已实现，服务端语义 HOLD |
| upsert | 保存前拒绝新行 rect ID 与任一旧框 ID 相交；六个新 rect ID / crop path 必须唯一；保存后旧框与旧正文严格相等 | 真实后端是否严格按 payload 语义执行，需保存后完整读取；当前没有新鲜保存/readback | 条件支持，实际效果 HOLD |
| newness | payload 固定 `question_order=null`、`is_new_question_insertion=true`、`insert_after_order=旧最大值`；回执必须 `inserted=true`、新 ID、order 增大；读回必须恰好多 1 题、6 框 | 尚无当前真实业务回执、实际新增 ID/order 与完整读回 | 条件支持，实际新建 HOLD |
| save_page | 每个 crop 的 `source_sha256+bbox+save_page+image_path` 必须与源绑定一致；框的 `page_index` 必须等于绑定的 `save_page`；六张 crop 的字节哈希/尺寸另有门 | 当前 source mapping proof、六张最终 crop 与真实页面/保存页关系缺失 | 条件支持，来源关系 HOLD |

## 链路核对

1. `wire.py` 要求 observed/synthetic 模式匹配、全部 proof 为 VERIFIED、旧正文覆盖声明为 `ALL_FIELDS_ALL_ZONES_ALL_OLD_QUESTIONS`，并要求每个 read phase 有精确 GET manifest。
2. 旧正文导出不接受“若干题 JSONL”作为完整性：complete codec 必须有唯一 metadata 记录并与快照题清单、五区、状态版本一致；natural codec 必须绑定 VERIFIED 的权威路线资格。
3. `UsenseTransport.observe` 把导出的每题 `rect_ids` 与同一快照中的实际框集合逐题比对，然后才把旧正文装入 observation。
4. `check_target` 在保存前再次要求所有旧题五区与 `question_info` 完整，并拒绝任何新 rect ID 覆盖旧框。
5. `check_preservation` 对旧目录、旧题、旧框、内部绑定、框投影、旧正文逐对象相等；只允许一个新平台题 ID 对应的新题/新框/新元数据。
6. runner 对 get 和 refresh 都使用最初 baseline 做保全比较；独立新 context 的 reopen 也再次用同一 baseline 检查。作者读回只能是 `AUTHOR_READBACK_ONLY`，不会自动升级为独立接受。

## HTTP 原始字节边界

当前浏览器 I/O 会从 CDP `Network.getResponseBody` 取得响应字节，并要求其 SHA-256 等于页面 fetch 返回文本按 UTF-8 重新编码后的 SHA-256；若二者不同会拒绝。因此非等价的 DOM/文本重编码不能静默通过。

但旧正文 coverage 中记录的是文本 UTF-8 哈希，ledger 也没有把 native raw response SHA-256 作为独立字段暴露在 observation 中。后续收到新 manifest 时，仍必须单独确认：每个私有输入的长度/SHA、采集类型（HTTP raw bytes 或 DOM/UTF-8 文本）及其与适配器输入的绑定，不能仅凭当前 `raw_export_sha256` 推断原始 HTTP 字节已经冻结。

## 定向负例

使用规定 Python 和 canonical long TEMP 运行 `tools/a24_old_preservation_negative_tests.py`，6/6 通过：

- 无权威完整性 metadata 的题记录：拒绝 `AUTHORITATIVE_EXPORT_COMPLETENESS_REQUIRED`。
- natural export 无 observed route qualification：拒绝 `NATURAL_EXPORT_AUTHORITY_UNBOUND`。
- 少一个五区键：拒绝 `EXPORT_QUESTION_COVERAGE`。
- 有题清单但缺旧正文分母：拒绝 `OLD_CONTENT_INCOMPLETE`。
- 保存后篡改旧 `question_info`：拒绝 `OLD_QUESTION_CONTENT_CHANGED`。
- crop 的 `save_page` 与源绑定不一致：拒绝 `CROP_SOURCE_BINDING`。

这些是小型合成 fail-closed 验证，不是网站实测、不是保存效果证明，也没有重复运行旧的大型测试套件。

## 冻结源码哈希

- `wire.py`: `e89057ecdcdcb4878c22138b6de99a47dcd621bb2ce52c938d6fcc83f1a88d08`
- `usense.py`: `6e5c6ae1fa08588ee675193a3054588c1b537083098ab169b4646cc1ddc3e277`
- `quality/live_pilot.py`: `6b5b9362bfab4879f8b2b676028848b3f7009fb3cf825ea7ba9dccc722d6ace6`
- `runner.py`: `2c3237e59ee92a2e804991bbc911f16dbf4c40a00fb4d5eaf5cef973de9f2275`
- 独立负例 harness: `5a562cf36f336b4433a311546846c95cacadcba7f982dc6907427c1bde0aab83`

## 后续接收门

收到来源成员的新 manifest/私有输入后，按以下顺序复核：

1. 逐文件核对长度与 SHA-256，并分类 HTTP raw bytes / fetch text / DOM 导出；不允许混称。
2. 从权威题清单建立当前全量旧题 ID 分母，再逐题核对五区、question_info、全部业务字段、rect ID 集合、order、directory。
3. 从全量框清单建立旧框分母，逐框核对题关联、类型、bbox、page/save_page 与 image path。
4. 用适配器生成的 observation 与原始私有输入逐字段对照，列出 preservation delta；任何缺项、额外项、重编码不明或关联不唯一均 HOLD。
5. 只有真实保存后 get、refresh 和独立 reopen 都相对同一 frozen baseline 无旧题 delta，才可进入人工/官方接受；机器 PASS 仍不等于平台或人工验收。
