# A12 formal independent static review

**REWORK**. This fixed candidate is not qualified for the one reuse-only live observation.

Review chat: `01a15794-ad3e-7653-8f77-237fe06f8898`.

Base/workflow: `5e31abf791a69333384b0154c02a77da557e7a63`.
Product/driver: `7f3d42e31be29782f0e09e6c01cc8e277387747c`.
Final delivery: `0c30b365ed18b006bcab32bed4acb60869ff9f92`.

Candidate manifest SHA256: `f900aba89ff0b4d997be227e0a1488f5e856987604f17aeeea24a41292bc31d7`.
Delivery raw manifest SHA256: `9a69d1dbf5913a5a566c2eae1af68fe7b4356aba0e83e942fd0eb3016a54431c`.

All 22 raw files match fixed final Git bytes; all 21 non-self delivery-manifest members match size/SHA/OID. All 31,159 baseline mode/type/blob members remain unchanged. Nine candidate members match both product and final. Four provenance copies match exact source commits. Every Git call used GIT_NO_LAZY_FETCH=1 and core.longpaths=true. No product/driver was imported or executed.

## R01 [P1] Windows occupancy stdout framing rejects a successful zero count

The helper writes JSON plus a text newline at [product line565](D:/1800-worktrees/a12-formal-review/tools/headless_native_reuse_probe.py:565). CPython 3.9.13 initializes Windows stdout to translate LF to CRLF. The parent uses binary PIPEs and accepts only LF bytes at [line333](D:/1800-worktrees/a12-formal-review/tools/headless_native_reuse_probe.py:333). A normal successful count=0 therefore produces `b'{"count":0}\r\n'`, which cannot equal the required `b'{"count":0}\n'`. PYTHONIOENCODING does not change newline translation. This follows from the frozen code and [version-specific CPython source](https://raw.githubusercontent.com/python/cpython/v3.9.13/Python/pylifecycle.c), supported by [TextIOWrapper semantics](https://docs.python.org/3.9/library/io.html#io.TextIOWrapper); the helper was not run.

The live intent and claim are already consumed before [occupancy at line543](D:/1800-worktrees/a12-formal-review/tools/headless_native_reuse_probe.py:543). Even with no actual occupancy, the candidate will stop before navigation. The original suite enters open_owned directly and does not cover this branch. This is a fail-closed framing defect, not a platform or actual occupancy result.

A separately authorized correction must define consistent binary framing or strictly validate one decoded JSON record with explicitly permitted framing. It must retain rejection of malformed output, stderr, nonzero exit and nonzero count. This review does not authorize a fix, another candidate/suite, live startup or marker removal.

## R02 [P2] Final viewer decision can ignore a concurrent guard stop

At [lines365-378](D:/1800-worktrees/a12-formal-review/tools/headless_native_reuse_probe.py:365), guard state is checked before awaited password/viewer reads. A handler can set stopped/failure during either await, after which the code can set LOGIN_REQUIRED or AUTHENTICATED_VIEWER_OBSERVED without rechecking. Policy denial can leave failure=None; the result does not record the pre-shutdown stopped state, and finally sets stopped for cleanup. The normal return at [line394](D:/1800-worktrees/a12-formal-review/tools/headless_native_reuse_probe.py:394) can therefore indicate success after an unexpected network stop. If the early precheck instead raises, guard_failure is not copied because its assignment is only on the successful loop path.

Static possible ordering: the loop sees no stop; DOM await yields; a live request is denied or callback fails; the DOM read returns the expected visible viewer; the current code accepts the viewer without checking the new terminal state. This is static control-flow analysis, not an observed platform event. The suite uses expected_block=True and cannot certify this live branch.

A separately authorized correction must preserve the first guard failure and make it authoritative after asynchronous reads and at result serialization, distinguishing shutdown-only stopping. No fix or execution was performed here.

## Per-item results

The [JSON report](D:/1800-worktrees/a12-formal-review/review-output/report.json) contains exact input evidence ranges for all 17 checks.

| Check | Result | Evidence and practical limit |
| --- | --- | --- |
| C01 Identity/preservation/provenance | PASS | 22 raw inputs, 21 manifest members, 9 candidate members, 4 source copies, 31,159 old members |
| C02 One candidate/one suite | PASS finite records | Exclusive intent and claim; no independent rerun or host-wide census |
| C03 N1 | PASS original | GET entry1/final1; redirect pause precedes final server record; actual DOM marker |
| C04 N2 | PASS original | Entry observed, redirect ORIGIN_BLOCKED, ERR_BLOCKED_BY_CLIENT, denied log empty |
| C05 N3 | PASS original | Actual POST/WS calls1 each, POST settled/WS closed, endpoint POST0/Upgrade0 |
| C06 Per-hop native/WS controls | Supported for owned main page | Fetch Request-stage checks plus preconnect WS route; context route alone is not used as redirect proof |
| C07 Worker/SW/frame/popup | Static design only | Offline startup, SW blocked, unowned frame routing, debugger-paused child rejection; no child-case runtime evidence |
| C08 Allowlist/business boundary | PASS static | Fixed origin/static/session paths; no book/source/annotation or OSS access |
| C09 Default mode/one-shot marker | PASS static | Default inert, explicit binding, exclusive directory/intent/claim; failure never resets |
| C10 Dedicated profile binding | PASS static, not observed | Existing single directory metadata/reparse checks; actual profile not read |
| C11 Four-second occupancy | FAIL R01 | Scan wait bound exists; output framing rejects normal Windows success |
| C12 45-second/90-second limits | Static limits, expiry untested | Shared45-second navigation/readiness clock; worker75 plus bounded ordinary cleanup; HARD_SECONDS85 is metadata, not an independent watchdog |
| C13 Exact Windows Job/identity | PASS original/static | Job assigned before GO; exact handle/FILETIME, Job active1 then0; no external process kill |
| C14 Context/runtime/fixture release | PASS original | Context/runtime closed, two fixture threads exited, temporary profile removed |
| C15 Authentication/first failure | Partial, FAIL R02 | Protected marker+route+no password, but terminal guard state can race |
| C16 Login/TLS/credentials/policy | PASS static scope | Strict TLS, no login fallback or credential APIs, no extension-page operation |
| C17 Failure retention | PASS finite scope with R02 | Original lookup/seal failures retained; suite first-failure successors initialized NOT_RUN |

## Original event and release evidence

In the original [suite result](D:/1800-worktrees/a12-formal-review/docs/evidence/A12/native-reuse-probe/suite-run/suite-result.json:108), N1 entry arrived at 04:23:41.873144Z, the redirect pause was 41.875864Z, and final GET was 41.883494Z. N2 entry at 41.954130Z preceded the blocked redirect at 41.956577Z. N3 POST/WS blocks at 42.057054Z/42.063573Z occurred before shutdown; the page proof requires POST settled and socket closed. Final endpoint logs have exactly four allowed GETs and an empty denied log. These are the finite original results, not new runs.

Original worker PID60972 has creation FILETIME134369438183400248 both before and after, with exit0 observed. Parent duration was 4,422ms. The exact owned Job still had one member before final cleanup, then active0 and closed handles. All browser descendants are not asserted to have exited naturally. See [worker release](D:/1800-worktrees/a12-formal-review/docs/evidence/A12/native-reuse-probe/suite-run/worker-release.json:1). Original context/runtime closure, fixture thread exit and empty-profile removal are also recorded. Error/timeout release branches were not executed by this reviewer.

The source/link lookup failures and evidence-seal SyntaxError remain unchanged. No old quota was restored. A reviewer report-packaging long shell call was rejected by the tool before process launch with "blocked by policy"; it wrote nothing. The same authorized reports were then written using apply_patch and short metadata sealing. This was not a product/suite/platform attempt.

## Scope, release and next gate

Independent product/driver imports or runs, suite runs, browser/server starts, platform/profile/credential access and B messages: **0**. Only report.json, report.md and raw-output-manifest.json were written under review-output. No author/mainline/coordinator/old-evidence input was modified.

No reviewer browser, context, Job or fixture was acquired. This independent review is complete and stopped; original author release is supported by fixed records. The current candidate remains REWORK. No new candidate, suite, live startup, repair, retry or marker reset is authorized by this report. Other three cases remain HOLD and Q22 is not replayed.

Unverified: actual dedicated profile/fingerprint/occupancy/authentication, real platform transport, book46007447, saving/readback, all child-target variants and forced expiry/error-cleanup branches. Blocking native calls and filesystem/fsync stalls are not certified by the original short run. seal_delivery.py has byte identity only; its behavior was not executed or accepted.

Supporting interface references: [CDP Fetch](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Fetch.pdl), [CDP Target](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Target.pdl), [Playwright WebSocketRoute](https://playwright.dev/python/docs/api/class-websocketroute). These current definitions support interface semantics; they are not a full pinned browser implementation certificate.

The output manifest hashes both reports and all22 unchanged inputs, excluding its own hash. The final receipt supplies that third hash separately.
