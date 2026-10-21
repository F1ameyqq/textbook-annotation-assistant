# A24 first-save wire R1 frozen independent delta review

Overall code result: **REWORK**, with one remaining owner/reopen correction. Receipt/query persistence P1 is **CLOSED_IN_REVIEWED_OFFLINE_LAYER**. The exact current AUTHOR_SAVE acquisition branch receives a separate **ACCEPTED_OFFLINE_ONLY / BOUNDED_AUTHOR_UNBOUND_FOUR_GET_PREFLIGHT** disposition; this review creates no activation. Conditional save and INDEPENDENT_REOPEN are not admitted.

## Frozen intake and verification

Same formal reviewer 01a15cf8-68e0-7b63-91a3-657a567b344c; same A24 stage. Task SHA256 0dc091a63be94a2429f5734083cb10cb86fcc7a1102af78d870151873ab27f71. Isolation D:/1800-worktrees/a24-first-save-wire-r1-review; new output is this directory only. No active author directory was read. Private source paths used by the new suite were transparently redirected to the 17 root-frozen snapshots.

Base 680bd5f624659f1091db974d5ed30b332ff946dc; product 0bc24966930c38df6cc75ae83dbb4069f35f966f; content f21325e887846b0ed7a2aa72627ac0e2dc99393f; final 2dcead75c317d3d46b56c1f2bc00583394daaea7. Candidate SHA256 ade52cb3cff54f7ed094f921daa4be55d747ed28beb2fc16c80312b176584c67; sole final delivery manifest b760076cf6e48b5fcaa3daf8738cf9788b24c5c8c76359587709292571305679.

Independent raw intake verifies 291 root-selected members by size/SHA256/Git blob and fixed mode/type metadata, all 132 dependencies and 290 delivery members, plus all 17 private snapshots by size/SHA256. Root input manifest SHA256 685174a033865695ac0143c559cb3b61a561302fbdee6391231bf935d4753018; private snapshot manifest a3057a872ba2faf47086079365938ab2b80ec2c75790bfb28bac5caa38f3b292. Both are copied exactly in the output. Root's 32,600-member historical comparison and 31,321 retained old-evidence comparison remain fixed coordinator evidence, not a repeated full-repository diff by this reviewer.

| Finite validation | Actual result |
| --- | --- |
| New R1 Python suite, once | 20 PASS, 0 failures/errors, exit 0; 117,422 ms report duration, 116.057 s embedded unittest timing |
| Independent unknown-author/unbound-reopen control, once | 1 FAIL, 0 errors, exit 1; 297 ms |
| Further controls after first material failure | NOT_RUN |
| Model, old suites, product launchers/native/browser/network/live | NOT_RUN / zero actual resources |

The review runner retained no-I/O patches, used the supplied pure-memory asyncio policy, added socket/process/config and output-write guards, kept temporary files inside this output, and set failfast. No historical suite entrypoint, model/backend inference or real launcher command was executed. Test timing differences remain unmodified; decomposition is UNKNOWN.

## Original P1 dispositions

### Receipt/query persistence: closed in the reviewed offline layer

`runner.py:114-123` now decodes a receipt before journaling. Valid receipts persist only the finite strict projection plus hashes; decoding failure persists UNKNOWN, response/payload hashes and a reason. The unapproved raw body is not journaled first. `usense.py:453-465,700-705` and `wire.py:39-50` use query key names/hashes and path templates, without account query values.

`ControlledVault` stores full intent, baseline/payload/readback and author evidence as immutable controlled-private records; the generic journal keeps hashes/references. The real owner adapter always supplies that vault. Resolve-intent verifies its stored hash chain. Durable intent then claim still precede signature/upload/commit, UNKNOWN does not resend, and the focused tests cover successful extra-field projection, bad-receipt UNKNOWN and spent-claim refusal, and query sentinel absence. The original failed sentinel control remains historical failure evidence, not relabeled PASS or rerun.

OSS handling is narrowed correctly: native 2xx/status and response hash are transport acknowledgements. Local host/key are request provenance, not invented server echoes or independent object-durability evidence.

### Executable owner: implemented, but reopen predecessor gate remains REWORK

The missing executable route now exists: CLI raw closure check precedes product imports; authority checks bind candidate/raw dependency/private source/decision/independent acceptance/scope/window; distinct launcher/product/worker/occupancy claims and tokens reuse held identity/Job handling. WindowsBackend creates an offline persistent context, installs the distinct new guard before online/bootstrap, and invokes the real async adapter. The supplied fake owner tests exercise that adapter/CurrentPageIO path and failure cleanup. Context/runtime/callback release and held-process/Job closure are separately recorded. The launcher correctly leaves its own OS exit UNKNOWN_WHILE_RUNNING pending the coordinator's later certificate.

**R1-R [P1]: require a qualified, released, known author predecessor before any independent owner acquisition.** `authority.py:243-246` only hash-reads/parses author_release. `owner.py:305` obtains the profile before role-specific predecessor validation, and `owner.py:330-333` routes every role into acquire_current_schema when schema_profile is absent or the plan is unbound. The full release/receipt chain is checked only on the later independent_reopen adapter path (`runner.py:182`); the unbound branch never invokes it.

