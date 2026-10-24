# B lesson C01 portable delivery

`tools/export_lesson_c01_b.py --spec INPUT --out NEW_DIRECTORY` freezes locally reviewed source content into existing C01 SourceBundle, EvidenceBundle, QuestionGraph and CheckReport envelopes. The input spec and delivery sidecar are internal producer evidence, not replacements for the public C01 contract. Private source paths are replaced by relative resource paths. Preserve originals outside the release.

`--frozen DELIVERY --out NEW_DIRECTORY` reproduces a frozen delivery using its basis, original images and generation context. No OCR, network, native identity, planning or platform write is performed.

`tools/verify_lesson_c01_b.py --delivery DELIVERY --out NEW_RECEIPT.json` independently checks source hashes, crop pixels, question fields, null blanks, selected answer ownership, diagnostic-only combined options and corrected child geometry. It does not import the producer. Synthetic tests cover the boundaries rather than asserting business acceptance.

The portable release includes the unchanged read-only consumer and 50 source files pinned to A24 commit `c5aefbc8e995c410b3babf74a251f05a7724a1c2`. Its actual entry is `annotation.contracts.load_bundle(..., verify_assets=True)`, followed by complete object equality. It blocks delivery/runtime/target imports, networking and subprocesses before contract import.

Run `python -B tools/replay_lesson_c01_b.py --package PACKAGE --out FRESH_EXTERNAL_DIRECTORY` using Python 3.12, Pillow 12.3.0 and Pydantic 2.14.1. Replay checks manifest membership and hashes, rebuilds all delivery bytes, runs the independent verifier, then invokes the pinned A24 reader. Dependencies must already exist; replay installs nothing. Python 3.11 is not validated with the unchanged consumer guard.

For lesson 2, the release contains 9 questions, 9 source-confirmed selected answer associations, 3 original pages, 46 crops, 43 active fragments and 12 independent option regions. The previous 3 combined option windows remain diagnostic evidence. Q7's reviewed top expansion is explicit. Q5 has the complete worked answer and no separate analysis; the variant states truck height 4.1 m and width 3 m. All EXCLUDED clues have empty region IDs. Eight printed answer blanks remain null.

B content readiness and PRE_APPLY readiness are separate: B content is ready, while the C01 report remains HOLD for joint policy adoption and full-page target readiness. Ordinary source-confirmed questions do not require an additional per-question human signature. A-owner, independent human and platform acceptance are not asserted. Root integration owns final review, tracked handoff placement and push.
