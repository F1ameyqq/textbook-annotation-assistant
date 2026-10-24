# A30 customer delivery 06 — independent finite review

Decision: **REWORK_REQUIRED_FIGURE_CONFIRMATION_BOUNDARY_ONLY**, with **ACCEPTED_OFFLINE_GUI_DEPLOYMENT_WIRING_AND_PARAGRAPH_ASSIGNMENT** retained for the independent paths below. This is separate from the already accepted first-batch product 07 / launch 03. It neither revokes that acceptance nor adds a gate to the four selected text/inline-TeX items.

## Frozen inputs and scope

Product 06 manifest `38e8a4c25ff037b5e7ec19bbd49cad702dbd2dc2b2ba0862531087a2a3771c40` and report `6c749e8510030b87f24d0daa7d95e62a578b5d5599b889e0ea77ff391225abae` were verified and isolated. 233 raw members comprise 216 source files, 15 evidence files and 2 metadata files. Against 05, four files change (customer instructions, review.py, review_ui.js, customer.py), two are added (orphan_groups.py and the deployment settings test), 210 stay identical and none are removed. The exact eight packaging-support members declared by manifest `0a86a26a807ccc52333c890da8c568ed3df402cff91ce27ec230e8160c9a2c35` were separately verified and isolated. No active workspace/profile or author checkout was used.

Root index `6dbc1ded166a12823c56974eeb9c2f9aad28eae8c26848afe12c96ff526568c7` matches all 233 product members. Root receipt `9f592a3a826576f6e0ff44310a5dbd01f1371e74970e2b841eb9e540201a34a5` is retained. Its broader external-reference inventory is root evidence; this review uses the eight exact packaging support files and does not rescan runtime/model installations or run packaging.

## Single actionable finding

**[P2] A required missing figure must remain blocked at confirmation.** `CustomerReviewWorkspace.confirm` rechecks text structure and rich-content syntax, but `FIGURE_OR_FORMULA_REVIEW` is confirmable and the successful branch clears all issues. It does not first require an image-region binding when the question explicitly depends on a figure. A normal confirmation can therefore promote an incomplete question to READY_CUSTOMER_REVIEWED / PREPARED_OFFLINE while it still has zero image frames.

One new synthetic full-Store example confirms this. A new source PNG contains a simple triangle; its candidate says “如图…” and has question/answer text frames but no image frame. The only candidate issue is FIGURE_OR_FORMULA_REVIEW. Calling the actual 06 confirm method once with ordinary source/content confirmations succeeds, leaves zero issues and zero image frames, and marks the candidate READY_CUSTOMER_REVIEWED. Result **FAIL_REQUIRED_FIGURE_PROMOTED_TO_READY**, direct child exit **3**. Seed, request, resulting job, raw stdout/stderr and command receipt are fixed. No old content, actual remaining item, OCR or platform request was replayed.

The unchanged native planner separately rejects its recognized figure-reference patterns without an image frame. Thus this evidence proves premature readiness and a later production obstruction; it does **not** prove an incorrect platform write. No production was attempted. The minimal correction is to retain a concrete missing-figure blocker through normal confirmation until a required source image region is bound, while preserving ordinary confirmation for text and inline formulas. This must remain a normal customer UI action, with no inferred diagram, answer or per-lesson developer JSON. Broader figure detection or multi-region authoring can be reviewed in their own frozen delta; this finding does not demand a new live/model run.

## Independent accepted paths

Six fresh checks passed in one separate synthetic workspace before the figure counterexample. They exercised the actual 06 review class, immutable blobs, SQLite Store, locking, structure recheck and state generation; no downstream persistence/helper stubs were used:

1. Actual state generation separates two orphan paragraphs at an already-owned source line.
2. A group request that supplies only a subset of its original line IDs is rejected without changing the head.
3. One full group assignment persists exactly once, preserving original texts, boxes and refs, leaving the other candidate and unassigned paragraph unchanged, and retaining formula/content review. It does not infer a question number or auto-confirm the answer.
4. A consumed old group cannot be assigned to the second candidate.
5. A stale head is rejected; the durable event inventory contains one CUSTOMER_ASSIGN_SOURCE and zero platform operations.
6. Actual customer-entry dispatch with `--customer-deployment` reaches the same synthetic workspace and passes only transient settings to a substituted GUI surface. Original settings bytes/head remain unchanged; no preparation/production/transport function is invoked by startup. The GUI surface itself was not opened or visually accepted.

Static inspection confirms the GUI sends group ID plus the exact displayed line IDs to the existing assign endpoint, retains the single-line option, and presents source/formula review rather than an inferred answer. Group IDs bind current head, source asset, window, column and original line sequence; title/number/owned-line/gap boundaries are retained. UI click/display behavior has not received a new browser run.

The exact packaging template embeds the retained workspace, checks its database/settings and retained Python/customer entry before launch, and supplies GUI deployment mode without a command subaction. Missing files stop instead of falling back to an empty workspace. The packager verifies declared source bytes, requires a new output directory, excludes private profile/state paths, and references retained runtimes without copying credentials or activating product settings. This is finite static support acceptance: no final package/ZIP was built, no real launcher/GUI was run, and runtime/model contents or cross-machine installation were not revalidated. Final packaging must bind the eventual accepted product manifest and actual delivery evidence; the historical 04 support preflight is not a final product binding.

The author's one settings test and support group's stub-limited check are retained, not rerun or promoted to full-product evidence. All supplied helper-error diagnostics remain unchanged. Product 06 has parent 05 and does not replace first-batch 07; the accepted first-batch scope correction remains separately bound.

## Limits and retained evidence

After the required-figure semantic counterexample, dependent confirm/production checks were stopped and marked NOT_RUN. Separate completed deployment/group checks remain valid. New reviewer real browser/network/OCR/model/platform activity: **0**. The only new job writes are in reviewer-created synthetic workspaces. No active customer job, profile, ledger, authority, automation or coordinator state was changed.

Customer readiness remains false. Actual remaining twelve-item content, required diagrams, final packaging, native delivery and customer end-to-end use are not accepted by this report. First-batch four-item acceptance remains **ACCEPTED_OFFLINE_FIRST_BATCH_LAUNCH_SCOPE_ONLY**, ready for the coordinator's distinct activation. 1800-a remains PAUSED.

Evidence: `D:/1800-private/a30-customer-delivery-independent-20261024-06/`, including full raw input isolation, eight fixed support members, six-check pass result, single-confirm failure result, both command receipts/raw streams, preserved synthetic state and review manifest.
