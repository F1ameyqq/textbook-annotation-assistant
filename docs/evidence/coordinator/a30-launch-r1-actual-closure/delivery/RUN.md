# A30 launch03-r1 actual executor report - 2026-10-25

Frozen, read-only report of the single bound actual run a30-full16-reconcile-continue-20261025-01.
No acceptance conclusion beyond fixed failure and own release is made here.

## Run identity

- authority id: a30-full16-reconcile-continue-20261025-01
- authority sha256: 10e9330b19254c50f8f369c143de3a66fbe40989114baf2b583675c82e3ce14d
- entry run_once.py sha256: fbfa867331c141f70f4d1e10a9393b78dd67aaabcb4fc61310d2a5d03ef7606a
- binding sha256: 35f87bd50b1e08f0241557ac8a65517697995b56c1e605955ea41152e2905688
- window: 2026-10-25T04:07:37Z - 04:37:37Z
- outer started 04:09:16.048751Z, child entered 04:09:30.389530Z, finished 04:11:02.584543Z
- exit code: 2, timeout: null, elapsed: 92.09928860000218 s, spent 1 / remaining 0, automatic_retry false

## Outcome (production-result.json)

- status: STOPPED_NO_RETRY
- type: Hold
- message: 读回题数或书籍不一致。
- successors: NOT_RUN
- original_settings_unchanged: true; workspace settings.json sha256 verified unchanged:
  56f07eb98e9712b662a13b016d9758c3d2c12109421a7b1f557a972e2b565f5f

## Own OS release (production-outer.process.json, A25OwnedWindowsProcess/v1)

owned_os_release_confirmed true. Launcher pid 73292 exited with code 2;
job_assigned_before_resume true, job_handle_closed true, job_active_processes_after 0,
thread_handle_closed true, process_handle_closed true, launcher_exit_signaled true,
launcher_exit_wait_result 0, errors [].
151 observed processes (88 msedge.exe, 36 python.exe, 10 conhost.exe, 9 node.exe, 6
identity_helper.exe, 2 python.exe with exit 2) - all with exit_signaled true and
handle_closed true. identity_helper observed exit code 3221226029 retained; its cause
remains UNKNOWN.

## Network during the run (9 usense-readonly rounds, 04:09:37Z-04:10:55Z)

661 events total: GET x661, POST x0. Zero POST/write/upload/login/OCR/model calls. 303
distinct urls retained as url_sha256 only (no plaintext URL index in the workspace).
Per-round counts: 7, 91, 91, 91, 91, 91, 91, 91, 17. All nine capture summaries:
NATIVE_GETS_CAPTURED, save_attempts 0.

## state.sqlite (read-only query)

Operations 85 -> 86. The single new op (rowid 86): reconcile
d779d3db6997363af731d4b6f5f2371a56d3ea964f4b29f8e51a4b20b79a02d5 FAILED_NO_RETRY, output blob
521de42316d48df43ea54b810a5fc4354469188f0cc916689227bc66ecc0c8b0 = {type: Hold, message:
读回题数或书籍不一致。}. Pre-existing reconcile op 06937fa7... COMPLETE (2026-10-24 Q1
CustomerSaveReadback) retained. Save ops unchanged at 12 (11 COMPLETE + Q12 56232bbf...
UNKNOWN_NO_RETRY); no Q12 COMPLETE, no new save op, no 13-16 save op. Jobs rows:
rowid 6 head a12f0f6c... (revision-1 head, a30-current-preparation-20261024 workspace,
predates run); rowid 100 head 28274dab... (current head, updated by this run from
7077df60...: platform_status RUNNING->UNKNOWN_NO_RETRY, stop message appended).

## Comparator diagnosis (Hold site)

app/src/annotation/customer/native_plan.py:256:
  require(len(new_questions) == len(old_questions) + 1 and after["book_id"] == plan["book_id"],
  "读回题数或书籍不一致。")
Plan blob 6163be59... (Q12, printed 12): before_count 37, new_order 38,
before_frame_count 125, book_id 46007447. Final fresh capture (04:10:55) directory: 42
questions. 42 != 37+1, so the COUNT predicate failed while book_id was equal on both
sides (46007447). Classification: COUNT_MISMATCH_ONLY (book identity matched); the
combined message does not separate the two predicates, but the count predicate is the
one that failed.

## Four extra nodes at orders 39-42

| order | node id | created (UTC) | platform local frame time | matches printed |
|-------|---------|---------------|---------------------------|-----------------|
| 39 | 1792864390658 | 2026-10-24T17:53:10.658Z | 2026-10-25T01:53:11 | 13 |
| 40 | 1792864454350 | 2026-10-24T17:54:14.350Z | 2026-10-25T01:54:14 | 14 |
| 41 | 1792864513549 | 2026-10-24T17:55:13.549Z | 2026-10-25T01:55:14 | 15 |
| 42 | 1792864580902 | 2026-10-24T17:56:20.902Z | 2026-10-25T01:56:21 | 16 |

All four predate the run window by about 10.2 hours; the first run-window capture
(04:09:37Z) already shows 42 questions. Their question/choice/answer/figure rect bboxes
match the prepared candidates 13-16 exactly, and all 15 rect_ids equal the deterministic
uuid5 derivation uuid5(NAMESPACE_URL, "customer/" + source_key + "/" + index) of our
tooling for those candidates (sanity-validated against printed 12 whose plan rect_id is
known). Nevertheless: no save receipt or operation for 13-16 exists in any retained
workspace (save ops unchanged at 12; no op key equals any of the four source keys
6ecc8fdc..., b753d684..., 27cf0df9..., e749cf34...), and candidates 13-16 remain
platform_status NOT_RUN in head blob 28274dab... Attribution: UNKNOWN. This report does
NOT claim Q13-16 accepted, and no resend is authorized.

## Raw evidence

See raw/ for byte-exact copies and SHA-256 of the nine live output files:
launch-intent.json, child-entered.json, outer-outcome.json, production-result.json,
console.stdout.txt, console.stderr.txt, console.exit.txt, production-outer.process.json,
production-outer.stderr. (production-outer.stdout exists in the live dir as 0 bytes,
sha256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; it was not part
of the required nine.)
