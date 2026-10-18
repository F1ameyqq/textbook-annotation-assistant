# A03 P2-R11-R1 archive closure review

2026-10-18 (Asia/Shanghai). Verdict: **ACCEPTED_FOUR_CRASH_CUTS_ONLY**.
This is the one separately authorized file-only closure of the completed R11 independent run. Functional calls: **0**. New SQLite connections/audits: **0**. No old scripts, tests, PRE/POST, run_plan or reconcile were executed.

Target `cc5966dc58c62017a27266c40ca0cedc5c68485c`; base `1c26b4a8eb378af33e57668472d2071e9ea6afff`; closure workflow `188fed05cd51789521b27efb04b2426f630571d0`.
Closure task raw SHA256 `9565f3e8cd86373ddda5cdf728cf5e07ec07347dfa1824319a53b20fcc5cf7c1`.
The original R11 REWORK report, both archive failures and its one correction remain unchanged. This new verdict closes only the four original V02/R03 singleton crash cuts. Whole A03, product integration and I01 remain unreleased; B mapping is not jointly confirmed.

## Basis and separate historical outcomes

[Original REWORK report](A03-P2-R11-crash-cuts-review-report.md)
has SHA256 `a964ef76d836c9935dd391ad72e073f49395196ffbcd5aa43040a8cd5498127c`. The original manifest is `eff77340f2577d1cf66eaa3c69ad4609b2673b87002951333d7f856b158f494c`; original release record is `eded396dddfa7b46d1b4e0c35bd5ed9af9853ba9d2ad89ce955e36c5d6c98d4a`.
All1209 original package/report files are bound to workflow raw Git blobs and their original SHA256 manifest. All677 original raw inputs and77 source seeds remain byte-identical. New files reference the old package; no historical corpus or database seeds are copied.
The decision uses the original handoff/execution criteria, four actual case results, complete recorded SQL/event/formal-reference boundaries, actual process/import records and stage binary digests. It does not adopt an internal audit status as acceptance by itself. [Detailed coverage](../evidence/A03/review/P2-R11-R1-archive-closure/coverage-map.json) and [Completed audit references](../evidence/A03/review/P2-R11-R1-archive-closure/completed-audit-reference-index.json).

## Four bounded conclusions

| Case | Original cut | Existing crash/query PID | Effect | Result | Actual plan state |
|---|---|---|---|---|---|
| F1 | BEFORE_INTENT_COMMIT | 39832/90 then 33332/0 | 0 to 0 | Query only; no intent/permit/formal result | RUNNING |
| F2 | AFTER_DISPATCH_STARTED | 31204/90 then 63372/0 | 0 to 0 | One reconcile; ABSENT / NOT_APPLIED | INTERRUPTED |
| F3 | AFTER_READBACK_CAPTURE | 70400/90 then 42688/0 | 1 to 1 | One reconcile; MATCH / APPLIED | FINISHED |
| F4 | AFTER_RECEIPT_COMMIT | 55052/90 then 37584/0 | 1 to 1 | Query only; durable APPLIED receipt retained | FINISHED |

Each original case ran once from a fresh isolated path. The same legitimate owner/PRE context reached the existing FaultController cut through normal run_plan and real os._exit90. Parent wait preceded the different reopened PID; original marker, persisted facts, instance and owner/generation agree. No new process competed for business ownership in this closure.
F1 distinguishes accepted/reserved plan/action from no committed intent/permit/effect. It did not fabricate UNKNOWN or a NOT_ATTEMPTED receipt. F4 preserves the durable plan/action/intent/fact/receipt binding and ATTEMPTED fact; no project/reconcile/resolution or replay was performed. Query bytes are unchanged in both cases, and their original dead generation1 ACTIVE rows were not cleared.
F2/F3 preserve pending intent, consumed permit and DISPATCH_STARTED before any formal result. Each saved a formal UNKNOWN before its single original max_attempts=1 reconcile. Fresh read sequences are2 to3 and3 to4, with exact source/target/scope/store/session/plan/action/digest/intent/observation/snapshot/readback bindings. The original UNKNOWN and MAY_HAVE_BEEN_ATTEMPTED fact remain. Effects stay0 and1; an absent effect is not treated as proof of no call. Generation2 was normally released. No old action was replayed.
All four recorded POST/Batch/native_report_reads counts are0. Reports were not generated to conceal their absence. Parent90-second, business45-second, observation2-second, barrier5-second, lease10-second and original recovery bounds were unchanged in the frozen runs. None were invoked again here.

## Exact formal references

### F1

