# Printed page 5 / viewer-13 independent census

Date: 2026-10-17 (Asia/Shanghai)  
Scope: the single newly frozen original page only; **not** a chapter inventory or chapter denominator  
External website/model calls: none  

## Fixed evidence

- Original image: `46007447_page_12.jpg`
- Viewer page: 13
- Printed page: 5
- Dimensions: 1219 × 1691
- Image SHA-256: `997b37d35fca57f73ab71e53f6721be145d10c436deab5fab38bf1ae0d31dc1e`
- Frozen observation ZIP SHA-256: `6f96dfd58be360e42fbd88266b0e5691dd905311c45d53b6a559f6d46e105a94`
- Observation scope note: “One newly frozen original page only; chapter inventory not frozen.”

## Page-level census

The page visibly contains three distinct instructional blocks:

1. A numbered top-left exercise, printed as **8** and labeled “教材习题变式”. It asks whether a 4.1 m high, 3 m wide truck can pass through one lane of a semicircular tunnel of radius 5.2 m, with the center-line width ignored. A semicircle diagram with center `O` is present.
2. An unnumbered top-right block labeled **“变式”**. It changes the tunnel to a single-lane semicircle of radius 4.3 m and asks whether the truck from the preceding problem can pass. A second semicircle diagram with center `O` is present.
3. A lower two-column shared reading/activity block titled **“漫话勾股世界——教材P6‘阅读·思考’变式”**. It introduces Zhao Shuang's chord diagram and Leonardo da Vinci's dissection proof, followed by tasks **(1), (2), and (3)**.

This supports the page-local statement “one printed top-level number (`8`), one explicitly labeled but unnumbered variant, and one shared reading block containing three numbered tasks.” It does **not** establish how any of these units should count in a whole-chapter denominator.

## Top exercise and variant

### Printed question 8

- Location: upper-left column.
- Given quantities visible in the source: semicircle radius 5.2 m; truck height 4.1 m; truck width 3 m; two lanes divided by the middle line; middle-line width ignored.
- Requested judgment: whether the truck can pass while driving in one lane.
- Printed answer/work: none visible.
- OCR coverage: lines 1, 3, 4, 6, and 7.
- OCR caveat: line 3 reads the diagram label `O` as digit `0`.

### Unnumbered “变式”

- Location: upper-right column.
- Given quantities visible in the source: semicircle radius 4.3 m; single-lane tunnel; same truck as question 8.
- Requested judgment: whether that truck can pass.
- Printed answer/work: none visible.
- OCR coverage: lines 0, 2, and 5.
- OCR caveat: line 2 reads the diagram label `O` as digit `0`.

The source image clearly separates these as two prompts, but only the left prompt bears the printed number 8. Whether the unnumbered variant becomes an independent platform question is **unknown and requires policy/business review**.

## Shared reading material

### Visible setup

The lower block explains that the Pythagorean theorem has many proofs, then presents:

- Zhao Shuang's construction: four congruent right triangles form the chord diagram in Figure 1; `a` and `b` are the legs and `c` is the hypotenuse; quadrilaterals `ABDE` and `CFGH` are squares.
- Leonardo da Vinci's Figure 2 construction: before cutting, the blank region comprises two squares and two congruent right triangles (`S₁`); after cutting and flipping, it comprises two congruent right triangles and one square (`S₂`).

OCR coverage for the prose is lines 11, 13–15, 17, 19, 21–23, and 25–30. Figure captions and action labels are lines 24, 32, 33, 35, and 37.

OCR uncertainty is material here: OCR flattened subscripts (`S₁`/`S₂`), split the two columns into one global sequence, and did not scope prose to figures or tasks. The original image, not OCR alone, is the authority for this census.

## Task structure

### Task (1): complete Zhao Shuang's proof

- Location: starts at lower-left and continues at the top of the lower-right column.
- Prompt: complete Xiaoying's verification using Figure 1.
- Printed scaffolding visibly includes:
  - `S` of square `ABDE` equals four times `S` of triangle `ABC` plus `S` of square `CFGH`;
  - a blank for the side length of square `CFGH`;
  - `S` of square `ABDE = c²`;
  - a blank for `S` of triangle `ABC`;
  - a blank for `S` of square `CFGH`;
  - the printed derivation `c² = 4 × 1/2 ab + (a-b)² = ...`, ending in `a²+b²=c²`.
- Blank count visible: three.
- OCR coverage: lines 40–45, then 10, 12, and 16 across the column continuation.
- Unknowns: the blanks are not filled on the printed page. The later printed derivation strongly suggests intended expressions, but this census does not convert those implications into verified answers.

### Task (2): reproduce a proof from Figure 2

- Location: lower-right column, mid-page.
- Prompt: follow Xiaoying's verification and use Figure 2 and its labels to write a verification of the Pythagorean theorem.
- Response form: open written proof; no printed answer or completed work visible.
- OCR coverage: lines 18 and 20.
- Unknowns: expected proof wording, scoring units, and whether intermediate equal-area statements are separately required.

### Task (3): provide another visual proof

- Location: lower-right column, below task (2).
- Prompt: give an algebraic identity other than the one just discussed that can be explained by a “proof without words,” draw the figure, and write the identity.
- Response form: open construction plus identity; no printed answer or completed work visible.
- OCR coverage: lines 29, 31, 34, 36, 38, and 39.
- Unknowns: accepted identities, equivalence policy, drawing requirements, and scoring rubric.

## Original OCR/layout evidence

- OCR lines: 48 total, IDs `viewer-13/ocr/0` through `viewer-13/ocr/47`.
- Layout mode: `UNRESOLVED_LAYOUT`; verified: false.
- Detected central cut: x = 611.
- Left OCR boxes: 31; right OCR boxes: 16; body-crossing boxes: 1.
- Unscoped OCR lines: all 48.
- Answer-detail lines: 0.
- Assembly result: 0 questions and 0 answers.
- Quality result: `HOLD`, with `UNRESOLVED_LAYOUT`, `QUESTION_COVERAGE_MISMATCH`, and `BUSINESS_REVIEW_REQUIRED`.
- Pipeline audit accepted the mechanics of the four-stage cached run, but explicitly retained `business_acceptance=false` and `transcription_verified=false`.

Every OCR line is accounted for by the regions above; lines 46 and 47 are respectively the printed page number `5` and the footer `数学·八年级上·BS`.

## Disposition

The original page is sufficiently clear for a bounded structural census, but not for automatic assembly under the current two-column parser. Preserve the following as explicit unknowns pending human/business review:

- whether the unnumbered top “变式” is a separate platform question;
- how the reading block and its tasks (1)–(3) contribute to any product-specific count;
- the verified answer keys/rubrics for all five response opportunities (Q8, its variant, and tasks (1)–(3));
- whether task (1)'s three blanks are scored individually or as one proof;
- all chapter-wide totals and denominators.

No shared-repository files were changed during this independent census.
