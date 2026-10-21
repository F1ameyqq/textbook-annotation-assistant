# A21 一次专用登录与同会话书源读取：具体决定提案

状态：READY_FOR_DIRECT_USER_DECISION。正式独立及根调度已完成有限离线接受，本提案已固定；它尚不是用户决定，未创建 activation 或启动真实会话。

## 本次请求

允许本 A21 新轮使用原专用无头 context，临时忽略 HTTPS 证书校验，运行时直接读取本机既有配置，通过官方 UI 最多提交一次登录；认证成立后在同一个 context 完成书 46007447 的六个固定 GET 和 viewer 14/173 两图读取。最多一次启动、一个 context、两个固定主导航，900 秒包含释放。

本轮仍包含**发送既有用户名和密码**。A17「一直批准」覆盖同类只读 context TLS 例外，不能单独授权此次凭据发送；A20「本轮一次登录及读取」已消费，不能借用。无需提供或在聊天显示密码。既有证书证据存在主站名称不覆盖与过期问题，未追加探测；本轮按证书不能可靠确认服务端身份处理。context 例外影响主站和已准 OSS，既有会话信息可能随获准请求发送；用户名/密码仅允许向固定主站登录接口提交。

新增的工程变化只有窄静态图片分类及 A21 身份绑定。已证 PROTECTED 可先于 STATIC 误拒以 login 等词开头的静态 basename；**A20 实际路径及是否属于此类仍 UNKNOWN**，不能承诺本轮一定恢复认证。原认证、业务读取、两层守卫、截止和释放流程保持。

## 本轮边界

| 项目 | 固定范围 |
| --- | --- |
| 原 context / 时间 | 1 个 / 900 秒，含启动、登录、读取和释放 |
| 固定导航 | 依次 `https://www.usense.com/qieti/login`、`https://www.usense.com/qieti/annotateUnified`；各最多 1 个 Document；其他 Document/reload/redirect 拒绝 |
| 官方 UI 登录 | 原主框、原站及确切表单成立，点击前记一次性意图；最多 1 次实际提交；两层各一次预留约束同一请求 |
| 唯一登录 POST | `https://www.usense.com/qieti/api/user_login/login`；JSON 仅 `username`、`password`，值与本轮内存配置一致 |
| 配置 / profile | live 获准后才读 `D:/1800/.local/usense-login.json`；原指纹 `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00`；不复制/替换 profile、不注入 token、不改日常 Edge |
| session GET | `profile`、`config/permissions`、`config/teams`，均位于 `/qieti/api/user_login/`；无 query/redirect，每路径 LOGIN、VIEWER 各最多一次，共最多六次 |
| 六个书源 GET | 下列六个固定 URL 各最多一次，不自动补发 |
| 原图 | viewer 14/173 各一次；由本轮源响应注册路径，限定 `/upload_images/46007447/`；仅原站或 `https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com` |
| version / 排除 | 原站 `/qieti/version.json?t=<原样13位时间戳>` GET 最多一次；原限定排除共享 16 事件，双层保守计数，第 17 次停止；CDN Script 仍拒绝发送 |
| 写入与重试 | 业务写入、上传、OCR、样题、送审送交均 0；refresh POST、自动重发、重复登录及未知 API 拒绝 |

六个业务 GET 均使用 `https://www.usense.com`：

1. `/qieti/api/claim_book/books?page=1&pageSize=10&id=46007447`
2. `/qieti/api/annotate_ocr/directory/get?file_id=46007447`
3. `/qieti/api/annotate_pic/get_manual_annotations_unified/46007447`
4. `/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre`
5. `/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=mr_pre`
6. `/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=173&annotationType=mr_pre`

验证码/MFA、拒绝、未知登录结果、意外错误、窗口或占用冲突即停止并固定证据，不重试。若候选可验证当前已认证事实，可走 0 次凭据提交分支；URL、HTTP200、登录 POST200 或 SPA 跳转本身不证明认证。六业务 GET 加两图不等于全部 HTTP 请求数，审计事件数也不等于发送数。认证后同 context 直接完成读取，不另拆诊断轮。

