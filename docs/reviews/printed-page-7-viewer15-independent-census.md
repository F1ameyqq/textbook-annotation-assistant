# Printed page 7 / viewer-15 independent census

Date: 2026-10-17 (Asia/Shanghai)  
Scope: the single newly frozen original page only; not a chapter inventory or answer denominator  
Code baseline recorded by integration: `af8e17c2ed60219db4f0da40daea6be0396c4b5b`  
External website/model calls: none

## Verdict

**Page census: PASS. Candidate content completeness: FAIL/HOLD.**

The original page visibly contains exactly six top-level numbered questions, 11–16. The current graph finds all six numbers and keeps separate A–D option starts for questions 11–13, but it is not a complete transcription: both figures are absent from candidate content, several mathematical symbols/fractions are flattened or lost, Q15 is materially truncated, and Q16's fraction structure and blanks are incomplete. The six candidates must therefore remain unverified and must not be treated as complete source content.

## Fixed evidence

- Original image: `46007447_page_14.jpg`
- Viewer page: 15
- Printed page: 7
- Dimensions: 1219 × 1703
- Image SHA-256: `7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd`
- Corrected source single-page package SHA-256 recorded by integration: `50f053175c487c2f35b1d1a4749aa1e06a65e52cc20b41db2ba3e976a2610d45`
- Frozen observation v2 ZIP SHA-256: `02750621e4ded908c4efd01d022201e57fd1574b57d9c3b418699fcd41e86daa`
- Corrected integration record SHA-256: `c65111eb6f51965a0d1f8e297d76ed37b2b7923c0b9b89f25f68a331db12a2f7`

The source package and observation both state that this is one newly frozen page and not a frozen chapter inventory.

The unpublished v1 package had included an API URL inferred from the page number. That inference was removed: the corrected metadata keeps the actually observed original-image URL and explicitly states that the complete API URL was not saved. The original image, all 62 OCR lines, graph, issues, and cold/warm execution files are byte-for-byte unchanged. The unpublished v1 bytes were moved to coordinator history and are not cited as final evidence here.

## Page structure

- Left column, “中档题”: questions 11, 12, 13, 14, and 15.
- Right column, “综合题”: question 16.
- Questions 11–13 are four-choice items with visibly independent A, B, C, and D alternatives.
- Question 14 is a fill-in/open-response item.
- Question 15 is a proof item with a figure.
- Question 16 is a shared setup with subparts (1), (2), and (3).
- Two source figures are visible: the Q13 grid/triangle diagram and the Q15 square `ABCD` diagram.

This is a page-local structural description only. It does not establish a whole-chapter count, answer denominator, or scoring-unit count.

## Question-by-question source check

### Q11

- Source topic: scale all three sides of a right triangle by the same factor and identify the resulting triangle.
- Four independent options A–D are visible and separately retained by the candidate.
- Candidate gap: the closing answer parenthesis/blank is not represented, and the decorative boxed `A` label is flattened into the stem text.
- No answer is printed or independently bound.
- OCR lines: 3, 4, 6, 8, 10, 12.

### Q12

- Source topic: given sides opposite `∠A`, `∠B`, and `∠C`, select the condition that cannot establish a right triangle.
- Four independent options A–D are visible and separately retained.
- Material transcription loss: angle symbols `∠` are dropped in the candidate stem and in options C/D. Mathematical expressions remain unverified OCR text, not normalized formulas.
- No answer is printed or independently bound.
- OCR lines: 14, 16, 18, 20, 23, 26, 31.

### Q13

- Source topic: inspect triangle `ABC` on a unit square grid and select the incorrect conclusion.
- Four independent options A–D are visible; their source meanings are `BC=5`, area of `△ABC` is 5, `∠A=90°`, and the distance from A to BC is `5/2`.
- The Q13 grid/triangle figure is visible in the source but is absent from candidate fragments.
- Material candidate defect: option D's fraction `5/2` is split into OCR atoms; the numerator `5` is attached to the preceding option-C fragment and the denominator `2` is detached as a stem fragment. The assembled candidate therefore does not faithfully preserve option D.
- The triangle and angle symbols are also lost from candidate text.
- No answer is printed or independently bound.
- OCR lines: 35, 37, 39, 42, 43, 45, 47, 48, 49.

### Q14

- Source topic: a historical/cultural Pythagorean-triple pattern; given an even leg 10 in the described family, fill in the hypotenuse.
- The prose is substantially retained, but the printed response blank after “弦为” is not represented as a typed field or answer candidate.
- No printed answer is present.
- OCR lines: 50–57.

### Q15

