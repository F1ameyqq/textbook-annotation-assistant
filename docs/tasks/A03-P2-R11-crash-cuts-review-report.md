# A03 P2-R11 independent review

2026-10-18 (Asia/Shanghai). Verdict: **REWORK**. The four independent functional cases completed once, and the retained database and process audits passed. Final acceptance closure stopped after a second post-functional archive error. The handoff permits at most one static metadata correction; that allowance had already been used. No second correction or retry was made.

Target: `cc5966dc58c62017a27266c40ca0cedc5c68485c`.
Direct parent/base: `1c26b4a8eb378af33e57668472d2071e9ea6afff`.
Review workflow: `0b843a49f394e962e4113ab3b04375e4f4698008`.
Handoff raw SHA256: `485724252e85c897810b21c91732301c4cb9dd8defc0a683975967ca365c6ef1`.

## Supported functional conclusions

| Case | Original fault | Actual independent result | Effects | Actual plan state |
|---|---|---|---|---|
| F1 | BEFORE_INTENT_COMMIT | Real exit90; new PID open/status/query only. Plan/action reserved, no intent/permit/result receipt. No fabricated attempt conclusion. | 0 | RUNNING |
| F2 | AFTER_DISPATCH_STARTED | Real exit90; original pending and formal UNKNOWN preserved. One reconcile, max_attempts=1. Fresh read sequence 2 to 3, ABSENT / RESOLVED_NOT_APPLIED. | 0 to 0 | INTERRUPTED |
| F3 | AFTER_READBACK_CAPTURE | Real exit90; original pending and formal UNKNOWN preserved. One reconcile, max_attempts=1. Fresh read sequence 3 to 4, MATCH / RESOLVED_APPLIED. | 1 to 1 | FINISHED |
| F4 | AFTER_RECEIPT_COMMIT | Real exit90; new PID open/status/query only. Durable APPLIED result and exact receipt/action/intent/fact bindings retained. No resolution or replay. | 1 | FINISHED |

All four functional parent processes exited0, all four crash children exited90, and all four reopened children exited0 without timeout. Parents waited for each crash PID to exit before starting the different query/recovery PID. F2/F3 retain MAY_HAVE_BEEN_ATTEMPTED before and after reconciliation; F4 has ATTEMPTED. An absent effect was not treated as proof of no call. F1 has no formal attempt result and none was created.

F1/F4 runtime and target bytes are identical before and after querying. Their original dead owner rows remain generation1 / ACTIVE; no locks or business state were cleared. F2/F3 used normal bounded claim_current acquisition and finished with generation2 released. Effects and original DISPATCH_STARTED/consumed-permit records show no replay. POST, Batch and native_report_reads are all zero in all four cases; no reports were published to fill their absence.

The [case and boundary audit](../evidence/A03/review/P2-R11-crash-cuts/case-and-boundary-review.json) contains actual PIDs, owners, instances, complete SQL rowsets, event chains, formal artifact four-tuples, entity bytes, Resource hashes and the new observation/snapshot/resolution bindings for the author and independent cases. Its ACCEPTED_FOUR_CRASH_CUTS_ONLY status records the successful bounded case audit; it does not override this final REWORK verdict.

## Frozen source and actual stage preservation

[Raw Git verification](../evidence/A03/review/P2-R11-crash-cuts/delivery-byte-index.json) verified 580 added blobs and all579 author manifest entries, and preserved all32413 old mode/type/blob entries. The target is a direct child of base. The [input index](../evidence/A03/review/P2-R11-crash-cuts/input-index.json) has677 necessary exports. The fresh isolated source workspace has77 seed files and no author database or historical validation seeds. Six schema pins and23 implementation pins passed static verification.

The [complete driver diff](../evidence/A03/review/P2-R11-crash-cuts/driver-diff.patch) adds only isolated path selection and stage byte capture to the complete frozen R11 driver. The [preregistration](../evidence/A03/review/P2-R11-crash-cuts/driver-preregistration.json) and [static review](../evidence/A03/review/P2-R11-crash-cuts/static-review.json) precede the first functional call. Normal frozen helpers were imported; no AST/exec slicing, monkeypatch, SQL business writes, fabricated clocks/PIDs/leases or private authority were used.

The original source cut locations are storage:615, storage:1101, recovery:116 and storage:739. They respectively precede intent transaction entry, follow committed permit consumption/DISPATCH_STARTED before effect authorization returns, follow execute readback before result commit, and follow durable receipt projection before POST/Batch publication. The original FaultController performed os._exit90. Parent watchdog90 seconds, business child45 seconds, observation2 seconds, barrier5 seconds, lease10 seconds and original recovery deadlines were unchanged.

Independent execution retained32 actual stage SQLite files: pre-fault, cut-after-parent-wait and after-query/recovery for every case, plus pending-before-projection and UNKNOWN-before-reconcile for F2/F3. Copies were made before subsequent mutations. Each has a capture.json with exact paths, hashes, nanosecond order, full SQL and own writer/keeper status. The pre-fault keeper was active; other captures had no active writer/keeper. No sidecars were present. The two databases were read sequentially and are not claimed to be an atomic cross-database snapshot.

The [database audit](../evidence/A03/review/P2-R11-crash-cuts/case-and-boundary-review.json) made64 own-copy immutable/query_only database examinations: the actual author and independent pre-run/final files, plus32 independent stage files. All quick_check results were ok and source/copy bytes remained unchanged. No author active database was connected and no SQL-to-SQLite reconstruction was made.

