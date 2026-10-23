# Frozen section sources to C01

The section projection entry reads the existing source-spec facts and original local assets/crops. It produces the existing private lesson-export input, then uses the unchanged public C01 envelope fields. It does not add a public schema, OCR engine, native writer or platform dependency.

```text
python -B tools/project_section_source_c01_b.py --source PRIVATE_SOURCE_DIRECTORY --splits PRIVATE_SPLIT_EVIDENCE.json --archive-sha256 ORIGINAL_ARCHIVE_SHA --manifest-sha256 ORIGINAL_MANIFEST_SHA --out NEW_PRIVATE_INPUT.json
python -B tools/export_lesson_c01_b.py --spec NEW_PRIVATE_INPUT.json --out NEW_DELIVERY
python -B tools/verify_lesson_c01_b.py --delivery NEW_DELIVERY --out NEW_RECEIPT.json
```

The source directory and projected input are private. The producer freezes relative assets and a derived source evidence projection. It retains original archive/spec/manifest/OCR/image/metadata SHA values, region coordinates, raw OCR row observations and source corrections. Absolute paths, native response bodies and native identities are omitted. The projection explicitly states that its JSON is not original HTTP or original spec bytes. Do not publish the original source ZIP: it contains personal paths and native metadata.

Multiple question/answer regions require explicit source-bound text splits. Region IDs must follow the original order and split texts must concatenate exactly to the source field. Region ownership, source SHA, original pixels, source blanks and any supplied per-region transcript are checked. Every declared source region must be used once.

Optional internal rich runs retain the exact source lexeme alongside canonical LaTeX for numeric fractions, Unicode powers, simple subscripts and square roots. Their source-text concatenation must equal the frozen field exactly. Blank IDs remain bound to original null slots. Unsupported math forms are not guessed or normalized. The independent verifier checks formula meaning and exact text, original crop pixels, source field/order/ownership and selected answers. These run fields are sidecar evidence, not new C01 fields.

The concrete section-2 Q1–Q15 scope excludes Q16 and all three adjacent reading tasks. It includes 15 selected source-confirmed answer relations, 65 fragments/crops, 28 independent options, five diagrams, five null blanks and 72 math runs. Q7 keeps its intentionally wrong worked solution in the cross-column question; its correct answer remains separate. Q15's answer continues from the left-column bottom to the right-column top. Q9's squares and Q13's false option 5/2 remain source facts.

B content readiness is distinct from C01 PRE_APPLY HOLD for joint execution policy and whole-page/full-chapter target coverage. Missing human signatures do not create a blanket answer ambiguity. Current A-owner, independent human and platform acceptance are not asserted. Root review, independent QA and push remain separate from local verification.
