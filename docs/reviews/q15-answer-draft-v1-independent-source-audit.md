# Q15 answer draft v1 — independent source audit

Date: 2026-10-18 (Asia/Shanghai)

## Verdict

**Independent model-visual source audit PASS for the six-line mathematical transcription and cross-column order.** I found no substantive character, operator, exponent, fraction, or formula mismatch between the draft and the supplied frozen pixels.

The package must nevertheless remain **MODEL_DRAFT / HOLD**. This review is not human verification, business acceptance, publication approval, or authorization to write the draft into the active graph.

## Frozen package and pixel binding

- Package: `B-46007447-page7-q15-answer-draft-v1-HOLD-2026-10-18.zip`
- Package SHA-256: `13e27682d4f33321468d0b28bc84bd25297e0ddfc7eaa87f84202df1af2a8a54`
- `draft.json`: `194210d3ada7be4f7aea70a85251e2e8cf9dc128f269b051913cc99231dd9d34`
- question source (`viewer-15`, printed page 7): `7c1a4afec69a94371fa31b6111969ca3d6ec39d7d7c6b1c73764f90316a610dd`
- answer source (`viewer-173`, printed page 25): `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`

Both crop files were independently compared pixel-for-pixel with the declared XYXY regions of the answer source:

- `q15-start.png`, 491×26: exact pixel match; RGB SHA-256 `dc2bbeb2eeb33d190667d672907cc64ac91df644f204ead4abbafa23c2d14d55`.
- `q15-continuation.png`, 497×114: exact pixel match; RGB SHA-256 `2a3f8272edf363a1dcb38dfcc969cc033ed346581a0a05668953124c4ce9582d`.

All supplied manifest hashes matched the extracted files.

## Identity and reading order

The question source is printed Q15 in section “2 一定是直角三角形吗”: square `ABCD`, midpoint `E` of `BC`, point `F` on `CD`, `CF=1/4 CD`, prove `∠AEF=90°`. The answer uses the same construction and conclusion, so it is not the other same-number lawn-area problem.

The cross-column order is visually and syntactically supported:

1. The bottom-left answer line begins `15. 解：` and ends `∠B=∠C=`.
2. With no remaining answer line below it, the right-column top begins `∠D=90°`, completing the equality chain.
3. Five consecutive right-column lines finish the proof with `且∠AEF=90°`.
4. The next right-column content is the separate “综合题” section, confirming the proof boundary.

Thus the six-source-line order `[left-bottom, right-top × 5]` is correct.

## Character-by-character findings

The following easy-to-lose source characters are present correctly in the draft:

- logical signs `∵` and `∴` throughout;
- angle signs in `∠B`, `∠C`, `∠D`, and `∠AEF`;
- the complete fraction `\frac{1}{4}CD`;
- lowercase parameter `a` in `4a`, `2a`, `a`, `3a`, and every squared term;
- all required squares in `AE²`, `AB²`, `BE²`, `20a²`, `EF²`, `EC²`, `FC²`, `5a²`, `AF²`, `AD²`, `DF²`, and `25a²`;
- `Rt△ABE`, `△AEF`, and the final `90°`.

The source itself uses `FC²` in `EF²=EC²+FC²`; the draft correctly preserves that order rather than normalizing it to `CF²`.

## Concrete artifact issues before production use

These do not invalidate the pixel transcription, but must be resolved in any formal revision plan:

1. **Printed-number duplication risk.** `draft_text` begins `15. 解：`, whereas the archived active answer `text` begins at `解：` and stores `printed_number: "15"` separately. A direct replacement with `draft_text` would duplicate the number at the data-model level. A production payload should explicitly separate the printed marker from answer text.
2. **Math-markup ambiguity.** `draft.json` contains `\frac{1}{4}` and `^{2}` fragments without math delimiters, while the README wraps formulas in `$...$`. Until the target formula consumer is specified and rendered, these strings could display as literal backslashes/braces. The formal plan must choose one exact representation and verify its rendering.
3. **Loss inventory overstates one item.** `identified_old_text_losses` lists a missing superscript on `AF`, but the archived old OCR text already contains `AF²` at both visible occurrences. The true missing-square losses are the two `AE` occurrences and the `EF`, `EC`, and `FC` occurrences. Correct this metadata so it describes observed deltas only.
4. **Typography remains intentionally non-pixel-exact.** Added spaces and normalized sentence dots are disclosed editorial choices. They are acceptable for a semantic draft, but cannot be described later as exact glyph-level transcription without a separate typography review.

## Scope

- No OCR, browser, model, or network call was made.
- Only the supplied original images, two exact crops, manifest, archived answer snapshot, and six draft lines were reviewed.
- No active graph, shared repository, or production artifact was modified.

