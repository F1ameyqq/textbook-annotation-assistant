# 已有题的稳定身份批处理清单

入口 `tools/run_usense_reviewed_batch.py` 只接受 `UsenseReviewedTargetManifest/v1`。清单绑定实际捕获和具体审校候选；它不授予读取、保存、登录或 TLS 权限。必须先完成当前来源和本轮独立验收，再按当前调度执行真实保存。

```powershell
python tools/run_usense_reviewed_batch.py --manifest C:/project/private/targets.json --manifest-sha256 MANIFEST_RAW_SHA256 --baseline C:/project/private/capture --profile C:/project/private/browser --out C:/project/private/new-batch --authorization-reference CURRENT_EXACT_WRITE_PLAN --tls-approval-reference CURRENT_TLS_APPROVAL --preflight-only
```

`--preflight-only` 创建全新本地输出并核验，0 browser/平台。实际执行使用同样参数去掉该标志；读取授权不能因此成为写入授权。依赖在当前解释器中，或通过显式 `--dependency-dir` 指向已有目录；不会下载环境。`--repo` 若传入，必须与工具实际所属 checkout 相同。原 `--orders`、`--reviewed` 和前序批根参数不再选题。

清单顶层恰好为 `schema`、`book_id`（固定 `46007447`）、`baseline`、`targets`。

A25 传输修订后的当前 capture-summary 必须包含显式 `transport`。代理模式执行/预检另传 `--proxy-server http://127.0.0.1:port`，并与 summary 严格一致；该参数进入每个 writer 和 independent-reader 的 configure。省略为明确 DIRECT，不能继承系统代理。此字段变化不能用旧 capture 或旧配置替代当前新源。

|字段|内容|
|---|---|
|`baseline.capture_summary_sha256`|原始 `capture-summary.json` 的 SHA256；必须完整 `NATIVE_GETS_CAPTURED`、0 writes、context/runtime 已释放|
|`baseline.files`|`{capture_name: raw_sha256}`；集合与 summary.captures 完全一致，文件为 baseline/capture_name.json；逐个核 bytes、hash、HTTP 200、业务 code 0 和双层次数各 1|
|`targets`|1—6 个条目；批内 node/info ID、native order、同语义课时印刷号不能重复|
|`targets[].printed_question`|正整数，原图印刷号；不推算它与 native order 的差值|
|`targets[].semantic_lesson`|有审校依据的语义课时标签；不会据此迁移服务器目录|
|`targets[].target`|恰好 `book_id, lesson_directory_id, node_id, info_id, question_order`；全部与目录 DFS、原始 order、全框/本题框和 info 原件核对。`lesson_directory_id` 始终是实际服务器父目录|
|`targets[].source_pages`|该目标使用的已捕获来源页整数列表，1—8 页；所有现有框 page_index 必须在内；source 及各 page 响应必须齐备|
|`targets[].candidate`|`{"path":"绝对文件路径","sha256":"原件摘要"}`；candidate 内容恰好为 `target, approved_changes`，target 必须与清单严格相同|
|`targets[].review_evidence`|`{absolute_path: raw_sha256}`，恰好覆盖所有 approved_changes 的 source_ref/review_ref。每个文本仍按既有单题协议绑定 source_sha256、reviewed_text_sha256；审校结论本身由具体独立验收核对|
|`targets[].previous_acceptance`|首次更新为 null；显式修订为 `{"path":"绝对acceptance.json路径","sha256":"原件摘要"}`。现有严格验证器逐一核原回执、原始前后读回、配置、独立进程、时序、来源及 accepted ledger，再派生 revision intent；不能拿一个 ACCEPTED 字符串绕过 UNKNOWN|

ledger 固定为原 profile 父目录下的 `usense-existing-ledger`，必须已存在。缺失 ledger 是待对账输入缺口，入口不会自动新建空 ledger、迁移或清理历史标记。任何既有稳定身份分支若没有显式合法前序，首写前拒绝。全部候选、来源、审校、原始捕获、生成后的计划及待执行目标 ledger 在启动各进程前再次核摘要。

输出按 `target-<node_id SHA256 前24位>` 建子目录，不按旧 qN 名字发现目标。每个目录仍有原 `plan.json`、`review-evidence-hashes.json`、配置、原始进程输出、进程结果和 acceptance.json，因此现有单题修订验证器可继续引用具体 acceptance。整批预检失败时每个 supplied 条目标为 `NOT_RUN` 且 identity_validated=false；执行失败时当前项为 STOPPED/FAILED，其后逐项 NOT_RUN。

真实 writer 仍对单题先完整重读，再以稳定身份 ledger 一次发送；成功且退出后才另进程读回。当前批入口保存子进程 PID、时间和原始输出，但不宣称它自身证明 Windows 所有后代进程退出；平台执行还需外层持有器和具体资源释放证据。没有来源、没有固定独立结论或存在 UNKNOWN 时，不执行保存。
