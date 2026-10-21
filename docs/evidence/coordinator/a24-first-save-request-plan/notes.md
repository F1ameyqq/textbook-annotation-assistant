# A24 首题 schema 与有界请求计划：静态准备

仅辅助准备，非正式验收、请求授权或 activation。未运行 Script/产品/测试，未联网或访问 browser/profile/凭据/native/活动作者/sidecar。原脚本已复核 3,065,996 bytes，SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`。以下 E 编号对应末尾精确 offset/length/SHA；只保留字段与关系，不复制脚本或任何真实签名值。

固定当前 `raw/current-state.json` 为 232,913 bytes，SHA256 `640aaabe023c1e96e24ac3b1b002c8b9e7c045ed7b075a8777377a8ae9ba5775`。它记录书46007447身份及 viewer 准入、22题节点/68框、LEGACY_DB 和两原图；但 `inventory_coverage=PARTIAL`、`content_coverage=UNKNOWN`、`write_preservation_baseline=false`、`append_after_order=null`、body/schema UNKNOWN、write_eligible=false。这些数量不能升格为全书保全或当前保存题序。正式实际审查另行进行。

## 保存接口及六框/正文关联

| 操作 | 精确静态合同 | 证据 |
| --- | --- | --- |
| 普通统一保存 | POST `/qieti/api/annotate_pic/commit_unified_submit`，JSON body，`VI→e8(includeOcrSubmissions=true)→E6e→gn.post` | E01–E05、E08 |
| 单题框读回 | GET `/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/{file_id}/{order}`；Hn 可将 data 数组包装为 annotations | E13 |
| 题信息读回 | GET `/qieti/api/annotate_pic/get_question_info/{file_id}/{order}`；前端消费 tishi/tilei/tihao | E14 |
| 三 zone 正文 | 同一 GET `/qieti/api/verify_annotation/get-ocr-annotation` 各一次，键 `file_id,question_order,zone`，zone 分别 question/choice/answer；第四参数非 null 才加 `image_order_in_annotation_zone` | E11–E12 |
| 现有全框入口 | GET `/qieti/api/annotate_pic/get_manual_annotations_unified/{file_id}`；省略 pageNum 是一个确切请求，不据此声称 FULL | E15 |

保存顶层字段完整白名单：`file_id,target_directory_id,question_order,is_new_question_insertion,insert_after_order,annotations_upsert,annotations_delete_rect_ids,ocr_submissions,ocr_delete_zones,question_info,created_by`。`question_info` 为 `{tishi,tilei,tihao}`。新插入分支的顶层及正文 `question_order` 为 null；`insert_after_order` 来自当前目录解析，当前仍未绑定，不能把22节点或 derived max22直接变成题序23。[E04–E05]

每个框字段：`rect_id,type,belong_to_level,order_in_level,image_order_in_annotation_zone,rect_bbox,page_index,image_path,parent_rect_id,directory_id,content_type,user_id,is_pre_annotation,pre_annotations_id`。具体 ordinary 六框为一个 question、四个 choice、一个 answer；客户端这些类型映射 `belong_to_level=question_level`，`order_in_level` 由暂定题序转字符串；不是可以提前编造的服务端 receipt。[E04、E07、E24–E26]

每份正文为 `{zone,ocr_result,rect_ids,question_order}`，通过明确 rect_ids 连接对应一/四/一框。choice 正文是一份 zone 内容，四个 rect_ids 按选项顺序列出；并非四次正文 GET。`image_order_in_annotation_zone` 为该区零基数组下标，Q/A各0、四个choice为0–3。UI 的上传收集顺序却是 question→answer→choice→analysis→knowledge_point，不能拿 Promise 完成序或总数组位置当 A–D 顺序。用稳定 rect_id、zone及区内顺序比较六框。[E05–E07]

`rect_bbox` 数组提交时 `.join(',')`，单位为原加载图像像素；parent 新框 page_index 取题目区 qn/答案区 ra，而非 resource_index。当前原图分别：viewer14/resource13，1218×1694，SHA `4186d57ffad14f576fe7c967c96697d25c83ffe3512217c79b8371134181c1d9`；viewer173/resource172，1148×1621，SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。两者 full_pixel_decode=true，但实际 save_page/visible_status仍UNKNOWN。静态 proposal可按所绑定 viewer选页14/173，不直接写13/172，最终六bbox/实际保存映射仍须明确。[E04、E25–E28及固定raw]

非空正文且有有效框 ID 才进入 `ocr_submissions`；空白有框或无框 zone可进入 `ocr_delete_zones`。不能把缺失正文当“无操作”。新题至少 question/choice/answer三区精确内容须绑定；analysis/knowledge_point若为空，也须明确空的语义及只影响本新题，不能默许删除旧正文。[E05]

## 回执能证明到哪一步

Hn 对 numeric code 0/200 返回 data，对其他 numeric code抛错，无 numeric code则原样返回；这只是客户端解包合同。VI只读取 `question_order`，`parseInt(...) || tentativeQuestionOrder` 含客户端 fallback，禁止作为真实成功或题序证据。新插入后还消费 `append_at_global_end` 和 `inserted_question_node`；pse要求 isQuestion，但在前端覆写该 node的 label/order_in_level。因此保留服务端原返回与本地派生的区别，不能把派生node当原响应。[E02、E08–E10]

当前静态链没有证明必返回六个 rect_id、稳定 platform_question_id、完整实际写集或服务端强制新增/幂等。下一真实 codec应保存有限 HTTP/业务状态和真实 question_order/node身份，缺失或冲突即 UNKNOWN，不用暂定题序兜底、不重发。保存后一份回执不足以证明正文和六框，必须后续真实 GET/refresh/正式独立 reopen。UI自带读框失败→全框 fallback也不应隐式继承。[E08–E10、E13–E14]

## 六个新裁片：准确计数及禁用重试

签名入口是 GET `/qieti/api/annotate_pic/oss_signature`，参数 `file_id` 与 `dir_type`，此分支默认 dir_type=`annotate_images`。JB缓存签名及expire，并共享正在进行的 I0；仅在当前时间不晚于expire前300秒时复用。因而六次BI调用不必产生六个签名GET。[E16–E18]

新框dataURL各自转JPEG Blob，六个实际新裁片意味着**六个单对象上传POST**。一份签名可被这条客户端链共享；可拟定“签名GET最多1、上传POST最多6”的具体路线，但先验证该签名host/dir/expiry/policy适用于这六个固定对象且覆盖整个发送窗口。未知、过期或不足即停止，不能自动再签。签名响应需用的字段名是 accessid/host/policy/signature/dir/securityToken/expire；值只在受控内存中，不写notes/日志/Git。[E16–E20]

每个上传使用响应host，FormData键 `key,policy,OSSAccessKeyId,success_action_status,signature,Content-Type,file`，securityToken存在才加 `x-oss-security-token`；此代码要求的 success_action_status 为200、Content-Type为image/jpeg，成功后客户端拼 `host/key` 成 image_path。`response.ok` 和该拼接路径还不是内容保存证明。上传host和对象路径、六个裁片bytes/hash/尺寸/rect_id/zone、是否原TLS许可涵盖该origin，均必须在具体写方案中绑定；不能把原图URL当已上传裁片。[E19–E20、E27]

必须禁用三处自动续发：JB签名失败的等待重试（默认一次、400ms）；BI遇403清缓存后重新签名并重传（默认一次）；gn的401 refresh-token/重发。不调用整个VI/e8/BI/gn副作用链来借用这些行为。一次签名异常、任一上传失败/UNKNOWN或保存UNKNOWN后，后继请求NOT_RUN，记录已上传对象但不补发、不自动删除。若六个已合法存在的裁片可被证实复用，可另固定U=0路线；当前不得假定它们存在。[E17–E20、E32]

## 导出作为全旧正文基线：可拟计划，当前未证覆盖

确切自然导出入口为一次 GET `/qieti/api/annotate_ocr/export-paper-questions/46007447`，无筛选query、按blob接收。AnnotateUnified交给paper handler后下载 `46007447_paper_questions.jsonl`，该handler没有解析JSONL或逐题/zone校验。只证明端点、整本ID参数和下载用途；**未找到这条消费链的确切JSONL记录字段、question/choice/answer/analysis/knowledge_point覆盖、完整性标志、版本/摘要、rect_id关联或空zone规则**。[E21–E23]

可以在同A24具体预读中固定该已知GET一次，尝试把自然导出变成聚合基线；不能把“无过滤”“扩展名jsonl”“正好22行”当覆盖证明。条件至少包括：响应成功且不是登录/错误blob；逐行可解析且实际字段可映射到当前22旧题的稳定身份；无重复/遗漏；多行/跨zone关系明确；全部存在zone及显式空值有规则；与目录/框的当前集合一致；响应的完整性/同一状态证据足以排除未导出的题/zone。由于当前库存PARTIAL，覆盖这22个已见节点只是必要条件，仍需证明权威集合无遗漏。[E21–E23及固定raw]

只有这些条件成立且对应schema/比较器已固定，才能给出全旧正文baseline。后续保全须拿新鲜导出或等价已证权威摘要/完整写集比较旧题所有正文，不能仅比较导出bytes（下载顺序/元数据可能变化）或只读新题三zone。若schema或完整性在预读后仍未知，本同阶段停在可复用事实，六裁片/保存NOT_RUN；不另开泛化诊断，不猜字段，不盲逐题扫描，也不对Q22作专项导航/抽样。

## 条件式请求计划实例，供根冻结准确 manifest

这是未授权的计划骨架，前置未知未清就不进入写阶段。候选实际时限、上下文和导航、所有method/origin/path/键/每phase次数须由同阶段具体方案固定；旧readonly两轮均已耗尽。

| 阶段 | 固定显式请求上限 | 门槛/去重边界 |
| --- | --- | --- |
| baseline预读 | book1 + directory1 + 全框1 + paper导出1 = 4 GET | 官方既有context的book查询，不猜账号；精确目录/库存/导出schema与保全成立；固定原图可本地复用，不再抓两图 |
| fresh prewrite | directory1 + 全框1 + 导出1 = 3 GET | 同context已确认书；与baseline同一旧状态，先持久化不可变intent/claim再发送 |
| 六裁片/保存 | 签名GET≤1；各裁片POST≤1，总≤6；统一保存POST≤1 | 六对象清单、origin/TLS范围、合法插入点、内容/六框/完整写集及适用保存许可齐全；所有重试0 |
| author get | directory1 + 全框1 + 导出1 + 单题框1 + 题信息1 + 三zone正文3 = 8 GET | 服务端真实题序；全旧保全与新正文六框分别比较，禁止缓存代替响应 |
| author refresh | 真实刷新1；同上8 GET | 旧phase响应不能冒充新鲜读回；UI自动请求与主动请求共享该phase槽位 |
| formal independent fresh reopen | 作者释放后新context/重开1；book1 + 同上8 = 9 GET | 独立读取固定新题、完整旧数据及释放链；不是作者标记reopen成功 |

此实例显式只读GET共32（其中导出5次分属baseline/prewrite/get/refresh/reopen），另签名GET≤1、上传POST≤6、保存POST≤1；不包含必须另列上限的认证/session/static及Document导航。第一次导出是上述基线候选，不是一次导出即可证明整个保存过程保全。若所选保全机制有已证版本/写集，或同phase全框已足够精确读回新六框，可在冻结前删掉确实冗余请求；不能运行时自选额外接口/备用路线。三个zone GET缺分析/知识点响应不能据此宣布全书正文完整。

计划中的已知路径另见 E29–E31：book `/qieti/api/claim_book/books`（原九键派生）、directory `/qieti/api/annotate_ocr/directory/get`（file_id），全框及导出如上。具体query值只在原会话受控内存形成；所有scope/policy/候选/当前manifest/请求预算/保存与上传授权仍待根及正式流程绑定。此辅助不创建它们。

## 精确证据索引

下表由原件逐段重新取bytes计算；文本未复制到产物。所有offset均0-based UTF-8 byte，片段只支持所列静态关系，不能证明本轮服务端schema或行为。

| ID | 片段关系 | offset | bytes | SHA256 |
| --- | --- | ---: | ---: | --- |
| E01 | API_prefixes | 1067339 | 149 | `280d8924302f3212d3e0f29a141c0ff1cb0d85c06bede68e1143457d08427e39` |
| E02 | Hn_envelope | 1069105 | 192 | `d112894ccf3bc7bf103b1bfb6549d2ee2142906567516e9c0b9779e5cc3f4bac` |
| E03 | commit_POST_wrapper | 1083248 | 95 | `34548ec469d6bf7963ab9b34648792b9b8c77727236a3a148d0b8ae28a29fa72` |
| E04 | full_commit_payload | 2752171 | 856 | `ae4d8cb7628b4b8d9bed899b03b1a44aa0277d87d425fe6efffa9bf42e739e86` |
| E05 | zone_body_and_delete_lists | 2750950 | 1221 | `4cdbae088443d8c3475ab17d96e79c67058fa6b6b429bf0ec457bc69562cb8d6` |
| E06 | zone_upload_collection_order | 2748800 | 345 | `07ed6ff33cc34a9bf1880c26a74fb06a5fc4be8caddaf7939faf515bbeb46918` |
| E07 | upload_result_to_frame_fields | 2749145 | 495 | `8d1663ce9fdd547a206b55cef1c4962ee3140568d3d8bdb3fd4d20491d3a2828` |
| E08 | save_result_and_order_fallback | 2753835 | 512 | `f59fffd549d4c8a2287b0746cc1a3761819f5cb516c3e0343e80816569377c86` |
| E09 | inserted_node_normalization_and_identity | 2682488 | 595 | `ccf0559272e81eae1aaabb1284e22b38585ae453eb1c59e365d48f72c880af0d` |
| E10 | new_insert_followup_and_fallback | 2683083 | 1208 | `cebec0f7d09961d92c15f5651b0d574c49ee50342bec1b7a78a38cbdf5786012` |
| E11 | body_GET_wrapper | 1081707 | 200 | `6506e54fe1aabbe7efd879bb770713695a60f31d86c64b66583196d7e3258655` |
| E12 | body_GET_three_or_five_zones | 2765887 | 1465 | `1b6a78c7fd53404f79025a25da35e28e30df8ea2fa6f5edb0565917542ceec47` |
| E13 | single_question_frames_GET | 1080370 | 154 | `a60c434f4fc214e1845a6959aa1f5f5d7eed4e74848a701beaeff0dc4ebf4f86` |
| E14 | question_info_GET | 1080524 | 100 | `e6e723fc155ade6777f26c2c6161279ff499f5b21d2a140df59e8891bcbcbfde` |
| E15 | all_frames_GET | 1078292 | 206 | `b21799a14eae2087db932580244e206febb805926456e9cbceb6ec3626444f3f` |
| E16 | signature_GET | 1078788 | 136 | `53148066d1e3c883a90f8a097899832f4cedb8e67242fe73bea0b7daaec2371f` |
| E17 | signature_cache_inflight_and_retry | 2744438 | 497 | `e3601eeb19737604c215ad6a89b025098f93d771df7f28a9184c02c1c66cd836` |
| E18 | signature_expiry_margin_retry_delay | 2658364 | 15 | `34649fa795e9ffc0b4d8e7360fa5c82cd0b3d3f26ff770a76e3ee348071faeef` |
| E19 | single_object_upload_and_403_retry | 2744935 | 871 | `ee5a04331837faaa28dc0b66511afa5dc33931eef89eb13092a85ce21aafc4ec` |
| E20 | new_dataURL_vs_existing_path | 2745806 | 632 | `170f2f58011e8aabdf1462aa711e94c00df39be241e27d25f28e8a4b1b2aef3c` |
| E21 | paper_export_API | 1086616 | 101 | `dabf1a1f68f77a6c1055dbb1de87817182c70e64b33134601780dd629638dbfc` |
| E22 | paper_export_download_handler | 2643641 | 396 | `051616ec06af4e6bacc8f89d3666e94e1f261667b456ce513ad5a18b927b825b` |
| E23 | paper_export_dependency_binding | 2710650 | 266 | `57c712e898a224b1a51a4f4220a546d9ab6318af0eab648d60b838ebe17b2d56` |
| E24 | frame_level_and_order_mapping | 2659358 | 580 | `07d7edcb67ebf07cdc302fb1eccbb5fcc9b6066855bff632d5ceb20c414eacf3` |
| E25 | question_choice_page_handler | 2727523 | 1402 | `3c4ac366a1c2d7d4fe75d01dda1c46c44f0434a38b054457eab0338b5a3ba9d5` |
| E26 | answer_page_handler | 2730261 | 1119 | `7856658dd1de22ad94de1a901a344bbb88effa0407574d8ca12d5ae20106e4dd` |
| E27 | original_pixel_crop_emit | 2626296 | 745 | `efe660e85394aabfe60106111a35a6f4772f93f8b4f1e7d850e8f080ee509454` |
| E28a | inverse_original_pixel_transform | 2611064 | 616 | `f5ba31da99051d4bb099367fb33b728e4500e835853c3994f5ff265ef594faae` |
| E28b | bbox_normalization | 2611680 | 96 | `68ce05187ff9a629e300fb9f4cdb02c92ce96e3597cf06c48172e8d4a1197c21` |
| E29 | book_GET | 1071302 | 490 | `785c2c0a82312f644427c46bcc5f337ae3b00338fb48e2921e147dc22614a2d5` |
| E30 | official_book_query_keys | 1071792 | 428 | `4993435e84e864f02e6415bb8a4bf9e823d5a6c34c8635ad503fec0711e77fd4` |
| E31 | directory_GET | 1082583 | 91 | `a4652b00216bb48abbe1b4a624a2a1aa5a474fb4585953bf0035be3f50c3c294` |
| E32 | axios_auto_refresh_resend | 1067893 | 1212 | `dc1eb399d6c90f867d065e757bd7f8100f80fb353231a49fa4340ddce54aab9a` |
