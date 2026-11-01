# Viewer 15 standalone question-content v4 — independent audit

Date: 2026-10-17  
Auditor role: independent quality/regression review  
Shared-repository edits by auditor: none

## Verdict

**PASS for the narrowly defined technical claim, provided the caller pins the exact v4 plan file SHA-256.** The producer and independent consumer consistently establish source/projection integrity for the supplied v4 fixture and replay. The result does **not** establish semantic correctness, human transcription approval, answer correctness, graph projection, or business completion.

The authoritative status remains:

- `accepted: true`
- `meaning: SOURCE_AND_PROJECTION_INTEGRITY_ONLY`
- `decision: HOLD`
- `complete: false`
- `human_verification: false`
- `transcription_verified: false`
- `business_acceptance: false`
- `new_model_calls: 0`
- `answer_matching_performed: false`
- `graph_projection_performed: false`

## Audited inputs and code identities

| Item | SHA-256 |
|---|---|
| `question-source-draft-v4.json` | `a7a5c43eb33d2e1378d0f82dc7375603a462dba64a60adbdb06f09a3a2f4ac99` |
| `viewer15-question-draft-v4.zip` | `6c8850dc9fdb9dc220175e6ca48a9de704eed29d5965be1010c0aabacc906019` |
| `src/annotation/recognition/question_content.py` | `694963744bbb9e697f0c9b8fffe63361cddf87b708c2d74f769da9efc0c48437` |
| `src/annotation/recognition/question_content_quality.py` | `bb22eead945be2747dd1c4428ac4eb881092c9da4840ca44c0694458d44c9822` |
| `tools/rebuild_question_content_b.py` | `2fbfb28edd56a3878d265374729a28d367ebe2bee3a2143c5faf47ef587b11a6` |
| `tests/test_question_content.py` | `57f5f84f5fae2035e0916489aefac797b8387bbf011cff6df864ff89a3d42ddc` |

The producer identity embedded in the application matches the audited `question_content.py` hash.

## Source-draft preservation findings

Independent reconstruction of the v4 source draft confirmed:

- payload content hash is correct;
- source image hash and dimensions are correct;
- baseline, evidence, graph, and context references are exact;
- all 62 OCR snapshot/ledger entries are exact;
- all six question raw archives are exact;
- all six question regions are disjoint and contain their original source fragments;
- all 23 block PNG and RGB pixel receipts are exact;
- blocks remain inside their question regions and do not overlap;
- all 12 option units are retained (`Q11`–`Q13`, A–D);
- figure units are retained for Q13 and Q15;
- all seven intentionally null answer blanks remain null;
- all six fraction-component receipts are present and now bind exact run indices;
- the four editorial badges are retained: Q11 `A`, Q14 `NEW`, Q15 `A`, Q16 `A`;
- Q16 task labels `1`, `2`, and `3` are retained;
- the plan decision remains `HOLD`.

Relative to v3, v4 adds exact `run_index` bindings to the six fraction-component entries and adds the full evidence/graph artifact hashes plus the context reference. The question text, mathematical content, 23 blocks, 12 options, seven null blanks, two figures, and three Q16 tasks are unchanged.

## Deterministic replay

The v4 fixture reproduced the checked-in replay application byte-for-structure (same parsed JSON), and the independent audit accepted it with no issues.

| Replay item | Value |
|---|---|
| Application schema | `b-question-content-application-trial/0.1` |
| Application artifact | `question-content-application-56df015d5d0e92c41a141ddb` |
| Application payload hash | `dbe20a6ce34f1cbf050a1d09a9f497f5405d53780fb298e3e72fc2b7058f02db` |
| `application.json` file SHA-256 | `a8c5a6fa7368d4e55e8813a27504db746e4589c5ab8f701ba91620c355ad8ab4` |
| Check content hash | `432cd7bca0582e87ed62723f90d2d01997a7dadacbaecafb1d681cb69cff6fce` |
| `check.json` file SHA-256 | `92800a2560facff88529de8aa2c6858b5e634697a94eb75c55714a674a3884a0` |
| Check result | accepted, zero issues, `SOURCE_AND_PROJECTION_INTEGRITY_ONLY` |

All 23 replayed source crops were retained and matched their recorded receipts.

## Adversarial and regression coverage

The focused command `python -X utf8 -m unittest tests.test_question_content -v` passed **11/11 tests** in 2.998 seconds. No full repository suite was run, as requested.

The successful coverage includes:

- a valid real-page projection;
- proof that the independent auditor does not call the producer;
- external fixed-file SHA rejection of a modified and internally re-signed plan;
- current source-pixel mutation rejection;
- exported-figure content or rescale rejection;
- rejection of a re-signed application that fills a blank, drops a risk, or changes a raw archive;
- structural plan rejection for reversed or duplicate fraction components, including reverse-and-rebind attempts;
- exact base-envelope validation in both producer and independent consumer;
- rejection of unknown or mixed base schemas;
- duplicate-JSON-key rejection;
- binding of the audit to the current application and external plan.

Independent attack probes also confirmed:

- evidence and graph mutations to `kind`, `run_id`, `producer`, or `input_refs` are rejected;
- the exact evidence and graph envelopes are bound through full artifact digests;
- evidence input references must equal `[baseline_ref, context_ref]` exactly;
- graph input references must equal `[evidence_ref]` exactly;
- reordered fraction components and duplicate component IDs are rejected;
- a plan prefixed with a UTF-8 BOM is rejected by both paths (producer: `JSONDecodeError`; consumer: `accepted: false` with the same issue);
- a changed plan cannot pass when the expected v4 SHA remains pinned, even if its internal payload hash is recomputed.

An earlier audit iteration exposed a real envelope-binding weakness: only selected evidence/graph reference fields were effectively bound, allowing envelope metadata changes. The final audited v4 code closes that gap with exact envelope key sets, full evidence/graph digests, exact run bindings, exact input-reference topology, and a context reference derived from the context payload. The final tests and independent probes reject the prior attacks.

## Residual trust boundary

The fixed external plan SHA is a required trust anchor. If a caller deliberately supplies a *different* externally authorized SHA for a modified, internally consistent plan, semantic edits that are not independently derived from pixels—such as removing an editorial badge or changing its text—can still be accepted. This is not a source/projection integrity failure under the stated contract; it is the boundary of that contract.

Operationally, consumers must pin exactly:

`a7a5c43eb33d2e1378d0f82dc7375603a462dba64a60adbdb06f09a3a2f4ac99`

They must not recompute and trust a SHA from an incoming replacement plan. The retained `MODEL_TRANSCRIPTION_UNVERIFIED` risk and `HOLD` status correctly communicate that semantic truth still requires independent human/model verification outside this audit.

## Scope conclusion

The v4 standalone producer/consumer pair is suitable for its declared purpose: preserving and independently checking the exact source-derived question-content projection with no new model call. It is not approval to perform answer matching, graph projection, human sign-off, or downstream business release.