Plan: `plan-r11-F1` / `942f7814686325960b841568fc009b191ecaba0a068e99326aa68974419e241f` (revision 1, ApplyPlan).
PRE: `pre-r8-r3-F1` / `26138c51e8bad6d10aaeadda1f5585c1fbe242981aef2d95ff84f71de50ae494` (revision 1, CheckReport).
Intent: none.
Receipt: none.
Resolution: none.
Actual attempt fact: `None`.

### F2

Plan: `plan-r11-F2` / `cc33adda0efec8fb4118202537aa2d356f3f3ffe72dc5644a512ad209736b3aa` (revision 1, ApplyPlan).
PRE: `pre-r8-r3-F2` / `6d61b97815a07e9da8821283b8ff208aeb83536564d45826474d21872448f734` (revision 1, CheckReport).
Intent: `writeintent-e889c97581ca4c60b4791e7856fd59a8` / `afee4a051b37549afaa6f9edf15e7c5eb2f90444d573ea02017e172fbaf9f1f4` (revision 1, WriteIntent).
Receipt: `executionreceipt-ce9f7ac370264c33a41569affde91876` / `56b16d9f34f3bb5963dc28af080d054d3355464db0ed0d01199ba04f9bd95871` (revision 1, ExecutionReceipt).
Resolution: `resolution-882a54c273eb446db2278683406a409b` / `ed90ae1bef5125b3c90c4c586533c5773e5d12964eb791fe5e101777d41ad58d` (revision 1, ReconciliationResult).
Actual attempt fact: `MAY_HAVE_BEEN_ATTEMPTED`.
Observation `native-observation-52a1eee91222412e90293aeaee1a699c`, sequence 3; snapshot `snapshot-a03-7c8675cdf7f004171cc2662b` / `4c4a3b299f1dc2b37aea6a65645378e39ffa201dbd335a4ec7d78058429ac9b6` (revision 1, PlatformSnapshot).
Readback Resource `assets/runtime/810bd82b27dd23b1f58b6e84fb0b6e164e41dcd63bb6596efa294cc5033e0390.json`, SHA256 `810bd82b27dd23b1f58b6e84fb0b6e164e41dcd63bb6596efa294cc5033e0390`. Original receipt is null; replay_allowed=false.

### F3

Plan: `plan-r11-F3` / `add4bd6964b8bf024793fba4b6907593fd6a8ab8dcd9fc46d13c4c487acb0b51` (revision 1, ApplyPlan).
PRE: `pre-r8-r3-F3` / `5eb1f187f973d1bff114fc90457015650a31793ffe4d92895a2cc882c3dd8484` (revision 1, CheckReport).
Intent: `writeintent-fed3bbb5a2cc49a186a1b89163ad2365` / `1c49f846272e95601482dbf028182a33b9bc0ef1fc0aaf4c03bedb6b419a5f32` (revision 1, WriteIntent).
Receipt: `executionreceipt-694ca7399ff04d87af11dace4df16c20` / `697c74da15c4045209dd8c8e4fe6942c5f5e84c77e5e479d7405c69961ec60d1` (revision 1, ExecutionReceipt).
Resolution: `resolution-de7f521abbd8480189885245da0601ba` / `a9b007915e6a3a6a389d9afa31434949ba8e9e78839e06549467fc1fc6ece52e` (revision 1, ReconciliationResult).
Actual attempt fact: `MAY_HAVE_BEEN_ATTEMPTED`.
Observation `native-observation-3d495ebb7a694f74b861d3b2879c9e7f`, sequence 4; snapshot `snapshot-a03-9552d7d7b18fbf8b6ee4b8be` / `116ab0e4aeac72b9516eff4a63fd198980919a0f337bd750bc2804ce361e414e` (revision 1, PlatformSnapshot).
Readback Resource `assets/runtime/8e5d977f4dce05d4895550ae2303fcf0ffa79b5800d243e0c5bf89d03fc01a03.json`, SHA256 `8e5d977f4dce05d4895550ae2303fcf0ffa79b5800d243e0c5bf89d03fc01a03`. Original receipt is null; replay_allowed=false.

### F4

Plan: `plan-r11-F4` / `09f558a498b869d90b1c064d676c1a20ad4f9413ce6e156fe8abcd06512295a6` (revision 1, ApplyPlan).
PRE: `pre-r8-r3-F4` / `8cbac5c79f24469860d50756900beedc63f4c5b0c85be997834de5b0498f4fc9` (revision 1, CheckReport).
Intent: `writeintent-87a8d4f73a574194a619fd7436b29a33` / `41d43da12f3098b40785873ff1e20547f62f5d2a45596678f434a9f65e043a07` (revision 1, WriteIntent).
Receipt: `executionreceipt-33b9a2daecfb4c45b6f07775720f72f2` / `558a87740b1a7152117e37f21400c622c7106f8aa723fe8fb09b270e403e44b9` (revision 1, ExecutionReceipt).
Resolution: none.
Actual attempt fact: `ATTEMPTED`.

