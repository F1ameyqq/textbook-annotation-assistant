# Q15 revision 9 current-baseline rebind — independent audit

Date: 2026-10-18  
Auditor: independent quality/regression lane  
Technical verdict: **PASS**  
Release/business verdict: **HOLD** (`transcription_verified=false`, `business_acceptance=false`)

## Scope

This audit covers the regenerated `q15-rebound-b5-generated5` package and the rebind generator that produced it. It verifies current-baseline identity, artifact integrity, revision lineage, preservation of the 14-operation revision-8 prefix, the exact two-operation Q15 delta, historical-to-current source-semantic mapping, strict stale-artifact rejection, independent consumer acceptance, and the two Q15-specific semantic assertions.

The prior pixel/source review and the root 14-stage integration suite were used as explicit dependencies and were not duplicated here.

## Audited identities

- Rebind generator SHA-256: `62685738b8bc9b06fc21379cb6d8c6d1d80fbb0da88a6a61f2de5af8c7dd0829`
- Rebind receipt SHA-256: `1836a25564d29251bf8e25d202fe1e7a31f7d263c7c3a341cc985b28b5b6e033`
- Revision-8 plan file SHA-256: `cbd8d317a2a5aa8b0ca4bd99d3dab9a5834004f5874b826b8bb9941d793a0f0f`
- Revision-9 plan file SHA-256: `761c079ebaf4939b48577284353484c18947f3b942e35a45f703e44a524f104f`
- Revision-9 application file SHA-256: `8a9ead7812268b3931d85505357704e94cfec30d6589774574e73d8cddbcbb12`
- Revision-9 graph file SHA-256: `e6becd4ed62ab7f0df578fd4e437296a8063f124f15e30b6fa631f76df6d9f68`
- Revision-9 check file SHA-256: `4393a92ecf527b4890c62ec650686ad4962acc1bf704a653fa449ec863056460`
- Declared and independently verified production baseline: `b5cc1ea2a0cc1b50b051ffc5ad429e7b473f516a`
- Production module SHA-256 values independently match both the isolated baseline checkout and the current shared checkout:
  - `content_revision.py`: `b24d0532ffabbc0e62a15061ffd394e0e06976217e77857b9555720704914ac5`
  - `content_revision_quality.py`: `368c5ec40b3cb990f2d08f82bc5b385b5b4f8fea1126f9e5124bfac77693acac`

All 15 schema artifacts in the generated package have a valid `content_hash == digest(payload)`.

## Independent results

### Lineage and operations

- The embedded plan lineage is complete and sequential from revision 9 through revision 1. Operation counts are `16, 14, 13, 8, 8, 8, 8, 7, 2` for revisions `9..1`.
- Revision 9 operations 1–14 are byte-equal to the rebound revision-8 operation list.
- Revision 9 operations 15–16 are byte-equal to the frozen Q15 delta. They remain, in order:
  1. `rebuild-page7-q15-left-start-source-region`
  2. `rebuild-page7-q15-right-continuation-source-region`
- Comparing historical revision 8 with rebound revision 8 found exactly 11 changed JSON leaves: two continuity `proposal_id` values and nine occurrences of historical Q9 `fragment_id` values. No kind, operation ID, target answer, replacement, format, span, author, region block, run, note, or ordering field changed.
- After applying the uniquely proven fragment/proposal crosswalk, all 14 historical and rebound operation-binding ledger entries are exactly equal.

### Source-semantic preservation

- All 195 historical base fragments map one-to-one to current-base fragments under the generator's stable source-semantic tuple; there are zero missing and zero ambiguous mappings.
- After that mapping, all 66 historical revision-8 answers are semantically equal to the rebound revision-8 answers. Printed numbers, active text, explanation text, source lines, normalized fragments, regions, content fragments, runs, block IDs, operation IDs, and verification/HOLD flags agree.
- The rebind generator now validates fragment semantics even when an identifier happens to be unchanged. `SELECT_INLINE` candidates are also uniquely rematched by candidate semantics on every rebind instead of trusting an existing ID.
- The receipt's recorded operation crosswalk agrees with the independently derived operation diff.

### Q15 projection and non-regression

- Q15 remains answer `a-17f4ef3ee25046f8e3f583a2` with `printed_number="15"`; the active answer text does not duplicate that printed number.
- Its four materialized blocks remain in left-start then right-continuation order.
- `\frac{1}{4}` occurs exactly once as a run with `format="latex"`; it is not hidden in a plain-text run.
- The current revision-8 to revision-9 comparison preserves all 65 non-Q15 answer semantics and preserves source coverage. Only the intended Q15 content projection is added.
- The dedicated high-level checker accepts the honest plan/graph and rejects both negative controls: duplicated `15.` in active text and demotion of `\frac{1}{4}` from `latex` to `plain`.

### Strict consumers and stale guard

Independent replay against the current shared production modules accepted all four checks:

- revision-8 application: accepted
- revision-8 quality: accepted
- revision-9 application: accepted
- revision-9 quality: accepted

The same current consumer rejects the stale, pre-rebind revision-9 plan/application with `CONTENT_REVISION_DATA_INVALID` and detail `revision plan exact fields, external refs, identity or draft author invalid`. This demonstrates that rebinding did not weaken the producer/external-reference identity guard.

### Root integration dependency

The root integration receipt (SHA-256 `9f1dbb3332aa6673f756b4ecd203ebd6ae5f9d4cee600c6d33c5ab4977424926`) binds the same revision-9 plan, graph, and check references and records four accepted 14-stage runs:

- merged cold: `READY`, 14/14 done, 0 cache hits
- merged warm: `READY`, 14/14 done, 14 cache hits, same final outputs
- restore revision 8: `READY`, 14/14 done
- reapply merged: `READY`, 14/14 done, same final outputs

It also records 34 questions, 66 answers, 137 issues, 19 unassigned source lines, and 32 unmatched answer entities. The issue total is the previous 134 plus the three intended pending-approval risks; the other counts are unchanged.

## Capability boundary and residual note

The generic content-revision consumer intentionally does **not** encode the two Q15-specific rules about printed-number duplication and the explicit LaTeX fraction run. Those are enforced by the plan-specific assertion and must not be described as generic API guarantees.

One non-blocking generator hygiene issue remains: the script creates the output directory before completing input validation, so a failed invocation can leave an empty directory that must be removed or replaced before retrying. This does not affect the successfully generated package or any artifact identity.

## Conclusion

The current-baseline rebound package is technically valid and regression-safe for integration. Its 16 operations preserve the historical source semantics, the Q15 delta is exact, the revision lineage is complete, current independent consumers accept it, and stale artifacts remain rejected. Human verification and business acceptance correctly remain on HOLD.

## Evidence paths

- Rebind generator: `C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-content-sol56\work\q15-rebind-b5\work\rebind_q15_revision9.py`
- Generated package: `C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-content-sol56\work\q15-rebound-b5-generated5`
- Root integration receipt: `C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\textbook-annotation-assistant\evaluation\book-46007447-q15-master-integration.json`
- Prior plan audit: `C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\outputs\q15-content-revision-v9-independent-plan-audit.md`
- Prior pixel/source audit: `C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\outputs\q15-answer-draft-v1-independent-source-audit.md`
- Q15-specific assertion: `C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\outputs\q15-v9-high-level-assertions.py`
