# I01-A frozen offline composition

Base `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`; workflow
`8b0fe38b3b520f0ff80801c98121acd3f335a1fc`. Product, 30 implementation
pins, schemas/profile/adoption and root dependencies are read-only.

`prepare.py` exports raw Git objects (including shared unmodified src files),
copies the complete A01 book archive and derives independent N/E/U identities
from the accepted 32×32 single-question fixture. Each synthetic input has one
PGM and stem/answer boxes; the inherited policy and raster bytes stay fixed.
The static preflight imports the complete product and checks the composition
without any target, ledger creation or dispatch.

Freeze this directory, `tests/test_i01_preflight.py`, fixtures and preparation
evidence in a candidate commit before `run.py --candidate FULL_SHA`.
The runner exports its own driver/inputs from that candidate's raw blobs and
uses the base raw src view. All output directories are exclusive.

Fixed order: A01 public C01 CLI once, existing A01 consumer once, N, E,
U-execute, U-recover. Each worker has 180 seconds and each parent stage 240.
Internal read 2s, entry 8s, gate 5s, lease 10s/renew 2s and all PRE/currentness
and recovery deadlines are unchanged. N/E each call normal one-action run_plan
once, including its sole report publication. U dispatches once, persists real
UNKNOWN from an unavailable execution observation, releases, then reopens in a
new PID, reconciles fixed call `I01-U-one-MATCH-call` with max_attempts=1 and
publishes one final fresh report. No report is published at the UNKNOWN stage.

E's old candidate is never accepted or dispatched. A single explicit synthetic
operator directory addition causes genuine TARGET_CHANGED at preparation.
The normal APIs release/reclaim owner and generate an entirely new INITIAL,
PRE, TARGET and plan. A fresh target has no terminal baseline; drift-hold
detection would return NO_TERMINAL_BASELINE (holds.py), so no hold is invented.
Release/reclaim advances real owner/history, and does not erase PRE budgets,
old plans or refusal evidence. No old proof is used by the new plan.

Cumulative limits: 3 fresh targets / 3 actual dispatches, one each for N/E/U;
failed creation/dispatch attempts remain consumed. The runner stops on failure.
At most one separately frozen glue correction may continue the same identity
and only failed/unexecuted stages within remaining limits; no automatic retry,
no product/pin fix, no rerun of successful paths, no third candidate.

T1 capture runs after every owned keeper stops/joins and owner releases; only
the retained immutable copies are queried with SQL. Sequential double copies
are not atomic. UNKNOWN and hold facts must remain even when resources release.

A01 public archive consumption and native synthetic composition are separate
boundaries. Neither proves real A01→native, B integration, S01 completeness,
OCR, content verification, real platform recovery, migration or final submission.
Reports retain PENDING / NOT_SUBMITTED and the complete one-question denominator.
Current A public interface usage is documented in the execution report; B
0.4–0.7 acceptance remains PENDING_A and belongs to A06. Zero network, platform,
browser, profile, credentials, model, payment, B messages, push or old DB access.
