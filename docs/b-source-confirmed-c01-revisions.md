# B source-confirmed C01 revisions

These tools revise existing C01 envelopes. Review JSON and delivery sidecars are internal evidence; no public schema is introduced. An explicit B model source review selects source-owned answer fragments. A missing human signature is not itself an answer ambiguity.

`python -B tools/revise_source_confirmed_c01_b.py --source OLD_DELIVERY --review REVIEW.json --out NEW_DELIVERY` requires a complete predecessor inventory, original-image SHA values, confirmed regions and explicit answer selections. Source assets, crops, geometry, formulas, blank values, answer text, shared fragments and stable local identities remain fixed.

The only supported transcription edits are the three printed prefixes `（1）`, `（2）`, `（3）` for `q16-task1`, `q16-task2`, `q16-task3`. Each edit must record exact before/after text and runs, original source SHA, original box, PNG SHA and RGB SHA. Only the first plain run may receive its exact prefix. Other text edits, formula edits, filled blanks, wrong crop hashes, incomplete label restoration or cross-question answer selections are rejected.

Changed predecessor JSON files, including its HOLD and pending-review state, remain exact bytes under `history/v2/`. All other original files remain byte-identical. `--frozen NEW_DELIVERY --out FRESH_DELIVERY` reconstructs the original member set from these overlays and reproduces the current revision without old producer code or new OCR.

`python -B tools/verify_source_confirmed_c01_b.py --delivery NEW_DELIVERY --out NEW_RECEIPT.json` independently validates the inventory, narrow text delta, original pixels, rich runs, formula/task spans, shared structure, selected answer ownership and content/PRE_APPLY distinction. It does not import the revision producer. The pinned A24 reader remains `annotation.contracts.load_bundle(..., verify_assets=True)` with complete object equality.

The portable replay supports exactly two registered local entry pairs: the lesson exporter/verifier and this revision producer/verifier. It checks complete manifest membership, rebuilds all delivery bytes and invokes the unchanged read-only A24 consumer. It installs nothing, performs no OCR and makes no platform requests.

The Q16/reading revision contains four tasks, one shared material with eight shared fragments used by the three reading tasks, 26 active fragments, 37 original crops, six null blanks and eleven diagnostic formula regions. Section-2 Q16 has its own local directory, distinct from lesson-1 Q16. Current B content issues are empty after the three printed-label fixes. C01 PRE_APPLY remains HOLD for formal platform policy and whole-page/full-chapter target coverage; independent human, A-owner and platform acceptance are separate, unasserted states. Root review, independent QA, integration and push are not implied by local success.
