# P1-R1 mapping / candidate profile / local Schema auxiliary review

Input is the isolated exact Git export of final `ca4fba4f505467228a8164c3999e0cecc54ffc4e`, design `095ed4aa18a56100ce3aabc4a0d6885ad37ab520`, under `D:/1800/.local/stages/A03-review-P1-R1/ca4fba4f505467228a8164c3999e0cecc54ffc4e/`. This is an auxiliary static audit; the parent alone issues the formal P1 conclusion.

Result: no additional blocking issue found in the assigned mapping, candidate-profile selection, namespace clarification or local Schema scope. This statement does not assess the separate API-prefix issue and does not execute any future behavior.

## Actual independent checks

- Strict JSON parsing accepts all 165 formal candidate JSON files: 164 below `data/` plus `api-proposal.json`. Duplicate keys and nonfinite numbers are rejected by the reader. Failed generation attempts are not treated as the formal package.
- `case-mapping.json` maps the original 42 cases exactly once, injectively into 69 cases. All original and new case SHA256 values match actual exported bytes. Original/new manifest layer, expected code, static class and source-case identity match for all 42. Semantic status remains `EXPECTED_NOT_EXECUTED`.
- The independent finite `LocalAssertions` evaluator accepts/rejects case wrappers and recursively referenced ActionFact/basis resources as expected for all 69. The five structural negatives are wrong schema, wrong exchange, fourth reconcile attempt, absent tail basis, and EXECUTION fact with a nonnull basis. The evaluator was retained from the prior independent P1 reviewer, not copied from the author checker. It resolves only local schema files and rejects unreviewed assertion keywords. Full standards-validator certification was not run.
- All six `candidate_profile.schema_files` SHA256 values match the actual schema bytes; no formal schema file is omitted. Top-level schema/exchange version strings equal the old unaccepted P1 candidate, as explicitly declared. The selection text pins the exact P1-R1 directory, Git delivery and schema hashes, excludes fallback/mixed P1 shapes, and states that profile metadata is not runtime authority. There is no implemented loader profile to functionally test in P1.
- All seven migration-map old/new refs match the actual archive and new normal bundle. Their declared namespaces match each enclosing schema/exchange version; namespaces differ while local ID/revision/kind remain the same. The future key includes namespace plus book/scope/id/revision, with kind/hash immutable. Ordinary four-field refs stay scoped to their owning candidate closure. P1/P1-R1 are alternative revisions of an unaccepted profile, not two concurrently admitted schemas. No historical UNKNOWN/intents were created by this audit.

## Closing the 40 projection differences

`audit-results.json` retains a detailed old/new projection for every original case. The projection strips only the corrected `input_refs`, resealed `content_hash`, relocated Resource path/SHA, and newly introduced `unattempted_basis`; it inlines the actual local resource JSON and aligns Artifact lists by ID/revision rather than abandoning comparison when an Artifact is added. It is a review aid, not an acceptance algorithm. Hash-based attack triggers are checked separately below.

The initial summary field `case_projection_diffs_require_human_review=40` is the count before this review, not 40 unresolved findings. `trigger-retention-results.json` closes all 42 comparisons and records zero unclassified changes. The observed difference categories are:

| Category | Difference occurrences | Review disposition |
|---|---:|---|
| Derived state/dependency digest and obligation resealing | 608 | Expected propagation after corrected consumer declarations and resource bytes; no changed business field outside the following five cases |
| Dedicated UNATTEMPTED_ABSENCE facts/prepared/resources and two design reads | 278 | Present only in partial-complete, fabricated partial, original-UNKNOWN and recovered-report representations; origin changes from EXECUTION to the new branch, with first-observation prepared and independent second-observation readback. They remain design data |
| Explicit INTERRUPTED/read-only branch metadata | 67 | Added to the same partial/recovered cases; no dispatch/effect or implementation claim |
| Explicit B UNKNOWN ledger pause/pending rows | 15 | Only the three partial cases; preserves the intended pending-book behavior that old example ledger fields omitted |
| Additional unattempted-observation snapshot Artifacts | 6 | One each in partial-complete/fabricated partial and two each in original-UNKNOWN/recovered report; new frozen design observations, not executed reads |

