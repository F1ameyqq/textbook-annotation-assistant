# A24 same-stage first-save real-wire offline implementation

FORMAL OFFLINE DISPATCH, not a new stage or live activation. Continue author01a15cf8-0c63-70d3-b374-ce85e6f29fd7, xhigh/existing model. The corrected readonly product dde5746600df9854c33c5814a8f41ad85b7b4e16 / final6740d7533ea7b5bf5f322d768e8688826afe5d43 is now received and raw-preserved. Use exactly final6740d753 as successor base in the existing D:/1800-worktrees/a24-first-save, branch codex/a24-first-save; do not reset/rebuild. Candidate SHA c68ce354be516552e1aadafe253cd3f9c12785b3107d2454e59f10446ef31b77; root120-input manifest SHA4ad6a9003ed23442b3f449b8d5216d6011a3df94fefcb5ce980d63e1e20675a1. Keep its raw-checkout, all fixed files/commits and historical evidence intact; new first-save changes are distinct successor files/commits and cannot contaminate the pending readonly candidate. Scope: implement necessary code below now, not documentation alone. Current0realresources/live/write. Task/workflow is the root commit carrying this document and dispatch intent, not any placeholder in historical drafts.

Independent reviewer is checking the frozen readonly candidate in parallel. If it passes and root sends the single readonly activation, promptly pause offline work at a clean fixed point, execute only that frozen raw command once and release actual results; then continue these offline edits as separately directed. Never run live from the mutable successor. Do not self-activate or consume the reserved checkpoint. A later actual-result archive must preserve whichever successor commits exist; root will independently verify the complete parent chain and identify offline changes rather than mislabel them as actual-only modifications.

The following implementation requirements are finalized from the auxiliary draft. Root verified6 fixed Git modules remain exact at6740d753 and8 source documents match. No old suite runs; use new tests/a24_first_save_wire/ and docs/evidence/A24/first-save-wire/ with pure fake transports and explicit synthetic inputs. Retain old readonly modules/guards and existing journal/lock/intent/claim semantics. Dependencies and precise missing real facts remain explicit; static source support cannot turn UNKNOWN into current platform proof. Return a frozen runnable adapter candidate, raw manifests, new relevant results/failures and release. No model/OCR API calls or guessed current source. No B/external messages or push.

## 本次应交付的实现

实现已有证据支持的窄真实 wire codec、注入 transport 的单次发送链和真实观察比较入口，并用新 fake transport/合成 fixture 验证。不能只交文档或把 stub 换成“成功”标签。当前 0 browser/network/profile/配置/凭据/login/native/occupancy/产品 launcher/upload/业务写入/真实 activation；构造对象也不能隐式创建这些资源。纯 fake 实现可执行，真实入口在当前事实、policy、完整 manifest 和明确权限缺失时必须停止零发送。旧 A11–A24 suite 不重跑，只做本次改动必要差量并保留首次失败。

固定分析基线为 `a1250758d0fc14e8c7d5c827ece2c207a4d99aac`；下列为该 Git 原件行号，不是尚未释放的 r1 源码：

| 必改位置 | 具体工作及边界 |
| --- | --- |
| `src/annotation/delivery/live_pilot/usense.py:14–34,57–63` | 实现 `UsenseTransport.observe/build_commit/send_once` 和真实 `parse_business_receipt` 分支；注入窄 I/O 能力，不调用整个 UI 保存链。保留 offline codec。每个字段映射有固定源码出处；未证响应 schema 显式拒绝，不猜成功回执。 |
| `src/annotation/runtime/live_pilot/runner.py:11–68,71–120` | 从目前强制 offline 流程接入受明确事实/许可约束的真实分支，保持 baseline→fresh prewrite→plan→durable intent→claim→唯一 send→receipt→get→refresh→release。正式独立 fresh reopen 是另一方后续证据，不由作者的模拟 reopen 代签。UNKNOWN 及只读 reconcile 永不恢复发送资格。 |
| `src/annotation/quality/live_pilot.py:177–183,187–228,236–296` | 用具体证据引用/版本/请求及 phase/session 来源接入真实事实，保留独立目标、旧目录/题/序/框/全文、角色顺序几何、正文精确比较；不能把 `FAKE_BACKEND_READ` 改个标签便接受。 `global_order` 的全旧正文 AVAILABLE 门槛当前仍有效。 |
| `src/annotation/delivery/live_pilot/plan.py:24–80` | 绑定当前实际目录、明确合法末端插入点、唯一新题及具体 payload；去除真实分支的合成 PASS 理由和无证据 `global_max+1` 推定。不得把前端 DFS derived order 当服务端保存序号。 |
| `src/annotation/runtime/live_pilot/journal.py:26–39,94–128` | 直接复用固定书锁、持久化不可变 intent、发送前 claim、现有记录硬拒绝。测试使用明确离线隔离根；不新建第二 journal/执行器，不靠换路径/run_id/profile 绕旧 claim。 |

产品修改集中上述 transport/runner/quality/plan，可加一个小的端点 codec 支持模块及新的相关测试；journal/storage/readonly/native 守卫不为接线重写。必要合同模型变更须列出具体原因和受影响序列化/校验，不能放松全局 validator。

