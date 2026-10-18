# Viewer-13 reviewed-layout v3 — independent final audit

Date: 2026-10-18 (Asia/Shanghai)

## Verdict

**Technical PASS for the frozen v3 patch and replay bundle.** The patch closes every previously frozen v1/v2 fail-open reproduction, preserves the 48-row source ledger and required cross-column ordering, and remains an explicitly unverified development route (`E0.4 -> G0.9 -> Check0.9`) with `HOLD` and no platform actions.

This is not human transcription, mathematical, business, or publication acceptance. The route must remain `HOLD` until those separate reviews occur.

## Frozen inputs

- Compatibility baseline: `65139f43e5ae8a6caf3f9c8f9ded8834cbe3e2de`
- Patch: `viewer13-reviewed-layout-v3.patch`
- Patch SHA-256: `316a9ebb164135e1b40daf3c5b5ef7abccf518502c25bb119279494db243163b`
- Bundle: `viewer13-reviewed-layout-v3-bundle.zip`
- Bundle SHA-256: `51d5e5704631f229deb792322d1fb7b34f61c4766e7c1b1c286c3709e77adda5`

The patch applied cleanly to a fresh detached export of the baseline; `git diff --check` was clean. Source byte hashes in that patched export exactly matched the producer's declared values:

- `offline.py`: `f5e125c77ed4c8d227d69570183e3421d1601d7b2716c11411ec1162561144bd`
- `pipeline.py`: `bb600b1aa457ae23bdca22f3787b0e488e048fbacdf46f73e3dcb2ca2908d31e`
- `pipeline_quality.py`: `afb71b3838da9094b92ac4b3cef6b48906a1d6e86855f23605d0a972166c453c`
- `question_quality.py`: `69b5632f760eb9338931677d68f94a79d0a64308a56d506d9e7cf9fe4ddae961`
- focused test file: `258890eb4a1f2b87797415e0b62ee42daea8f868da856d7d0c5699ef0d61d106`

## Independent checks performed

1. Replayed the unchanged v1 adversarial reproducer against the v3 export: exit 0. Forged material/task identities, legacy-layout bypass, graph verification/platform-action claims, flag manipulation, and top-level Check approval claims all rejected.
2. Replayed the unchanged v2 extended adversarial reproducer: exit 0. All context, evidence, graph, Check, and review promotion/rebinding attacks rejected, including printed number and response-kind changes, evidence verification fields, question/task order, type candidate, material asset/path, matching/unmatched/issues, nested Check approval, and review provenance/reference-quality promotion.
3. Reviewed the source-level independence boundary. The consumer re-derives the pixel gutter, OCR source partition, raw-anchor identities, columns, receipt maps, fragment/entity identities, full 48-row ownership ledger, and exact Check 0.9 payload. `_structured_expected_check` reconstructs expected output from evidence/context and does not call the quality producer.
4. Focused tests: **10/10 passed** (`tests.test_viewer13_reviewed_layout`).
5. Legacy affected regressions: **44/44 passed** (`tests.test_b_offline`, `tests.test_b_pipeline_quality`).
6. Ran the supplied bundle replay in a brand-new directory:
   - cold: `READY`, independent audit accepted, 0 cache hits;
   - warm: `READY`, independent audit accepted, 3 cache hits;
   - deliberately corrupted assemble cache: `READY`, independent audit accepted, 1 invalidation and 1 cache hit;
   - all reports/audits remained `HOLD` with zero platform actions;
   - replay declared zero new OCR, model, or network calls.

## Source-structure checks retained

- Exactly 48 frozen OCR rows are owned once each.
- Printed Q8 and its variant remain distinct; the variant derives its identity from Q8.
- The spanning title remains a two-segment left/right projection.
- Figure labels retain reviewed order `[24, 33, 32, 35, 37]`.
- Task (1) retains the one-time column transition `[41, 42, 43, 44, 45] -> [10, 12, 16]`.
- Tasks (2) and (3), material body/title/heading, and decoration exclusions remain separately owned.
- Task response kind remains exactly `UNKNOWN`; reference quality is `MODEL_VISUAL_DEVELOPMENT_REVIEW`; all verification/business acceptance fields remain false or unverified.

## Scope and repository state

- No OCR, model, browser, or network call was made during this audit.
- The full repository suite was not rerun for v3; only the focused 10 and affected legacy 44 tests were rerun, consistent with the requested scope.
- The shared repository was not modified by this audit. At final inspection it still pointed to the stated compatibility baseline and contained unrelated pre-existing chapter documentation/handoff changes.