The five cases with non-digest differences are `partial-without-absent`, `partial-with-complete-absent`, `partial-fabricated-receipt`, `original-unknown-preserved`, and `recovered-report-binding`. Original receipt outcome/attempt/effect/replay fields and progress classifications remain the same. Original UNKNOWN receipt data is retained; tail facts use the newly specified representation. The normal all-attempted case retains EXECUTION fact semantics (with the new nullable basis field) and has only derived-digest changes under this projection.

## Core trigger preservation

`audit_trigger_retention.py` independently extracts named core fields from old/new actual JSON, separately from manifest expectations. The resulting 42-row old/new table is in `trigger-retention-results.json`; all 42 core signatures match. The coverage includes:

- All normal/match/absent/conflict/indeterminate outcomes, attempt facts, progress outcomes, `replay_allowed=false`, final PENDING/NOT_SUBMITTED, and recovered report HOLD/state bindings.
- Partial C still has no intent; insufficient ABSENT still has no whole receipt; fabricated receipt still removes C result readback while its immutable fact retains it.
- Wrong schema/exchange strings, zeroed action digest, wrong target/book/scope, absent plan, zeroed Resource SHA (verified unequal to actual bytes), missing readback, zeroed target-state hash and zeroed obligation ID are retained exactly.
- ORIGINAL source, OBSERVED producer/resource/evidence, joint-confirmed policy, PLATFORM execution mode, and unknown source integrity triggers are retained exactly.
- Stale owner/generation, wrong state directory, caller-empty versus actually-pending ledger, uncommitted local intent, and fourth-attempt inputs remain unchanged.
- The old-observation attack still repeats ID `observation-match` and sequence 10 across its two resolutions while only the timestamp advances. The legitimate new-read case retains sequence 11 and unchanged business version `design-effects-0`.
- Terminal-successor/fork/self-cycle chain identities, old legacy-no-intent classification, two-scope unresolved diagnostic rows, and source-only unknown/zero-action coverage remain.

This establishes static retention of the named perturbations and expected layers, not execution of their future rejection/acceptance paths.

## Reproduction and limits

From `D:/1800`:

```powershell
python -B docs/evidence/A03/review/P1-R1/mapping-agent/audit_mapping_profile.py --stage D:/1800/.local/stages/A03-review-P1-R1/ca4fba4f505467228a8164c3999e0cecc54ffc4e --out D:/1800/docs/evidence/A03/review/P1-R1/mapping-agent
python -B docs/evidence/A03/review/P1-R1/mapping-agent/audit_trigger_retention.py --stage D:/1800/.local/stages/A03-review-P1-R1/ca4fba4f505467228a8164c3999e0cecc54ffc4e --out D:/1800/docs/evidence/A03/review/P1-R1/mapping-agent
```

Both completed commands exit 0. `audit-final-stdout.txt` and `trigger-retention-completed-stdout.txt` retain the final successful summaries. The earlier trigger script failed once due to the reviewer's misspelled `previous_resolution_ref` field; that diagnostic is retained in `trigger-retention-stdout.txt`. The next run reported 41/42 only because the zero-source proof had the same actual SHA at a relocated path; the final extractor compares the declared and actual SHA/media/origin of that proof, not its filename. These are reviewer-tool corrections, not candidate defects or recovery failures. No failed diagnostic was deleted.

No author checker or generator was imported/executed by these scripts. No runtime/business/target/database module, network, installation, browser, platform, credential, browser profile, OCR, or model API operation occurred. The candidate-profile JSON here is schema selection metadata only. No P2, implementation, code change, integration, schedule change or I01 release occurred. The exported source and old evidence were read only. All own foreground command sessions completed; no own background process or session remains to release.
