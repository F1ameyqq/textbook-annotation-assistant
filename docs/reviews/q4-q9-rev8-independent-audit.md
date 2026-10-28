# Q4 geometry + Q9 revision 8 independent audit

Date: 2026-10-17 (Asia/Shanghai)  
Role: independent quality/regression review  
Shared-repository baseline at review: `3de1e62d3554118816f5c4df597869193de70720` plus the explicitly listed uncommitted integration files  
External website/model calls: none  

## Verdict

**Technical integration: PASS. Business/content acceptance: HOLD.**

The merged revision-8 plan is internally consistent, source-bound, reproducible through cold/cache/restore/reapply runs, and preserves all non-target content checked here. The Q4 text is `2或\frac{25}{8}`. The geometry change remains a model draft and is not human approval of geometry, glyph identity, transcription, or final business content. The final check correctly remains `HOLD`, with `complete=false`, `transcription_verified=false`, `business_acceptance=false`, and `human_verification=false`.

## Fixed artifact identity

- Plan file SHA-256: `e9320d1d8d2d582706c3fec9eea6ed6569d1b6fab9e4ea7330f71b1cce914217`.
- Plan: `content-revision-plan-f80cd24f277f50190e84da8e`, revision 8, payload hash `b23dcf48f656a589d95ec938985cc55c01e3ee56a8e383fa1ba0ab387ad5a5ca`.
- Application: `content-revision-application-cdf952da6eff50c87ab47833`, payload hash `41908e8cee72804dbf0226ebbedba35f17b0447df222a5254051a7b85f841403`.
- Graph G0.8: `content-graph-f2fab520796bcd2a13343454`, payload hash `cae6271b3adbc1a9b60bb784ceaf035e070c35345265bee5068ff1db8242cea5`.
- Check 0.8: `content-check-ba69ec844643e6a6c6c9beb1`, payload hash `34ce53e36fa2a1e8e3dd246dab34f520404a527099f81844f62ddda5e232dc36`.
- Final integration record SHA-256: `528b8eefa228eecfa19e05fd4e27b98790fbcb7dfeea13cc1b0c436ebdc233b5`.

All four payload hashes were independently recomputed. The application embeds the exact derived graph, and the check refers to the exact G0.8 graph.

## Source and geometry findings

I reread the original `viewer-173` source asset and independently checked the fixed pixel evidence. The source supports the Q4 reading `2或\frac{25}{8}`.

The plan performs only the declared one-edge trims and preserves each original bounding box:

- Numerator fragment `af-53dc3afbfa2772a721251e6f`: original `[663,1051,690,1071]`, revised `[663,1055,690,1071]`, removed top strip `[663,1051,690,1055]` (4 px).
- Denominator fragment `af-a93723edaa95a143cca80ce0`: original `[663,1071,690,1089]`, revised `[663,1071,690,1088]`, removed bottom strip `[663,1088,690,1089]` (1 px).

Both application receipts exactly match the plan. Fragment/OCR overlap lists are complete and exact, including the numerator's overlapping answer fragment and OCR line 103 and the denominator's excluded OCR line 109.

At the fixed threshold 170, both trimmed strips contain 0 dark pixels. Independent measurements were:

- Top strip: 108 pixels, minimum luminance 247.228; 0 pixels below 170, 200, or 230.
- Bottom strip: 27 pixels, minimum luminance 245.228; 0 pixels below 170, 200, or 230.

This is only evidence under the declared threshold and crop. It is **not** a claim that the strips contain absolutely no content, and it does not replace human visual/transcription approval.

## Lineage and non-regression

- The embedded previous-plan archive exactly equals the approved Q9 revision-7 plan.
- Operations 1–13 exactly retain Q9 revision 7; operation 14 is the single Q4 geometry/rebuild operation.
- All 66 answers preserve raw `fragments`, `source_line_ids`, and `bbox` exactly relative to the Q9 parent graph.
- All 65 non-Q4 answers are semantically equal after excluding only derived IDs/plan references required by the schema upgrade.
- Questions, matching, the answer-coverage ledger, and unmatched records are exact.
- All five Q9 corrections remain present.
- Q16 revision-6 content, including `60 61`, remains present.
- The issue increase from 132 to 134 is exactly one `CONTENT_REGION_REBUILD_DRAFT_UNVERIFIED` plus one `CONTENT_REGION_SOURCE_GEOMETRY_DRAFT_UNVERIFIED`. No unrelated issue drift was found.

The final graph contains 34 questions, 66 answers, and 32 unmatched records; the final check contains 134 issues. The integration summary separately reports 19 unassigned items under its own projection.

## Adversarial and compatibility checks

During review, a genuine fail-open was found: Python accepted `False == 0` and `170.0 == 170` for integer-only receipt fields. The producer, independent consumer, and preparation entry point were corrected to require exact integer types. Final reviewed code hashes include:

- `content_revision.py`: `b24d0532ffabbc0e62a15061ffd394e0e06976217e77857b9555720704914ac5`
- `content_revision_quality.py`: `368c5ec40b3cb990f2d08f82bc5b385b5b4f8fea1126f9e5124bfac77693acac`
- `prepare_content_revision_b.py`: `68349eb93c11d3ff9edaf53aabc85fcc6131d24a36f90098882129a4c7a972de`

After that fix, both producer and independent consumer rejected all 13 tested attacks/malformed inputs: forged crop hash, missing fragment conflict, missing OCR conflict, wrong subject, omitted revision, duplicate conflict, expanded source region, a re-signed crop that removes observed ink, empty revision list, wrong list type, Boolean zero, floating-point zero, and floating-point threshold.

The archived pre-change reader at `c3cc2df` explicitly rejects plan schema 0.3 in both producer and consumer paths; the consumer reports `CONTENT_REVISION_DATA_INVALID`. Its accepted schema sets also exclude graph/check 0.8. The current adapter accepts only the matched 0.7/0.7 and 0.8/0.8 graph/check pairs and rejects mixed or unknown pairs.

## Execution and regression evidence

The coordinator's final integration record contains four accepted READY runs:

- `merged-cold`: 14/14 stages, 0 cache hits, 61.703 s.
- `merged-warm`: 14/14 stages, 14 cache hits, 39.969 s; outputs match the first merged run.
- `restore-q9`: 14/14 stages, 12 cache hits and 2 rebuilt, 43.547 s. The restored graph payload and content hash exactly equal the prior Q9 graph (`fef9a722ee523de46503a4347024ae3887c2da7bac69fe56f8d0355b88407ca1`). The integration record now asserts `restore_q9_payload_and_content_hash_exactly_equal=true` and `restore_q9_artifact_id_regenerated_by_new_code=true`; the regenerated artifact ID is intentionally different and is not claimed to be the old reference.
- `reapply-merged`: 14/14 stages, 14 cache hits, 40.360 s; outputs again match the first merged run.

Repository regression command recorded by integration: 51 tests passed in 108.906 s. I also independently reran the focused geometry/adapter set (14 tests, all passed), the revision-8 structural/non-regression audit, the 13 adversarial cases, and the old-reader rejection test.

The exported chapter candidate is `PARTIAL/HOLD` and is bound to the exact G0.8/Check0.8 references above. Independent candidate file SHA-256: `196cc31ea0e4f1647f977aa444ac790709bc25da9b760e33cfb26afe657545a`.

## Release guidance

The revision-8 machinery and merged artifact are suitable for integration under the current draft/HOLD contract. Do not represent Q4 geometry or the chapter as human-verified or business-accepted until the outstanding manual review is completed. This audit made no changes to the shared repository.