## Actual stage originals and author limit

[Stage file index](../evidence/A03/review/P2-R11-R1-archive-closure/stage-file-index.json) lists all32 actual independent stage SQLite files with paths, SHA256, capture-file digests, capture PID, writer/keeper flag and times. Every case has pre-fault, cut-after-wait and after-query/recovery; F2/F3 additionally have pending-before-projection and UNKNOWN-before-reconcile. Original capture records and completed immutable-copy SQL rows agree. This round reads frozen records/hashes only and does not repeat the64 completed SQL audits.
Pre-fault capture had its own keeper active; later captures had no active writer/keeper. The two databases were read sequentially, not as an atomic cross-database snapshot. No missing database was constructed.
**Author F2/F3 intermediate binary originals remain absent.** Their full SQL rows, contemporaneous hashes, event chains and immutable artifacts/Resources support only their declared layer of evidence. Their missing intermediate raw hashes cannot be rederived from nonexistent files. Author pre-run/final originals and F1/F4 unchanged cut/final bytes exist. The32 new independent stage originals satisfy the independent review stage-preservation requirement; they cannot retrospectively repair the author package.
This limitation is preserved separately from the four independent runtime conclusions and is not waived or relabeled complete. [Author declaration](../evidence/A03/review/P2-R11-crash-cuts/input/target/docs/evidence/A03/execution/P2-R11-crash-cuts/stage-binary-preservation.json).

## Archive failure and this authorized closure

Original process-audit-01 exited1 because the returned observation wrapper was compared directly with its persisted body. Its single permitted static correction compared all body fields and validated the four extra Resource/path fields against actual bytes. Process-audit-02 exited0. Both versions, original stderr and the correction record remain unchanged.
Original report-01 PID54900 exited1 before the normal report/coverage-map output, with a source-decoding SyntaxError recorded at line35. Static inspection now establishes that the retained script and preregistered snapshot are identical and strictly decode as UTF-8. Therefore the statement that the retained file is invalid UTF-8 is not established. The historical interpreter diagnostic is retained verbatim; its exact interpreter-level cause is not reproduced or inferred. This difference in diagnostic description does not change or contradict any recorded crash-cut, transaction, observation, process or database criterion. [Encoding facts and output gap](../evidence/A03/review/P2-R11-R1-archive-closure/encoding-and-output-gap.json).
The original round correctly stopped at its correction limit and remains REWORK. This separately registered one-round closure supplies a new explicitly UTF-8 decoded/compiled generator, this report and coverage map from already frozen evidence. It does not fix or retry either old script or change any old byte. No new metadata correction or retry is made.
The new [Source preflight](../evidence/A03/review/P2-R11-R1-archive-closure/source-preflight.json) records strict UTF-8 decoding and compile-only validation before the single file-only child started. Git commands and that child are preregistered with actual source/input SHA, argv/cwd, timeout, raw streams and waits; every child limit is at most45 seconds.

## Preservation, scope and delivery

[Original package byte preservation](../evidence/A03/review/P2-R11-R1-archive-closure/original-preservation.json) covers all1209 original files before and after this closure, including the old report, manifest, failed script/snapshot and outputs. [Release proof](../evidence/A03/review/P2-R11-R1-archive-closure/process-release.json) records only actual current-round Popen children; historical33 waits remain historical evidence, not a scan of possibly reused PIDs. [New manifest](../evidence/A03/review/P2-R11-R1-archive-closure/sha256-manifest.json) covers this report and all new files, excluding only itself.
The old AFTER_INTENT_COMMIT, lost-receipt N1, R9/R10, old R3 N7, other fault cuts, full suites, multi-action/mixed-tail cases and all other original gaps were not rerun or waived. No product/source/schema/profile/adoption/pin/oracle/producer/verifier/dependency/author/old-evidence/state files were modified. No integration, INTEGRATED registration, commit or push was performed. Coordinator functional acceptance/registration is still separate.
Functional calls0; new SQL connections0; closure rounds1; corrections/retries0. No agents/delegation, network, platform/browser/profile/credentials, OCR/paid models, installation, B contact, A05 question22 or book submission. User model/thinking preserved.
Field reset: `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`. No execution, variant, delegation or retest recommendation.
