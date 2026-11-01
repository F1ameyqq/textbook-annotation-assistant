# Viewer-15 question source draft v2: independent audit

Date: 2026-10-17 (Asia/Shanghai)  
Draft file: `question-source-draft-v2.json`  
Draft file SHA-256: `2c9ec62f158d3dd9dbbdb59ed2fb80b21625dfbcccc311e433ccbf8d76fce9ff`  
Source image SHA-256: `7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd`  
Scope: independent source/pixel audit only; no shared-repository changes or full regression run

## Verdict

**Mathematical/source geometry: PASS. Full visible-content completeness: NEEDS ONE SMALL REVISION.**

The six question regions, twelve independent A–D options, seven `value=null` response blanks, three Q16 task blocks, six fraction-component receipts, and two figure crops agree with the original page pixels. No mathematical text, formula, blank, or figure-boundary error was found. However, four visible in-question editorial badges are inside the stem crops but silently absent from the structured runs. They should be represented explicitly or explicitly excluded as decoration before this draft is frozen as the complete source projection.

All new text remains `MODEL_VISUAL_TRANSCRIPTION` / `UNVERIFIED`. This audit does not convert it into human-approved or gold transcription.

## Independent integrity checks

- Draft payload hash recomputes exactly.
- Source image hash and 1219 × 1703 dimensions match.
- Baseline, refined-evidence, and graph references match the published viewer-15 observation artifacts.
- The page OCR snapshot exactly matches all 62 frozen OCR rows.
- The source ledger contains exactly those 62 line IDs once each: 59 question-source rows and three decoration/footer rows.
- All six archived original question objects exactly match the frozen graph.
- The six question regions are pairwise disjoint and contain every archived original fragment.
- All 23 block bboxes lie inside their owning question regions and are mutually non-overlapping within a question.
- Every one of the 23 PNGs is an exact, unscaled RGB crop of the declared source bbox; PNG hashes, RGB hashes, and dimensions all match.
- Every numerator/bar/denominator component hash recomputes from the original source image.
- All questions remain `counting_status=UNKNOWN`, `section_status=INFERRED_UNVERIFIED`, and `answer_link_status=UNMATCHED`.
- Draft state remains `HOLD`, with human verification, transcription verification, and business acceptance false and no platform actions.

## Required correction

Four visible badges occur inside the source stem crops but are omitted from the corresponding structured text:

1. Q11: boxed/stylized `A` before “教材经典设问”.
2. Q14: `NEW` badge before “数学文化”.
3. Q15: boxed/stylized `A` before “教材经典图形”.
4. Q16: boxed/stylized `A` before “清华附中校本经典题”.

Recommended fix: add an explicit source-bound `editorial_badge`/`decoration` component for each, with its own bbox and RGB receipt, or record a per-block, source-bound exclusion stating that the badge is intentionally non-semantic decoration. Do not silently omit pixels that fall inside a block advertised as a complete stem crop.

One ledger-label clarification is also advisable: OCR lines 0 and 1 are the visible column headers “中档题” and “综合题”, while line 61 is the page footer. Replace the combined `PAGE_HEADER_OR_FOOTER` status with `COLUMN_HEADER_DECORATION` for 0/1 and `PAGE_FOOTER` for 61. This does not change question content or counts.

## Question-by-question findings

### Q11

- Stem wording and single-choice blank agree with the source.
- A–D are four distinct blocks in correct order and with complete text.
- Required correction: preserve or explicitly exclude the visible boxed `A` editorial badge.

### Q12

- Stem correctly restores `△ABC` and `∠A/∠B/∠C` from pixels while remaining model-unverified.
- Choice blank and all four independent options agree with the source.
- Option formulas/text, including `b²-c²=a²`, radical values, angle equations, and the `3:4:5` angle ratio, are visually consistent.
- No correction found.

### Q13

- Stem and A–C agree with the source.
- Option D correctly reads “点A到BC的距离为 `5/2`”. Its numerator, bar, and denominator geometry are separate, source-bound, and exact.
- Figure crop `[434,741,586,891]` contains the complete grid, triangle edges, and labels A/B/C without clipping or option-text intrusion.
- No correction found.

### Q14

- The title `《周髀算经》`, historical prose, examples, and final null result blank agree with the source.
- Required correction: preserve or explicitly exclude the visible `NEW` badge.

### Q15

- The draft correctly reads `CF=\frac{1}{4}CD` and “试说明：`∠AEF=90°`”. The fraction components are correctly bounded even though the supplemental CPU OCR did not recover them reliably.
- Figure crop `[398,1376,587,1548]` contains the full square, all A–F labels, and the drawn segments without clipping or neighboring-question intrusion.
- Required correction: preserve or explicitly exclude the visible boxed `A` editorial badge.

### Q16

- The common stem and four displayed triples agree with the source.
- Task (1) preserves label 1 structurally, `11`, and two separate null blanks.
- Task (2) preserves label 2, all three example fractions, the general second-number expression `(a²-1)/2`, and the null third-expression blank. All four fractions have exact numerator/bar/denominator receipts.
- Task (3) preserves label 3 and the proof request.
- Task bboxes are ordered, non-overlapping, inside Q16, and do not cross into another question.
- Required correction: preserve or explicitly exclude the visible boxed `A` editorial badge.
- `answer_link_status=UNMATCHED` is correct; nothing in this draft links viewer-15 Q16 to the distinct viewer-11 Q16.

## Blank and formula inventory

Exactly seven null blanks are present:

- Q11, Q12, Q13: one single-choice blank each.
- Q14: one expression blank.
- Q16 task (1): two expression blanks.
- Q16 task (2): one third-number expression blank.

Exactly six structured fractions are present:

- Q13 D: `5/2`.
- Q15: `1/4` within `CF=1/4 CD`.
- Q16 task (2): `(3²-1)/2`, `(5²-1)/2`, `(7²-1)/2`, and `(a²-1)/2`.

No blank has been filled, no answer has been inferred, and no OCR retry has been promoted to truth.

## Supplemental OCR disposition

The recovery directory records exactly eight ordinary CPU OCR calls: four bounded regions at scales 1 and 3. Its summary remains `MODEL_DRAFT`, `HOLD`, `transcription_verified=false`, with no network or paid calls. The source draft does not select or reference a recovery result. This is correct: Q15's OCR loss and Q16's erroneous general-expression OCR are retained as failed observations, not used as consensus or gold evidence.

## Final recommendation

Issue a v3 source draft containing the four explicit badge dispositions and the more precise header/footer ledger statuses. Apart from those metadata/completeness corrections, retain all v2 question text, formulas, null blanks, block/question bboxes, figure crops, OCR archive, question archive, answer-unmatched state, and HOLD flags unchanged.
