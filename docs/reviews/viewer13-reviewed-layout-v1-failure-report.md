# Viewer-13 reviewed-layout patch v1 — frozen independent failure report

Date: 2026-10-17  
Result: **FAIL / repair required before integration**  
Shared or producer-private repository edits by auditor: none

## Frozen artifacts reviewed

- Patch: `viewer13-reviewed-layout.patch`
- Patch SHA-256: `0f4da133dd4de093bab6894dfd8bbd04a444015d7cb3239b42f1e58b989de919`
- Baseline used for the auditor's isolated application: `ee8df364d2c7d24375f22d9264033b18c02d6a98`
- Initially frozen bundle: SHA-256 `ead4905f2d04e9c075bca9c774e58415f868b321154ae208cb228d4ada10bfab`
- Supplemental receipt bundle inspected/replayed later: SHA-256 `2c7989b548d94b7d5c9f3349df5aef938379f00d58d0ba0dd9ffd1f149bcc42e`
- The patch bytes are identical in both bundles. `git apply --check` also succeeds against the then-current shared checkout `7d5c3b738a3e28b528e510d16d7cfe2640936964`.

## Checks that passed

- Patch applies cleanly and `git diff --check` is clean.
- Reported code/test hashes match the patched files.
- New focused suite: 4/4 passed independently.
- Legacy/regression slice: 70/70 passed (`test_b_offline`, `test_b_pipeline`, `test_b_pipeline_quality`, `test_b_pipeline_recovery`).
- Independent cold/warm/corrupt-assemble replay passed:
  - cold: 3 done, 0 cache hits, 0 invalidations;
  - warm: 3 done, 3 cache hits, 0 invalidations;
  - recovery: 3 done, 1 cache hit, 1 invalidation;
  - decision remained `HOLD`; no OCR/model/network call.
- The first three prior design blockers are structurally repaired in the honest replay:
  - title/task roles are re-derived from source pixels, OCR anchors, and geometry by both producer and independent consumer;
  - line 40 is a distinct task-section heading, body/figure order is corrected, and figure labels use geometry-defined ordering;
  - all 48 rows are partitioned once, with task (1) exactly `[41,42,43,44,45] -> [10,12,16]` and strict within-segment order.
- Exact baseline reference, producer, 48 snapshots, and the explicit route `context0.2 -> evidence0.4 -> graph0.9 -> check0.9` are bound in the honest path.

These successes do not override the following fail-open consumer defects.

## Blocking defects

### 1. Graph false-verification fields are accepted

`_structured_graph_sources` checks the presence of `selection_status` and `platform_actions`, but not their values. A re-signed graph with either:

- `selection_status: "VERIFIED"`, or
- `platform_actions: [{"action": "PUBLISH"}]`

produces zero independent graph issues. A fresh check remains `HOLD`, and `_quality_bindings` also produces zero issues. This creates a contradictory graph that the independent consumer accepts.

The same path accepts an added `HUMAN_VERIFIED` question flag and accepts removal of `FIGURE_EXTENT_UNVERIFIED` from material/task flag sets. Required repair: exact `DRAFT_UNVERIFIED`, exact empty platform actions, and exact or explicit allowlisted flag sets.

### 2. Check0.9 accepts injected approval claims

`_quality_bindings` lacks an exact check0.9 payload shape. Independently re-signed checks containing any of the following added fields produce zero audit issues:

- `accepted: true`
- `business_acceptance: true`
- `transcription_verified: true`
- `platform_actions: [{"action": "PUBLISH"}]`

Changing `decision` to `PASS` is caught, but the additional contradictory claims are not. Required repair: exact payload keys and explicit false/empty approval values, or strict rejection of fields not in the schema.

### 3. Shared-material and task entity IDs are not source-derived by the consumer

The producer derives `material_id` and `task_id`, but the independent graph consumer does not recompute or validate them. A coordinated mutation can:

- replace the material ID with an arbitrary value;
- replace all three task IDs with arbitrary values;
- update each task's `material_id` and the 48-row ledger `owner_id` values;
- recompute the graph payload hash;
- produce a fresh check0.9.

Both `_graph_sources` and `_quality_bindings` then return zero issues. Required repair: independently derive material ID from the evidence revision plus title anchor; derive each task ID from the evidence revision plus task anchor; require uniqueness; and construct ledger expectations from those derived IDs.

### 4. New layout mode weakens the legacy evidence0.2 path

`question_quality.audit_questions` accepts `two_columns_with_reviewed_spanning_headers` without checking the evidence schema or receipt. On a legacy evidence0.2 fixture, setting five otherwise unresolved pages to this string and recomputing normal artifact hashes changes the `UNRESOLVED_LAYOUT` finding count from 5 to 0.

Required repair: accept that mode only for evidence0.4 with a valid reviewed-layout receipt; otherwise retain an unresolved/invalid-layout finding. This guard belongs in both the producer-facing quality path and the independent audit path.

## Exact reproducer

Run the companion `viewer13-v1-adversarial-repro.py` against a repository where the v1 patch is applied:

```powershell
$env:PYTHONPATH = '<patched-repo>\src'
python -X utf8 viewer13-v1-adversarial-repro.py '<patched-repo>'
```

The script exits 1 while any documented attack is still accepted and prints every finding list. It performs no browser, OCR, model, network, or shared-repository mutation.

## Gate

Do not integrate v1. A repaired v2 should add focused regressions for all four classes, rerun the existing 4 viewer13 tests plus the affected legacy/quality tests, and preserve the same source partition, schemas, replay/recovery behavior, and `HOLD / UNVERIFIED / no platform actions` semantics.
