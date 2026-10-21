# A24 首题保存页码、坐标与已知正文导出：静态准备

辅助准备，已释放。仅核指定历史 Script 原件与两份已有首题笔记；未读活动作者、A24 r1 实际输出、真实资源、profile 或凭据。0 产品运行/import/test、浏览器、网络、权限或正式验收。原件先核 3,065,996 bytes / SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`。

## 页码链

`qw` 根据题目区/答案区输入更新 `qn/ra`，`Ql` 将该 viewer 页码传给 `Mo` 并将结果给 `mn/Un`，它们分别作为两个 PdfViewer 的 pages。OSS `p6e` 中资源索引为 viewer−1。

PdfViewer 的 `nt` 发出 `selectRegion(dataURL, pages数组下标, rect)`。父 `Aue` 明确设置题干/选项新框 `page_index=qn.value`；父 `Due` 设置答案新框 `page_index=ra.value`。**保存页码没有采用事件的 pages 下标，也没有采用原图资源的 page_index。** `e8` 从 clip 到上传结果再到 `annotations_upsert` 原样传 page_index，提交前无 ±1 转换。

因此，若当前绑定的题目区选页为14、答案区为173，官方客户端合同发送的保存页码是14/173；即使 OSS 资源索引为13/172，也不能直接写13/172。这里证明的是客户端转换关系，未证明本轮实际显示选页、服务端接受或最终读回。建议字段分开命名 `viewer_page`、`resource_index`、`saved_page_proposal` 并附来源。

## 坐标链

设原加载图像尺寸 W,H，canvas像素 Cw,Ch，浏览器矩形 left/top/width/height 为 L,T,Bw,Bh，缩放 z，平移 px,py。`$(mouse,slot)` 的精确逆变换是：

```
cx = (clientX-L) * Cw/Bw
cy = (clientY-T) * Ch/Bh
f = min(Cw/W, Ch/H)
ox = (Cw-W*f)/2; oy = (Ch-H*f)/2
x = (cx-px-ox*z)/(f*z)
y = (cy-py-oy*z)/(f*z)
```

这是 `Be` 对原图居中、fit、缩放和平移绘制的逆运算。`rect_bbox` 因而处于**原加载图像像素坐标**，并非 CSS、截图或显示 canvas 坐标。`A` 排成 xmin/ymin/xmax/ymax；普通完成路径可能按预标注或交叠 blocks 调整框，不能以鼠标端点代替最终框。提交链没有再缩放，只把数组 `.join(',')`。本辅助未测当前画布变换，也未确认实际六框。

`nt` 以加载图像完整尺寸建立临时画布，再按原 bbox 裁片并生成 JPEG dataURL；它不将 bbox 改成裁片局部坐标。裁片光栅化和编码不能作为原 bbox 取整规则。新框产生 dataURL 会进入既有上传分支，不能把源图 URL 当成已存在裁片；具体上传范围仍须固定。每区数组序号成为 `image_order_in_annotation_zone`，与资源页索引无关。

最小同阶段接线：把已固定原图 bytes/hash/尺寸、viewer与resource关系、最终六框原图 bbox 绑定；不重复做显示缩放；保留普通框与预标注调整的区别；裁片和保存请求分别计数。服务端保存映射只能由实际回执和独立读回完成证明。

## 仅沿两条已知旧正文导出线索

- `q6e`：GET `annotate_ocr/export-paper-questions/{file_id}`，只传路径ID并按 blob 接收。AnnotateUnified → hyt 的 paper handler 直接调用并下载 `{file_id}_paper_questions.jsonl`，该 handler 本身没有调用其他导出所用 precheck。此链无 zone 参数，也无 zone覆盖、全题集合、分页完整性、版本/摘要或框关联验证。**无 zone 参数不等于覆盖全部 zone。** JSONL 的实际 schema/内容尚未知，不能直接当全旧正文 baseline。
- `D6e`：GET `annotate_pic/training_questions/{file_id}/export`，经 Hn 解包。确切消费者来自“题干训练拉框”，提示“导出仅包含已保存题目”，下载 `_traning.json`。不能将训练题集合视为统一标注全部旧题；没有找到这条确切调用链的全 zone/coverage 验证。

只沿上述已知符号追调用，没有全前端泛搜导出端点。后续如采用聚合读，必须在同 A24 具体方案中固定已有接口的一次有限 schema/coverage 核查；本笔记没有增加请求或授权，也没有证明全量保全。

## 精确证据

以下为原 Script 的0-based UTF-8字节offset；全部小片段文本及输入笔记hash见 `notes.json`。

- OSS_viewer_to_resource_index: offset 1076726, 550 bytes, SHA256 `b87eada935d68158b0f7d1fdacac1409991a3dcefea61660a981c974ef19d927`.
- parent_page_navigation: offset 2710986, 423 bytes, SHA256 `d8b08be864434bbaa7ef59170ab88f0e57509c05228425ea180995ecbe1dc40e`.
- parent_page_load: offset 2712280, 2062 bytes, SHA256 `0d6bcaeeb410a33dfae3b8387111d0b4fb96837cc6d3bf8e5162976c9bff335c`.
- viewer_mouse_inverse_transform: offset 2611064, 616 bytes, SHA256 `f5ba31da99051d4bb099367fb33b728e4500e835853c3994f5ff265ef594faae`.
- bbox_normalize: offset 2611680, 96 bytes, SHA256 `68ce05187ff9a629e300fb9f4cdb02c92ce96e3597cf06c48172e8d4a1197c21`.
- ordinary_draw_finish_and_optional_snap: offset 2621778, 1932 bytes, SHA256 `c469bf8040bc457788c125e74ba61f68379b3d2cd193c225443391bf35bb28f4`.
- viewer_image_draw: offset 2624767, 1425 bytes, SHA256 `dcc9afaab60ee5517d7103b65414328b22f84bace93bef4f8ed791ccfdcf731c`.
- crop_and_selectRegion_emit: offset 2626296, 745 bytes, SHA256 `efe660e85394aabfe60106111a35a6f4772f93f8b4f1e7d850e8f080ee509454`.
- question_choice_parent_select_handler: offset 2727523, 1402 bytes, SHA256 `3c4ac366a1c2d7d4fe75d01dda1c46c44f0434a38b054457eab0338b5a3ba9d5`.
- answer_parent_select_handler: offset 2730261, 1119 bytes, SHA256 `7856658dd1de22ad94de1a901a344bbb88effa0407574d8ca12d5ae20106e4dd`.
- question_component_event_binding: offset 2800133, 332 bytes, SHA256 `fc17f515fcd3dc39f428153a36ae24753c31049e48b12a68963dd065b43f1c92`.
- answer_component_event_binding: offset 2803377, 330 bytes, SHA256 `4ac784765fcb8fc7491c11489a932aec8ab250162b3ac98433b61af5813c9ec0`.
- crop_dataURL_upload_selection: offset 2745806, 632 bytes, SHA256 `170f2f58011e8aabdf1462aa711e94c00df39be241e27d25f28e8a4b1b2aef3c`.
- upload_result_to_rect_fields: offset 2749145, 495 bytes, SHA256 `8d1663ce9fdd547a206b55cef1c4962ee3140568d3d8bdb3fd4d20491d3a2828`.
- final_commit_payload: offset 2752171, 856 bytes, SHA256 `ae4d8cb7628b4b8d9bed899b03b1a44aa0277d87d425fe6efffa9bf42e739e86`.
- ordinary_save_call: offset 2753835, 512 bytes, SHA256 `f59fffd549d4c8a2287b0746cc1a3761819f5cb516c3e0343e80816569377c86`.
- commit_API: offset 1083248, 95 bytes, SHA256 `34548ec469d6bf7963ab9b34648792b9b8c77727236a3a148d0b8ae28a29fa72`.
- paper_export_API: offset 1086616, 101 bytes, SHA256 `dabf1a1f68f77a6c1055dbb1de87817182c70e64b33134601780dd629638dbfc`.
- training_export_API: offset 1083587, 101 bytes, SHA256 `674d45de5dc9ac06119c4d4d050b14470a2314219ec072865d08ec690d1fb68a`.
- paper_export_UI_handler: offset 2643641, 396 bytes, SHA256 `051616ec06af4e6bacc8f89d3666e94e1f261667b456ce513ad5a18b927b825b`.
- paper_export_dependency_binding: offset 2710650, 266 bytes, SHA256 `57c712e898a224b1a51a4f4220a546d9ab6318af0eab648d60b838ebe17b2d56`.
- training_export_UI_handler: offset 3052920, 397 bytes, SHA256 `a379acfe347668b7eb2d28f69471f7122e75955f960702e334366eeee7b97f2a`.

相关静态事实仅供同 A24 执行/正式独立固定修订使用。所有本辅助进程已退出，未持有等待任务。