The independent control supplied a hash-bound SYNTHETIC INDEPENDENT_REOPEN authority with schema_profile=None, author status UNKNOWN, no receipt and released=false. verify_authority returned a capability. run_owned_worker logged profile, occupancy, install-before-online-bootstrap and close; it executed four fake business GETs and returned PREWRITE_BLOCKED_NO_EFFECT. Exact result and traceback are frozen in counterexample-unbound-reopen-result.json and reopen-control-result.json. No real resource or write occurred. GET-only is insufficient to classify these reads as a valid independent reopen after release; it also bypasses the separately bounded UNKNOWN reconciliation distinction.

Minimum fix, same A24: before native/profile/context acquisition, reject INDEPENDENT_REOPEN unless a qualified profile/body route and known author save/strict receipt/refresh observation are bound. Validate the hash-linked full outer release certificate, author result and receipt/observation/session chain at that gate. UNKNOWN, absent receipt, unreleased owner or unbound schema must not fall through to four-read acquisition. Restrict acquire_current_schema to AUTHOR_SAVE. Keep independent reopen GET-only; keep reconciliation separate and no-resend. No generic owner rewrite, new stage, model work or old-suite replay is needed.

## Separate current four-read disposition

**Yes: the exact schema_profile=None AND role=AUTHOR_SAVE branch can receive a separate finite offline preflight acceptance.** The reproduced defect is a role/predecessor bypass on independent reopen; it does not create an effect path in this specified author branch.

After root binds the existing user request to a new exact authority, the reviewed current branch has one newly owned context, one initial viewer navigation within its <=900-second window, original session/frame admission, exact bootstrap resources, and four once-only business GETs:

1. /qieti/api/claim_book/books, using the same-page official query and shared exact book slot;
2. /qieti/api/annotate_ocr/directory/get?file_id=46007447;
3. /qieti/api/annotate_pic/get_manual_annotations_unified/46007447;
4. /qieti/api/annotate_ocr/export-paper-questions/46007447.

Book response is retained only as finite metadata/hash; directory/frame/export raw bytes stay under controlled-private references. Exact active request and native/context bytes/cache/frame provenance are checked. No synthetic completeness row, codec qualification or write-ready request is generated. Successful collection still returns PREWRITE_BLOCKED_NO_EFFECT; adapter/signature/upload/commit/refresh/reopen successors remain NOT_RUN. First failure stops successors and releases the owner. This is safety/executable preflight acceptance only: actual session, endpoints/export format/body coverage and successful collection remain unproved. A later write must use separately frozen current facts and a qualified new exact request; the collector cannot promote itself or reuse old spent budgets. No real authority or collection was run here.

Bootstrap limits and every frozen plan leaf are mapped in typed-authority-scope.json. Important limits/business counts use recursive same-type comparison; current values and complete raw plan hash are bound. Some bootstrap scalar constants are checked by equality rather than an explicit same-type predicate: the mapping discloses that distinction, so this report does not claim universal runtime rejection of every bool/int alias. Their effective constants and this frozen four-read scope do not expand; no further counterexample suite was run after the material failure.

## Native content binding and conditional branches

Existing corrected-content acceptance remains unchanged: cd4ee0c6a379fa5bf8cc87dccdb010c423a9e2f9a2382336efaa00cefe103b5a, independent machine 1dad447c41ee2d8a8ce79e02d3aef2c5ef0238be07278759a118d0273ab6e9e0 and root disposition 9feb5218e54b561a5d094d5bbd86604a8574b3c773722ce768f31924fa123d2e. No model/content review was repeated. The new fixed-content suite control passed against snapshots: conversion parts quote that artifact with explicit option-label formatting, four model/input/failure refs and both acceptance refs. Six Q/W/W/W/W/A crop bindings retain original hashes, original bboxes and unit-scale offsets; JPEG byte hashes are fixed separately. HISTORICAL denotes the quoted corrected artifact, not human approval or raw OCR success. The raw model FAILED_HOLD/empty answer and AI visual transcription remain disclosed. Native source graph conversion is source preparation; joint policy is still PROPOSAL_ONLY and request approval/body schema are null.

Conditional save remains **NOT_QUALIFIED_NOT_ADMITTED**. It needs actual natural-export codec/route completeness and all-five-zone old bodies/frames, legal append/newness, current save-page/account/policy/receipt/signature bindings, exact payload/request and a new scope-bound authority. The aggregate 17/20 GET compiler is a future qualified route, not this four-read activation budget. Conditional independent reopen additionally needs the R1-R code correction and a known successful author chain/full coordinator release proof before owner acquisition. No new actual save, upload or independent reopen is authorized by this report.

## Preservation and release

All author helper failures, original model failure, prior wire REWORK and independent sentinel failure remain frozen. A reviewer metadata-only inspection after the material control failed with KeyError 'text' while assuming the QuestionGraph fragment shape; the query produced no comparison result. It is recorded as an inspection-helper failure, not a product/content defect or another test, and was not retried. No additional product/control execution followed the first material failure.

All own local suite/control helpers exited; temporary test files were cleaned. No real native/browser/context/profile/service/Job was acquired. Input-preservation and output size/SHA manifests are frozen, self excluded with external digest. Both prior A24 readonly allocations remain spent, zero remaining. write_eligible=false, production_ready=false, actual_save=NOT_RUN, actual_independent_readback=NOT_RUN. Same author/reviewer continue in this A24 chat; current limited collector acceptance does not close the remaining owner code REWORK or qualify writing.