## 八项窄图片规则

| scope 字段 | 候选固定值 |
| --- | --- |
| `static_image_path_pattern` | `/(?:qieti/)?assets/[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*\.(?i:png\|jpg\|jpeg\|gif\|svg\|ico\|webp)`，完整匹配规范单 basename |
| `static_image_method` | `GET` |
| `static_image_resource_type` | `Image` |
| `static_image_origin` | `https://www.usense.com` |
| `static_image_query_allowed` | `false` |
| `static_image_redirect_allowed` | `false` |
| `static_image_original_main_frame_required` | `true`，两层真实框身份关联仍须成立 |
| `static_image_precedes_basename_protection` | `true`，仅此窄类先判定，不把整条 STATIC 前移 |

新例外不覆盖 `/static/`、嵌套目录/API 路径、编码/反斜杠/点段/空段/重复分隔符等歧义路径、Document/XHR/Fetch、登录 POST 或其他方法/来源；既有正常 static 范围保持。此分类改变不能冒充已确认实际阻断路径用途。

## 精确绑定

| 绑定 | 值 |
| --- | --- |
| task / scope | `A21` / `AUTHENTICATION_RECOVERY_STATIC_IMAGE_CLASSIFICATION` |
| run_id / 执行 | `A21-static-image-01a15c27-595a-70e0-88b4-fe064550c884` / `01a15c27-595a-70e0-88b4-fe064550c884` |
| 正式独立 | `01a15c27-a798-7e63-a879-a1bfd2d56b5a`；host local，已封存释放 |
| workflow | `82c2b7ee62a126bb74bc08c2d2dedbe5c556d1ca` |
| base / 产品 / final | `f45fa86789b8f154d03e8c4807412a2161d678f6` / `b65d85156b56840d6ae055880d4d707b998e2ff3` / `cf03910d9554d6e3198c59494de2d4ce7bf7ad80` |
| 候选 SHA256 | `f0710e872776c452728e68710052c8580ae45fc4ea55cbff7fddb11a11d18657` |
| 作者清单 SHA256 | `3cfc649370032e80a52c763e3c7c18b741358d2b5bfe38e14d89b3fcf2c9b099` |
| 固定输入清单 | `D:/1800/docs/evidence/coordinator/a21-fixed-delivery/input-raw-manifest.json`，76 成员；SHA256 `7e0e2bf511ff325e9c1ac0e723d2edfefedf77f96f7e8c49ddc9e35d5d172431` |
| 固定 plan | final 的 `docs/evidence/A21/static-image/plan.md`；SHA256 `f0b97e70026f9d1eed2f2b81b8214643314455ba1a2f6c89da782d88132cf665` |
| 独立机器报告 | `D:/1800/docs/evidence/coordinator/a21-independent-closure/independent-result.json`；ACCEPTED_OFFLINE_ONLY；SHA256 `2fa24bc6c8cb1cd7a898a502bed0ba678b331ab6c04cd0732eff452ea3d9523a` |
| 独立报告 SHA256 | `8fdc634b05e6b6ca419a3d7f245ae190b56675226d923377ac897289788ec222` |
| 独立清单 SHA256 | `1553bbfc70a3f61e196624c6c5df4d0a07d5cee1c0604dc48d93b35c750eb015` |
| 独立释放 SHA256 | `ef856b628d2e4c1509c67b94858b5dc1e74edf85148be1e5d23ee3689868e7d4` |
| 调度接受提交 | `09b25a90abc3645915f0f04113541aa83dfb9afe` |
| 正式提案与问询记录 | 本文件为固定提案；其 SHA 及原问题保存在 `docs/evidence/coordinator/a21-user-decision-request/request-intent.json`。等待直接用户答复。 |
| 决定 / activation / 输出 | `D:/1800/docs/approvals/A21-static-image-user-decision.json` / `D:/1800/.local/stages/a21-static-image-activation.json` / `D:/1800/.local/stages/a21-static-image-live` |
| 实际窗口 / 新一次性标记 | 获批后首次具体派发时固定新900秒窗口及本阶段标记；不沿用A20窗口/标记，不重建或延期。 |