- Source topic: in square `ABCD`, E is the midpoint of BC, F lies on CD, and `CF = 1/4 CD`; prove `∠AEF=90°`.
- The Q15 square diagram with A–F labels is visible in the source but absent from candidate fragments.
- Material candidate defect: OCR retains only `CF=` and a detached `4`; it loses numerator `1`, the fraction bar, `CD`, the proof request, and `∠AEF=90°`. The current candidate is therefore severely truncated.
- No proof or answer is printed or independently bound.
- OCR lines: 58–60.

### Q16

- Source setup: Pythagorean triples `3,4,5`; `5,12,13`; `7,24,25`; `9,40,41`, observing consecutive odd first terms from 3.
- Subpart (1) asks for the next triple. The printed scaffold shows `11,` followed by two blanks; OCR retains `11,` but not the two blank fields.
- Subpart (2) lets the first number be odd `a≥3`, asks for formulas for the other two numbers, and prints the examples `4=(3²-1)/2`, `12=(5²-1)/2`, and `24=(7²-1)/2`. It then prints the second number as `(a²-1)/2` and leaves the third-number expression blank.
- Subpart (3) asks for a proof that the three expressions from subpart (2) form a Pythagorean triple.
- All three subpart labels and their prose anchors survive, but formula preservation fails: numerators, denominators, fraction bars, and reading order are atomized; the candidate loses the numerator `a²-1` entirely from the general second-number formula and does not preserve the response blanks.
- No source answer is printed or independently bound.
- OCR lines: 2, 5, 7, 9, 11, 13, 15, 17, 19, 21, 22, 24, 25, 27–30, 32–34, 36, 38, 40, 41, 44, 46.

## Q16 identity check against the existing graph

Printed number alone is not a valid identity key. Independent comparison proves that the existing graph's Q16 and this page's Q16 are different questions:

- Existing graph Q16: source asset `viewer-11`; “月牙图” geometry problem; two subparts; semicircle-area relationship/application.
- New page Q16: source asset `viewer-15`; Pythagorean-triple pattern problem; three subparts; algebraic fraction formulas and proof.

They differ in source asset, stem, figures/material, subpart count, and requested work. No existing Q16 answer or match may be applied to viewer-15 Q16.

## OCR, graph, and quality evidence

- OCR lines: 62 total, IDs `viewer-15/ocr/0` through `viewer-15/ocr/61`.
- Layout mode: `two_columns`; cut x = 609; left boxes 34; right boxes 28; body-crossing boxes 0.
- Layout verification: false.
- The only unscoped lines are the two column headers (0, 1) and footer (61).
- All 62 OCR lines are accounted for: headers 0/1; Q11 as listed above; Q12 as listed above; Q13 as listed above; Q14 50–57; Q15 58–60; Q16 as listed above; footer 61.
- Graph: 6 candidate questions, printed numbers 11–16, 0 answers.
- Check: 12 issues and `HOLD`: six `ANSWER_MISSING_OR_AMBIGUOUS`, four `FIGURE_OR_FORMULA_REVIEW` (Q12, Q13, Q15, Q16), one `SHARED_MATERIAL_STRUCTURE_REVIEW` (Q16), and one `BUSINESS_REVIEW_REQUIRED`.
- `transcription_verified=false`, `business_acceptance=false`, `human_verification=false`.

The candidate question objects correctly remain `verification_status=UNVERIFIED`. Their presence is evidence of candidate detection, not proof of complete content.

## Execution evidence

- Cold run: READY, audit accepted, 4/4 stages, 0 cache hits, one `ocr_atoms` entry call, 32.844 s, decision HOLD.
- Warm run: READY, audit accepted, 4/4 cache hits, zero OCR entry calls, 0.922 s, decision HOLD.
- No paid model calls and no network connections were permitted for these runs.

Pipeline audit acceptance confirms artifact/run consistency only; it does not override the content defects or HOLD state above.

## Section-path constraint

Every candidate currently carries `第一章 勾股定理 / 2 一定是直角三角形吗`. The printed page itself shows only the column headings “中档题” and “综合题”; it does not print that section path. The path was inferred from adjacent printed page 6 and remains unverified for this page. It must not be used as sole evidence for cross-page identity or answer matching.

## Required disposition

- Preserve six page-local top-level candidates, numbered 11–16, as unverified drafts.
- Preserve A–D as four independent source options for each of Q11–Q13, but repair Q13 option D's fraction before any use.
- Add source-bound representations for both figures before claiming content completeness.
- Reconstruct and independently verify Q15's full ratio and proof request.
- Reconstruct Q16's three subparts, all example fractions, the general `(a²-1)/2` formula, and all blank fields from source pixels before matching or export.
- Do not match viewer-15 Q16 to the existing viewer-11 Q16 or reuse its answer.
- Do not promote the inferred section path, candidate count, or this single-page census into a chapter-wide denominator.

No shared-repository files were changed during this independent census.