## Author evidence limit

The author's [original preservation declaration](../evidence/A03/review/P2-R11-crash-cuts/input/target/docs/evidence/A03/execution/P2-R11-crash-cuts/stage-binary-preservation.json) remains unchanged. F2/F3 intermediate cut and pre-reconcile SQLite binary originals are absent. Full SQL rows, contemporaneous raw hashes, events and immutable artifacts/resources support limited review, but the absent binary files cannot be independently rehashed. Author pre-run/final binaries exist. F1/F4 final bytes match the author's cut hashes.

The new independent stage evidence supports this review's four functional conclusions. It does not retrospectively repair the author's missing original files. No author rerun or supplemental functional round was requested or performed.

## Process evidence and archive stop

The [process/import audit](../evidence/A03/review/P2-R11-crash-cuts/process-and-import-review.json) passed with19 frozen author process records,14 actual independent nested children and492 actual module import records. Four crash-finally import files are absent as expected after os._exit; the actual pre-fault imports were used without fabricated exit evidence. Native observation workers are bound by exact module snapshots, request hashes, parent PIDs, stdout PIDs, every persisted observation field and actual Resource bytes.

The first post-functional metadata failure was process-audit-01, PID19828 / exit1. The audit incorrectly compared the returned observation wrapper, which has four extra Resource/path fields, with the stored observation body. The [single permitted static correction](../evidence/A03/review/P2-R11-crash-cuts/post-functional-metadata-correction.json) preserves the original source snapshot and [raw error](../evidence/A03/review/P2-R11-crash-cuts/runs/process-audit-01/stderr.log). Based on persistent.py:476-479, the corrected file-only audit compares every persisted field and validates the four extra fields and resource bytes/hashes/JSON bodies. Process-audit-02, PID68184, exited0. It made no product calls.

The second archive error was report-01, PID54900 / exit1: a source encoding SyntaxError in write_report.py before any report or coverage-map output was created. The failed [script snapshot](../evidence/A03/review/P2-R11-crash-cuts/runs/report-01/entry-source.py), [raw stderr](../evidence/A03/review/P2-R11-crash-cuts/runs/report-01/stderr.log) and completion record are retained unchanged. That script was not corrected or retried. Normal acceptance/report generation stopped. This failure report and failure manifest preserve the completed evidence and the unclosed archive gate; they do not bypass the one-correction limit.

Two read-only discovery probes for nonexistent paths are separately recorded in the [probe note](../evidence/A03/review/P2-R11-crash-cuts/read-only-probe-note.json). No missing files, PIDs or separate output streams were fabricated.

Functional failures/timeouts/reruns:0. Static metadata corrections:1. A second metadata error remains uncorrected. No further functional or corrective work is authorized by this review.

## Commands and frozen failure package

Actual commands ran from D:/1800 with the existing CPython3.9 executable. Outputs are exclusive and not reusable as a rerun authorization.

```powershell
$py='C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe'
$r='D:/1800/docs/evidence/A03/review/P2-R11-crash-cuts/scripts'
& $py -X utf8 -B "$r/run_recorded.py" freeze-01 90 "$r/freeze.py"
& $py -X utf8 -B "$r/run_recorded.py" static-preparation-01 45 "$r/prepare_review.py"
& $py -X utf8 -B "$r/run_group.py" F1
& $py -X utf8 -B "$r/run_group.py" F2
& $py -X utf8 -B "$r/run_group.py" F3
& $py -X utf8 -B "$r/run_group.py" F4
& $py -X utf8 -B "$r/run_recorded.py" boundary-audit-01 90 "$r/audit_review.py"
& $py -X utf8 -B "$r/run_recorded.py" process-audit-01 45 "$r/process_review.py"
& $py -X utf8 -B "$r/run_recorded.py" correction-record-01 30 "$r/record_correction.py"
& $py -X utf8 -B "$r/run_recorded.py" process-audit-02 45 "$r/process_review.py"
& $py -X utf8 -B "$r/run_recorded.py" report-01 45 "$r/write_report.py"
```

[Historical preservation](../evidence/A03/review/P2-R11-crash-cuts/historical-preservation.json) records9079 prior review files/reports,276681374 bytes, inventory SHA256 `8f1ce647ffaeedc4c90b5541dc33df564c0bb9281318d3932c04d62a84480e84`. Their bytes are checked again for the failure package. Product/source seeds, author files and old evidence remain unchanged. Only this report and the R11 review directory are added. No state, commits or pushes were made.

The [process release record](../evidence/A03/review/P2-R11-crash-cuts/process-release.json), [final failure-package verification](../evidence/A03/review/P2-R11-crash-cuts/final-verification.json) and [SHA256 manifest](../evidence/A03/review/P2-R11-crash-cuts/sha256-manifest.json) cover actual new evidence and this report; only the manifest excludes itself. The final tool receipt supplies their hashes without a self-reference.

Final verdict remains **REWORK**, with the four finite functional results supported as described above. The old AFTER_INTENT_COMMIT, lost-receipt N1, R9/R10, old R3 N7, other fault cuts, full suites, multiple actions and other original matrix gaps were not executed or waived. Whole A03 remains REWORK; local product integration, INTEGRATED registration and I01 are not released. B mapping is not jointly confirmed. Final coordinator registration was not performed.

Field reset: `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`. No reset, variant, delegation or retest recommendation. No network, platform/browser/profile/credentials/OCR/paid models/install/push/B contact/A05 question22/book submission. User model/thinking were preserved and no agents were delegated.
