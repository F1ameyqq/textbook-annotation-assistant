# 后续只读取证静态索引

仅辅助静态检索，不是正式执行/验收，不授权扩展A15守卫。作者 `/root/a14_dispatch_boundary_aux`；0旧工具/suite运行、0网络/browser/profile/凭据/进程扫描、0.local读取、0B消息。

旧 `docs/evidence/A10/execution/preflight.py` 212–224行列出这些已有GET：

- `/qieti/api/claim_book/books?page=1&pageSize=10&id=46007447`
- `/qieti/api/annotate_ocr/directory/get?file_id=46007447`
- `/qieti/api/annotate_pic/get_manual_annotations_unified/46007447`
- `/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre`
- `/qieti/api/annotate_pic/pre_annotation/46007447?pageNum={viewer}&annotationType=mr_pre`

旧A10候选viewer10/14/15/173实际只固定14/15/173，10为NOT_SELECTED。旧guard资源索引13/14/172不能代替当前viewer/resource绑定。旧preflight202、227、243行含UI书号、book/page_index和原图/canvas维度核对。旧collector26、39行包含GET允许名单、401/403登录判定和页面内部令牌使用。

这些仅为后续阶段的源码线索。原A10书籍/目录/框/source/三页均NOT_RUN；历史22题68框不能作现状。旧collector128行_annotations仅保留框/目录/角色/坐标，不能证明文本内容。当前 `src/annotation/delivery/live_pilot/usense.py:17` 仍有 `LIVE_READBACK_CODEC_UNAVAILABLE`；A11真实接口、完整target/内容刷新重开codec未接通。

若A15仅认证观测通过，需另固定当前书/source/target的正式只读阶段，核实际接口和绑定，不能重跑原A10或沿用历史库存，更不能由本索引直接写题。主调度使用这些线索前仍须核固定源码与新的实际结果。
