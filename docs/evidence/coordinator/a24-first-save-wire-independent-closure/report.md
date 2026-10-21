# A24 frozen first-save wire independent review

Result: **REWORK**. The frozen candidate implements the wire adapter and substantial preservation/receipt checks, but two material defects prevent acceptance of a runnable first-save preflight. Correct both in the same A24 delivery; no new stage or chat is needed.

## Frozen identity and intake

- Reviewer: 01a15cf8-68e0-7b63-91a3-657a567b344c; workflow e0bcd85ec419a69d492aebac918917401fef5926.
- Isolation: D:/1800-worktrees/a24-first-save-wire-review. Only this report/evidence directory was writable review output. The active author tree was not inspected.
- Base dceda09db31487d64654e23dd36ccd3705c740fc; product 851cf6fce217df8f64a6f3bdeaa99b5e5e2c234d; final 680bd5f624659f1091db974d5ed30b332ff946dc.
- Fixed task SHA256: 64ffaf55f42fb64e9fc9d0af66945fdddae071ebe09f082b5f83b60a622c8cdb.
- Root input manifest SHA256: 165b840054cc18ecaaa1cc89f17c3678c3450f26c842509351a4a78d2cba0326; 225 raw files independently checked by size/SHA256/Git blob, before tests and at closure.
- Candidate SHA256: ac9573448692f313076a02489a9727cb9131040e22a6c55e5797c11a3e01cf19; 92 dependencies checked. Authoritative final delivery SHA256: 03366e94a4b7d3672322839f5581a118c26190df3d5274b41bcd73fa0cb382d1; 144 members checked, plus the manifest itself bound by the root inputs.
- Author release SHA256: 178934cfb5a530623d77e39b3c276b0dbd70bf2372172f1177c60ec19f2ccd59. Older delivery-manifest.json remains failed packaging evidence, not intake authority.

Root's 32,459-member preservation comparison is fixed input evidence, not independently rerun against the full historical repository here. This review independently verifies every supplied raw input and the two supplied member sets. No product/input change was made.

## Bounded verification

| Verification | Actual result | Timing |
| --- | --- | --- |
| New Python suite, once, independent guarded runner | 45 PASS; 0 failures/errors; exit 0 | report duration 7,688 ms; embedded unittest timing 7.366 s, both retained |
| New JS VM controls, once | 8 PASS; exit 0 | independent duration not measured |
| Independent receipt-persistence counterexample, once | 1 FAIL; 0 errors; exit 1 | report duration 234 ms; embedded unittest timing 0.247 s, both retained |
| Further controls after material failure | NOT_RUN | No repeat trial |

Python retained socket, URL-open, subprocess and private config/profile guards; temporary files and patched test homes stayed under the output directory. JS used the frozen PAGE_FETCH/PAGE_UPLOAD literals with fake fetch/localStorage/FormData. No older suite, product launcher, seal/package helper, real browser, network, profile/config, credentials, native API, model, login, upload, save or activation was run.

## Consolidated minimum corrections

### R1 [P1]: provide the executable owner/authority/guard/release integration

`src/annotation/runtime/live_pilot/runner.py:11-37` accepts an already owned page/context/guard/binding and explicitly delegates acquisition and outer release to its caller. In the supplied frozen src/tools tree, there are definitions but no call sites for apply_current_context, reopen_current_context, build_guard_binding or make_first_save_guard. The supplied real owner still constructs the readonly CurrentGuard with ReadPolicy at `tools/a16_current_state_probe.py:740-756`; its observe_live/worker_main path does not invoke the first-save adapter. This is a missing executable integration, not a missing current server field value.

`usense.py:52-58` compiles slots from an activated object and nonempty decision/report/dependency references. It is expressly not the authority verifier. `usense.py:98-110` requires a distinct new guard but leaves installation to the caller. The new platform tests inject an authenticated fake BaseGuard and SYNTHETIC_ONLY activation references (`tests/a24_first_save_wire/test_platform.py:43-59,133-150`); they do not supply the missing real owner path. No absence claim is made about files outside the frozen supplied set.

Minimum fix: add a narrow callable entry through the existing owner framework. Before acquiring real resources, verify the exact frozen dependency/candidate/decision/independent-report/activation hashes, scope, window and unique counts. Install a new first-save guard before online bootstrap; perform the separately bounded viewer/session admission; call the adapter; and on every exit collect actual callback/context/runtime/held-process/Job release evidence. Bind the designated independent readonly reopen through the same ownership contract. Keep old guards and spent budgets untouched. Verify this orchestration with a small injected-owner fake; do not start a real context during correction.

