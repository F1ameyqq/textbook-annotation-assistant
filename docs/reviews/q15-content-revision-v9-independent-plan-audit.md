# Q15 content revision v9 — independent plan and consumer audit

Date: 2026-10-18 (Asia/Shanghai)

## Technical verdict

**PASS for the exact frozen revision-9 plan, its two Q15 operations, source geometry, and materialized Q15 content, subject to a required rerun on the current shared baseline.** The plan retains the previous 14 operations byte-equivalently, appends exactly the two declared Q15 region operations, preserves raw OCR/source coverage, and materializes the reviewed six-line content without duplicating printed number 15.

**PARTIAL / do not overclaim for generic consumer enforcement.** Two negative claims in the preparation receipt are plan-builder-specific, not enforced by the reusable `content_revision` / `content_revision_quality` API: a correctly re-signed plan that prepends `15. ` to the region draft is accepted, and a correctly re-signed plan that changes the `\frac{1}{4}` run from `latex` to `plain` is also accepted. The exact frozen plan is correct, but those two properties require a higher-level assertion/test if the final evidence says the consumer itself rejects them.

This remains separate from content acceptance: **human verification, transcription verification, business acceptance, and platform action all remain HOLD/false/empty.**

## Frozen inputs

- Plan: `q15-content-revision-plan-v9.json`
- Plan SHA-256: `68ba66315e86b0efb8307f5fec17e4b7608a91ab4c0a6175cca8ef597383f0b7`
- Q15 delta operations SHA-256: `dd97ccac6e2c48b4d8916b0469c8b65a9092b393eb994a53486eed741b26ca28`
- Preparation receipt SHA-256: `670625101a979b4ae154a0a504d6d4e09a3f19f7b686f933482fab6cc9040d77`
- Draft source package SHA-256: `13e27682d4f33321468d0b28bc84bd25297e0ddfc7eaa87f84202df1af2a8a54`
- Independent source audit SHA-256: `d0b8be6dc65696648eca2f492adca38d6afdac9cdc7a52bb0a5115dc9efeb823`

The revision lineage is exactly 14 retained operations plus two Q15 operations. The current plan's first 14 operation objects equal the previous plan's operations, and its last two operation objects equal the standalone Q15 delta file.

## Four prior review comments

1. **Printed-number duplication — fixed in the frozen plan/output.** The left block begins `解：`, not `15. 解：`; `printed_number` remains separately `"15"`. The materialized active answer text does not start with `15.`.
2. **Math representation — fixed in the frozen plan/output.** Fraction and powers are explicit typed runs rather than delimiter-dependent mixed strings. There are 16 Q15 LaTeX runs; all 16 independently pass the existing offline inline parser. Browser/MathML rendering is still a separate required receipt.
3. **Incorrect AF² loss claim — fixed.** The receipt now says both `AF²` occurrences were already present and identifies only two `AE²` occurrences plus `EF²`, `EC²`, and `FC²` as missing squares.
4. **Typography scope — handled as an unverified semantic draft.** Spaces and sentence punctuation are explicit plain runs; no pixel-exact typography or human glyph approval is claimed.

## Source geometry and collision audit

### Left-bottom start

- Immutable fragment box: `[59,1515,535,1536]`.
- Effective revised box/source region: `[59,1516,535,1536]`.
- Trimmed strip: `[59,1515,535,1516]`.
- Independent fixed-threshold-170 pixel result: zero dark pixels.
- RGB SHA-256 of trimmed strip: `5f4c60163b2d98be1412ad424cc0233c68094c7e8e9575ec9121e2d1c207a551`.
- The only OCR row whose overlap is removed is `viewer-173/ocr/152`, box `[59,1499,244,1516]`, coverage `CONSUMED`.
- No graph fragment overlap is removed. The declared affected-fragment and affected-OCR lists exactly match the consumer's independent enumeration.

The one-pixel trim therefore removes only empty top padding and resolves the real half-open-boundary collision with the preceding Q11–Q14 short-answer row. It is not glyph approval.

### Right-top continuation

- Source region: `[585,130,1082,245]`.
- Ordered target fragments: OCR rows `2,3,5,7,9`, corresponding to the five continuation lines.
- Blocks are non-overlapping and remain in the original presentation order.
- The `1/4` gap has no coarse/detail OCR element; it is represented as `NEW_UNVERIFIED_REGION_DRAFT_TEXT`, not as invented OCR or a change to the 19-row source layer.
- The region ends before the following `综合题` row. Extending it into that row is rejected as foreign/untargeted source text.
- Left and right locations remain two independent region operations. They do not overlap source pixels and are not merged into a cross-column box.

## Independent consumer attacks

The matching baseline-13204a7 consumer accepted the honest frozen application and independently reconstructed its graph. The following re-signed mutations were then tested directly against `content_revision_quality`:

| Mutation | Result |
|---|---|
| Corrupt trimmed-pixel SHA receipt | Rejected: fixed zero-dark receipt differs |
| Omit the `ocr/152` affected-conflict row | Rejected: geometry/conflict receipt invalid |
| Bind the continuation to `viewer-14` | Rejected: source page/role/location differs |
| Extend the right region into the next tier | Rejected: covers foreign/structural/diagnostic text |
| Merge both columns into one mega-region | Rejected: source-region/effective-union mismatch (and cannot establish one location) |
| Reinsert `15. ` into active region text | **Accepted — generic semantic enforcement gap** |
| Change `\frac{1}{4}` run format to `plain` | **Accepted — generic typed-run enforcement gap** |

Accordingly, the receipt's `printed_number_duplicated` and `fraction_hidden_in_plain_text` entries may describe preparation-time assertions, but they are not reproducible consumer rejection guarantees in the current API.

A standalone plan-specific assertion is supplied as `q15-v9-high-level-assertions.py`, SHA-256 `daf6f731effe0565d2d8eb97c6f4bbb37482b957f3974b45ffe0b2a1b3fbcbbe`. Its self-test accepts the honest frozen plan/graph and rejects both a duplicated-number mutation and a plain-run fraction mutation. This is deliberately identified as a Q15 coordinator gate, not a property of the generic consumer.

## Baseline compatibility

The supplied application/check were generated and accepted under commit `13204a7ac3232a1042fdfa9e981e90c8857615da`, whose `offline.py` and `question_quality.py` dependency digests are embedded in the application producer receipt.

On current shared commit `b5cc1ea2a0cc1b50b051ffc5ad429e7b473f516a`, `content_revision.py` and `content_revision_quality.py` are unchanged, but Viewer-13 changes altered the `offline.py` and `question_quality.py` dependency digests. Therefore the pre-generated application is correctly rejected there as `content revision output header/producer/identity differs`. It must not be reused. The planned current-baseline 14-stage rerun must regenerate application, graph, check, and audits.

## Release boundary

Technical acceptance of the frozen plan requires all of the following in the coordinator's fresh run:

- regenerated current-baseline application/check accepted by the independent consumer;
- the two plan-specific assertions (`printed_number` absent from active text; fraction run remains typed `latex`) recorded explicitly;
- browser MathML/render verification for all 16 LaTeX runs;
- final decision remains `HOLD`, with `transcription_verified=false`, `business_acceptance=false`, and no platform actions.

No shared repository, active graph, or production artifact was modified during this audit.