正式独立新suite16/16（296ms）、五组独立控制5/5（141ms）；根已核22报告成员+self、76固定输入、27候选依赖及47项scope完整原值，测试后输入不变。结论仅ACCEPTED_OFFLINE_ONLY / BOUNDED_OFFLINE_PREFLIGHT_ONLY。首次文档helper参数错误保留为标明来源的转录，原raw stderr未捕获；只改helper，两组测试各运行一次。实际DOM、CDP请求及服务端认证仍未实测，A20路径用途/根因和旧UNKNOWN保持。三个产品模板仍为不可执行原件；本阶段直接决定到达后，根调度才把实际报告及决定原bytes hash、新窗口、原profile指纹绑定A21 activation。唯一实际轮之后仍需同正式独立验收事实与释放。本提案不授权首题保存；其他三例 HOLD、Q22 不导航/样题/重放、0 B 或外部联系人消息保持。

## 47 项 scope 原值附录

以下为正式独立及根核证的47项固定scope原值，用于绑定本次具体决定；本附录不是可执行决定或activation。

```json
{
  "task": "A21",
  "run_id": "A21-static-image-01a15c27-595a-70e0-88b4-fe064550c884",
  "workflow_commit": "82c2b7ee62a126bb74bc08c2d2dedbe5c556d1ca",
  "scope": "AUTHENTICATION_RECOVERY_STATIC_IMAGE_CLASSIFICATION",
  "candidate_manifest_sha256": "f0710e872776c452728e68710052c8580ae45fc4ea55cbff7fddb11a11d18657",
  "sample_limit": 0,
  "automatic_schema_confirmation": false,
  "fixed_business_get_count": 6,
  "original_get_count": 2,
  "new_live_limit": 1,
  "context_limit": 1,
  "navigation_limit": 2,
  "total_seconds": 900,
  "business_get_limit_per_url": 1,
  "original_limit_per_viewer": 1,
  "navigation_sequence": [
    "https://www.usense.com/qieti/login",
    "https://www.usense.com/qieti/annotateUnified"
  ],
  "login_post_url": "https://www.usense.com/qieti/api/user_login/login",
  "login_json_keys": [
    "username",
    "password"
  ],
  "credential_config": "D:/1800/.local/usense-login.json",
  "required_profile_fingerprint": "b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00",
  "session_get_limit_per_path_per_phase": 1,
  "session_phase_limit": 2,
  "refresh_post_limit": 0,
  "automatic_request_resend_limit": 0,
  "credential_transmission_requires_direct_A21_decision": true,
  "static_image_path_pattern": "/(?:qieti/)?assets/[A-Za-z0-9][A-Za-z0-9_-]*(?:\\.[A-Za-z0-9][A-Za-z0-9_-]*)*\\.(?i:png|jpg|jpeg|gif|svg|ico|webp)",
  "static_image_method": "GET",
  "static_image_resource_type": "Image",
  "static_image_origin": "https://www.usense.com",
  "static_image_query_allowed": false,
  "static_image_redirect_allowed": false,
  "static_image_original_main_frame_required": true,
  "static_image_precedes_basename_protection": true,
  "login_submission_limit": 1,
  "business_write_limit": 0,
  "upload_limit": 0,
  "ocr_limit": 0,
  "old_budgets_restored": false,
  "executor_thread_id": "01a15c27-595a-70e0-88b4-fe064550c884",
  "output_directory": "D:/1800/.local/stages/a21-static-image-live",
  "activation_path": "D:/1800/.local/stages/a21-static-image-activation.json",
  "decision_path": "D:/1800/docs/approvals/A21-static-image-user-decision.json",
  "report_path": "D:/1800/docs/evidence/coordinator/a21-independent-closure/independent-result.json",
  "excluded_static_event_limit": 16,
  "version_check_limit": 1,
  "standing_tls_permission_path": "D:/1800/docs/approvals/A17-excluded-static-user-decision.json",
  "standing_tls_permission_sha256": "f5ceacf9028f773ead882f3e6601004c2c3e28171be31abb85c5be99a1d67b46"
}
```