### R2 [P1]: project durable receipts and query provenance before persistence

`runner.py:88` journals the complete BUSINESS_RECEIPT raw response before strict decoding at line 89. `usense.py:790-807` returns the full response body; `wire.py:381-410` validates JSON/provenance and extracts approved receipt paths but permits unrelated JSON members. Therefore the extra members reach durable storage even when the strict receipt succeeds.

The independent fake response added only unapproved_session_material with a synthetic sentinel. One fake commit completed as APPLIED_SYNTHETIC_WIRE, while event-000004.json retained that value. The exact offending synthetic event is preserved as counterexample-event-000004.json; privacy-control-result.json contains the failure and full output. This proves the persistence-boundary defect without accessing any actual secret or platform.

A related static path retains raw GET params at `usense.py:634-636`, carries the ledger into observation provenance, and stores the baseline/plan in the durable intent at `runner.py:75-78`. Current official account-query values would follow that path if later bound. This branch was inspected statically; no actual account values were read or tested.

Minimum fix: journal only the finite approved receipt projection plus necessary response/payload hashes, or a finite UNKNOWN record when decoding fails. Do not dump the raw body before validation. Persist query provenance as phase/slot/path template, approved key names and hashes; retain account/token/query values only ephemerally. Any separately required private raw evidence must have an explicit controlled reference rather than entering the generic journal/report/Git artifact. Preserve intent/claim and UNKNOWN stop semantics; no resend or budget reset. Add one focused sentinel regression for the repaired persistence boundary.

## Implemented behavior retained in this assessment

The code provides durable intent/claim before signature/upload/commit, burns effect slots before I/O, and prevents retry/re-sign after ambiguous outcomes. It binds the six Q/W/W/W/W/A crop objects, actual multipart bytes/hash/fields, signing host/path/policy/expiry and commit JSON. The guard retains original frame identity, redirect rejection, native/context matching and cache/freshness checks.

The body write set is explicit question/choice/answer plus NEW_QUESTION_ONLY empty analysis/knowledge_point operations, without old-frame deletion or order renumbering. Strict receipts require server stable identity, actual integer order and all six rectangle identities; tentative 23 is not a receipt. Fresh get/refresh comparisons and independent-session/release-chain checks exist. The full-export codec rejects incomplete membership/zones; 22 observed question nodes and 68 frames do not prove whole-book completeness. These are static/fake findings, not live acceptance.

## Actual inputs and concentrated-plan limits

Current complete authoritative export/field maps/all-zone coverage, protected account field maps, legal leaf/end insertion, newness, current joint W-role policy, approved body/six JPEGs and pixel boxes, source-to-save-page relation, receipt/readback schema, signature/OSS success contract, current lock/journal state and final owner bootstrap budgets remain unbound actual inputs. They must be frozen before activation, but are not each a separate implementation defect.

The proposal explicitly totals 32 business GETs, one signature GET, six object POSTs and one commit POST, excluding unfrozen bootstrap/UI slots; refresh includes one Document reload and independent reopen requires its own new owned context. Counts are proposed, not an executable authorization. Existing upload code checks signing and native bytes/status, but locally returned host/key do not independently prove object durability. Bind the actual OSS success semantics; do not infer body save from a constructed URL or add an unapproved verification GET.

## Preserved failures and release

Metadata helper errors remain recorded: initial PowerShell brace syntax failure; intake candidate-key KeyError; follow-up nonexistent files-array errors; a static lookup of a launcher absent from the supplied set; and a report apply_patch attempt that produced truncated output and no report file. The latter's exact exit/chunk was not exposed. Corrections affected only new review metadata; no product test was rerun. Author historical failures and the older failed delivery manifest remain unchanged. Test timing differences are retained without a root-cause assertion.

All own local helpers completed. No real browser/context/native runtime/OS Job was acquired; no retained helper or test temporary resource remains. See release.json and input-preservation.json. First and revised A24 readonly allocations remain spent (0 remaining). Actual upload/save/get/refresh/reopen are NOT_RUN; write_eligible=false and production_ready=false. This review creates no real authority or budget and does not alter the earlier limited actual source acceptance.
