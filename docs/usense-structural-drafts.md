# 第二课时目录纠正和新增题：离线结构草稿

本轮基于第一轮 `604b83d`，仅新增通用离线模块、工具、合成测试及本文档，不修改公共状态、OCR、Q7专用算法或网络传输。没有任何结构写入口；所有草稿和比较结果都保留 `write_authorized=false`、`platform_acceptance=false`。原统一 writer 和 Q7 writer 不接受此草稿格式。

第二课时现有 native18—22 是当地印刷 Q1—Q5，不能再把旧原生17—21称作印刷题号。真实范围是当地Q1—Q8及Q8后变式，共9题；相邻阅读3任务另计。该修正来自新来源核查，不修改此前历史记录的原字节。

## 已确认的前端协议

绑定留存 JS 的SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`。实际请求构造器为：

- `POST /qieti/api/annotate_pic/directory/change-set/preview`
- `POST /qieti/api/annotate_pic/directory/change-set/apply`
- 两者载荷均为 `{file_id, original_directory_data, draft_directory_data}`，后两项是完整目录数组，保留未知字段；不是 `structure` 包装，也不是单题move请求。
- 前端 `Eg/C0` 克隆整树后按遍历顺序把题节点 `order_in_level/label` 改为连续字符串。前端没有独立version字段；提交原树不等于已证实服务器具有乐观锁，具体冲突HTTP状态和业务code尚未知。
- `has_changes=false` 时前端停止；`directory_moves[].impacted_question_count>0` 时显示确认。其他情况可能自动调用apply。**不要运行这条完整UI流程来采preview。**
- 名为preview的请求仍然是POST。前端不能证明它绝无写入副作用，需要总控隔离该请求、留原始响应并重新GET比较。

实际预览回执/apply收据还没有在本工作线被观察，因此不猜服务器响应schema、不生成apply请求或自动放行。私有前端片段和实际五题preview载荷单独留本机，不进入仓库。

## 可复现入口

```powershell
python tools/prepare_usense_structure.py protocol --frontend PRIVATE/current-1-index-CU_hexWN.js --out PRIVATE/protocol.json
python tools/prepare_usense_structure.py prepare-move --baseline PRIVATE/full23 --targets PRIVATE/targets.json --destination TARGET_DIRECTORY_ID --scope-review PRIVATE/move-scope.json --protocol PRIVATE/protocol.json --observed-at ACTUAL_OLDEST_CAPTURE_UTC --out PRIVATE/move-bundle.json
python tools/prepare_usense_structure.py prepare-new --baseline PRIVATE/fresh-after-move --candidate PRIVATE/new-candidate.json --scope-review PRIVATE/new-scope.json --content-review PRIVATE/content-review.json --protocol PRIVATE/protocol.json --observed-at ACTUAL_OLDEST_CAPTURE_UTC --out PRIVATE/new-bundle.json
python tools/prepare_usense_structure.py preflight --bundle PRIVATE/move-bundle.json --sha256 BUNDLE_FILE_SHA256 --fresh PRIVATE/fresh-full23 --ledger-root PRIVATE/usense-existing-ledger --out PRIVATE/preflight.json
python tools/prepare_usense_structure.py verify --bundle PRIVATE/move-bundle.json --sha256 BUNDLE_FILE_SHA256 --after PRIVATE/independent-after-move --out PRIVATE/move-comparison.json
python tools/prepare_usense_structure.py verify --bundle PRIVATE/new-bundle.json --sha256 BUNDLE_FILE_SHA256 --after PRIVATE/independent-after-insert --receipt PRIVATE/native-receipt.json --runtime-actor-hashes PRIVATE/actor-hashes.json --out PRIVATE/new-comparison.json
```

工具只读本地证据、独占创建输出；不启动浏览器、不联网、不导入Playwright。相对工具路径按仓库定位，证据引用使用绝对路径+原始字节SHA256。bundle锁定全部baseline响应文件和输入文件。`preflight`重建草稿、核完整新基线相等、900秒原始观察时效及ledger；即使通过也**只证明基线一致，不授予写入**。同身份已存在intent（包括历史accepted）采用保守拒绝，需单独审查结构前序适配，不能自动忽略或重发。

## 目录纠正保护范围

`make_move_draft`输入完整原生map、五个既有完整target、目的目录和来源归属审校。目标每个字段都须与当前目录节点、question_info ID、原生序号、全框/单题框一致。只支持单一源目录→空叶目录，并且整树遍历后的全局题序完全不变；不支持在本协议未观测时推断更复杂的重排。

对本书当前结构，五题从第一课时移至第二课时，仍为native18—22。预期仅目录父级和这些题所有框的`directory_id`改变，所有node/info/rect ID、题序、题文/答案及其未知字段、时间戳、来源保持。第一课时17题及另一道既有题，共18题逐对象保护。任何额外时间戳或元数据变化都HOLD，不能依据“服务端正常重排”自动放宽。

`scope_review`形状为 `b-usense-move-scope-review/0.1`，字段为 `book_id/targets/source_directory_id/destination_directory_id/decision`，decision明确 `SOURCE_LESSON_MEMBERSHIP_REVIEWED`。这是来源审校绑定，不代表独立真人确认。

## 通用单题新增的最小绑定

`make_new_draft`只接受同书已明确审校的一个逻辑题，目标目录内已有题必须先独立读回且全部稳定绑定。它在该课时最后一题之后、全书其他既有题之前做中间插入，沿用已真实观察的统一提交载荷。新server node/info/order必须保持null；仅客户端frame UUID预先固定。临时frame order沿用前端的全书现有最大题序+1，最终新题序由收据与新原生读回绑定。

候选schema为`b-usense-new-question-candidate/0.1`，精确字段：`book_id/logical_key/printed_number/variant/target_directory_id/server_identity/anchor/frames/zone_values/question_info`。anchor为完整既有target；question_info恰含`tishi/tilei/tihao`，不得猜题型。至少提供question/answer正文及相应框，choice/analysis/knowledge_point只在有来源审校时加入。

每个frame精确包含：`key/rect_id/zone/index/content_type/viewer_page/bbox/source/source_binding/crop/crop_evidence`。

- `source/crop/source_binding/crop_evidence`均为`{path,sha256}`，实际文件须存在。
- `source_binding`复用已留存的`CurrentPlatformSources/v1`或`UsenseObservedPageSourceDownload/v1`。验证实际本地文件路径、源字节、viewer页、原图URL及原生page_index，不能把viewer173图片贴上viewer13页号。
- 原图与裁图用PNG/JPEG头实际核像素尺寸，bbox在原图内，裁图尺寸精确等于bbox。
- `crop_evidence`为`b-usense-observed-frame-crop/0.1`，记录`book_id/viewer_page/source/source_url/source_dimensions/bbox/crop/crop_url/http_status/dimensions`；须有实际HTTP200裁图留存。工具不生成或代跑这份取证。
- 正文所有图片引用必须对应本题已审校框；image/table框须在所属区正文显式引用，不能默默丢图。

scope schema `b-usense-new-question-scope-review/0.1`，字段为`book_id/source_lesson/directory_id/existing_targets/allowed_new_items/completed_logical_keys/allowed_pages_by_zone/decision`。`existing_targets`必须恰为当前目标目录全部稳定绑定；`allowed_new_items`逐项明确`logical_key/printed_number/variant`；`decision=SOURCE_LESSON_AND_EXISTING_BINDINGS_REVIEWED`。回答区允许viewer173而非174的约束由本课时scope明确锁定，不能只凭题面页标签猜测。

内容审校schema为`b-usense-new-question-content-review/0.1`，绑定`candidate_object_sha256/scope_object_sha256`（本包严格JSON对象digest），decision为`SOURCE_CONTENT_AND_FRAME_BOUNDARIES_REVIEWED`。这两者是对象摘要，不是文件字节SHA；外层bundle另锁原文件字节。

新题读回比较消费实际收据、运行时操作者摘要和完整全书对象；逐一核新node/info/rect、正文、zone与frame关系，以及全部旧题仅允许明确的+1题序变化。旧题时间戳和其他字段不放行。比较匹配仍需独立进程/释放/一次性intent/真实导出等外层证据，不能称为平台验收。

本课时四个新增项必须分四次闭环：Q6→新读回→Q7→新读回→Q8→新读回→变式。第二题不能引用尚未由服务器返回的Q6身份，也不能复用五题scope或旧基线。工具没有为整书候选增加写资格。

## 验证及尚缺证据

```powershell
$env:PYTHONPATH='src'
python -B -m unittest discover -s tests -p test_usense_structure.py -v
```

测试均为合成内容，不是实际平台写入。覆盖五题移动/18题保护、稳定身份错配、原字节和协议变化、900秒时效、旧UNKNOWN、原生收据未知、错答案页/错本地图片、漏图、旧题元数据变化、下一题未刷新scope等。

下一关需总控取得独立精确preview原始HTTP响应及前后GET，审查服务器变更集合和冲突处理；再决定目录apply适配。新增题还需来源/裁图/逐区内容审校、目录纠正后的完整新读回及一个通用单次writer适配。当前只有离线草稿和比较器，没有将这些缺口描述为完成。