## 有据的 wire 与必要模型边界

固定脚本 SHA `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41` 的既有笔记给出普通 `VI→e8→E6e` 链（bytes 2753835/2752192/1083284）：POST `/qieti/api/annotate_pic/commit_unified_submit`。顶层白名单为 `file_id,target_directory_id,question_order,is_new_question_insertion,insert_after_order,annotations_upsert,annotations_delete_rect_ids,ocr_submissions,ocr_delete_zones,question_info,created_by`；框的完整白名单见依赖 notes 第 24 行，正文为 `zone,ocr_result,rect_ids,question_order`，题型为 `tishi,tilei,tihao`。新插入的 null 题序是该静态分支事实，当前合法插入点及服务端分配仍待绑定。

目标恰好一题、Q/W/W/W/W/A 六个新框，正文与 zone 的 rect_ids 明确关联；不 upsert/删除旧框或旧正文。空 zone 可能生成删除，必须逐项建模，不能把“空/缺失”一律当无操作。裁片 `data:` 可触发签名/上传及 403 重试（bytes 2744935/2745340/2745410）；当前不得继承 UI 上传/重试。先实现已存在合法非 data 路径的有据分支，缺路径明确待补；是否另需上传及精确次数/对象属于后续具体方案输入。回执禁止暂定题序 fallback（2754036），HTTP200、业务 code 或客户端 `append_at_global_end` 均不能独自证明完整写集、唯一新增、实际题序或保存成功。

明确 GET 读回：单题框 `/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/{file_id}/{order}`（1080407）、题信息 `.../get_question_info/{file_id}/{order}`（1080562）、正文 `/qieti/api/verify_annotation/get-ocr-annotation`（1081843；必需 `file_id,question_order,zone`，第四参数非 null 才加 `image_order_in_annotation_zone`）。当前只证明前端消费 success/ocr_result，不能编造返回 rect_ids/version/fullness。按当前真实 schema 决定正文与框关联证据；缓存/默认空串不是 readback。按 rect_ids 的读取实际是 POST，不得偷算 GET。

复用 `contracts/models.py` 的 EvidenceRecord/Capability（260–276）、PlatformSnapshot（280–310）、Action/ApplyPlan（404–440）。SYNTHETIC 与 OBSERVED 分开，能力 VERIFIED 必须有证据；internal question_id、服务端题序/稳定 ID、rect_id 分开，缺稳定映射不造 platform_question_id。原图 resource index、原图坐标和 save_page/保存坐标分开。当前 Action 只有 CREATE_FRAMES/UPDATE_FRAMES，首题正文责任须在已有相关计划/不可变 payload 中明确绑定；若确需最小模型补充，连同准确校验/序列化差量提交，不能以 CREATE_FRAMES 标签漏掉正文写集。BLOCKED 计划无可执行 actions，源码静态支持不能自动产出真实 READY。

## 真实事实到达后才可绑定

根接收本轮实际及正式核证后补齐：当前认证书 46007447/完整目录和目标库存、新题确未录入；末级目录及合法插入点；viewer14/173 的原图 SHA/完整解码尺寸、resource/source/save-page 与坐标转换；这道普通单选的当前正文/答案/六 bbox/合法题型；当前 wire/receipt/readback schema 和精确关联；裁片路径/上传必要性；旧正文保全证据；实际 policy、代码/候选/来源/题图/内容/plan/payload/manifest SHA 及各 phase 精确请求次数。当前 r1 的 derived resource/DFS order、passive canvas UNKNOWN、零样题正文不能升格为保存资格。

旧正文保全可由已证覆盖的聚合正文前后比较，或覆盖旧集合的权威摘要/版本，或服务端强制唯一新增及可独立核验完整写集满足原合同；必须证明所选路线。当前三者 UNKNOWN；全框、单样题正文、空删除数组、is_new 标志、前端版本号不够。不得降低原门槛、盲读全书或重放 Q22。代码可先实现精确类型与拒绝缺证分支；有必要只读补证时交根集中到具体请求计划，不自行探测。

首题候选可沿用原任务的普通单选线索，但历史答案/题序/旧 Q1 结果不当当前批准。其他三例 HOLD、Q22 不导航/抽样/回放、不书级提交、不自动推进余四题、不发 B/外部消息。

## 新离线差量与交付

集中验证：有据 payload/正文及六框关联；缺 schema/policy/保全/映射零发送；重复 claim/效果后超时不重发；伪回执、fallback 题序、旧记录变化及部分成功停止；真实分支的 fake 输入保留 SYNTHETIC 来源；get/refresh 不复用旧响应、独立 reopen 必须新会话且前驱释放；未知及释放失败不伪造成功；没有隐式上传/登录/额外 POST。必要新迭代允许，失败原件保留。

交付源代码、必要新 fake 测试/失败、完整 raw 依赖及 manifest/self SHA、精确待绑输入表和释放。形式为可用适配代码而非先造一次真实运行。根/同独立核固定候选；待实际事实和具体首题方案全部绑定并获得适用写权限后，才由作者一次 save/get/真实 refresh，释放后正式独立 fresh reopen 比较正文与六框及旧数据保全。此处没有实际预算、窗口、命令或 activation；持续只读 TLS 许可不代替保存授权。
