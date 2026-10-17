# Viewer-13 reviewed-layout patch v2 — extended independent failure report

Date: 2026-10-17  
Result: **FAIL / v2 closes v1 attacks but is not yet integration-ready**  
Auditor repository edits: isolated temporary export only

## Frozen version

- Patch SHA-256: `3141feed89e1b30e59645dd44bbbac8f2b9e15e15171ebd7464224d8e9e22e25`
- Bundle SHA-256: `e2f58af90f45d2a56ef00ce553129d8ae77fe73042a92341009df9e2e365e9d9`
- Compatibility baseline used: `a2b3cf77672e861fea52e5f8e96e7c8b7ea96141`
- Producer code hashes match the v2 verification report.
- Patch applies cleanly and `git diff --check` is clean.

## V1 defects correctly closed

The unchanged v1 adversarial reproducer exits 0 against v2. Independent checks now reject:

- forged material/task IDs and coordinated ledger owners;
- duplicate material/task IDs;
- legacy E0.2 use of the reviewed-spanning mode;
- graph-level `VERIFIED`, publication actions, added human flags, or dropped risk flags;
- added top-level check approval/business/transcription/publication fields.

These repairs are technically sound but incomplete at the next nested semantic level.

## Remaining blocking defects

### 1. Source number and task response semantics remain context assertions

A context can change the visible Q8 and child variant to printed numbers `9` and `9:variant`, or change task (1) `response_kind` from `UNKNOWN` to `HUMAN_GRADED`. Producer refinement, assembly, and quality all succeed; independent source, graph, and quality consumers report zero issues.

Required repair:

- bind the QUESTION printed number to the independently derived `QSTART` capture;
- derive the variant number from the bound parent number and fixed uncounted-variant policy;
- require this route's task response kind to be exactly `UNKNOWN`.

The context and review document roots likewise accept `reference_quality: HUMAN_VERIFIED` and provenance text claiming human approval. This route should require its exact development/model quality and non-human provenance contract.

### 2. Evidence0.4 permits injected approval metadata

The independent source consumer returns zero issues after each re-signed mutation:

- `page.layout.verified = true`;
- adding `human_verified: true` to `reviewed_layout_receipt`;
- adding `human_verified: true` to the E0.4 payload.

Require exact structured-route payload/page/layout/receipt shapes and explicit false/unverified values. This is artifact-integrity validation, not OCR semantic certification.

### 3. Graph0.9 has unbound source and ordering fields

The graph consumer accepts all of the following with zero issues:

- reversing the two question entities;
- reversing task order `(1),(2),(3)` to `(3),(2),(1)`;
- replacing `type_candidate` with arbitrary content, including `human_verified: true`;
- coordinating an arbitrary material/task `asset_id`;
- replacing the material `section_path` with `FORGED`;
- changing `matching` to `HUMAN_APPROVED`;
- setting nonempty forged `unmatched_answer_ids` in this no-answer route;
- replacing graph issues with an arbitrary `APPROVED` record.

Require source-derived entity order, exact type-candidate projection, material asset/path equality to its title source group, and exact no-answer route values for matching, unmatched IDs, and graph issues.

### 4. Check0.9 validates only the outer payload shape

The quality consumer accepts all of the following with zero issues:

- `reason: APPROVED FOR PUBLISH`;
- added `accepted: true` and `business_acceptance: true` inside `summary`;
- changing every issue to `severity: INFO`, `blocks: []`, and `suggested_strategy: AUTO_PUBLISH`;
- adding nested `accepted: true` to an issue.

The complete issue multiset must be independently reconstructed or checked field-for-field: exact issue keys, deterministic issue ID, code-to-scope binding, evidence references, severity, blocks, strategy, and detail. `reason` and `summary` also need exact shapes and values.

## Gate

Do not integrate v2. A v3 should apply exact per-field validation to context, evidence, graph, check, and development-review inputs while preserving the already correct 48-row partition, task flow, deterministic replay, legacy compatibility, and persistent `HOLD / UNVERIFIED / no platform actions` status.

The companion `viewer13-v2-extended-adversarial-repro.py` exits 1 against v2 and should exit 0 unchanged against the repaired version.
