# A30 integrated01/02: concentrated production/UI findings

Decision: **REWORK_INTEGRATED_PRODUCTION_AND_FIGURE_REVIEW**. The separate bounded continuation preparation acceptance in PREPARATION-REVIEW.md stands. No need to wait for these production/UI corrections before separately authorized missing-page preparation.

Both fixed revisions are preserved, with02 as current binding. Main reviewer owns this decision; three auxiliary agents performed static reads only of the independent frozen inputs. They did not run tests, products, browsers, OCR or platform operations. Author19/21 results and original accidental12-test collection / fill-envelope failure remain author evidence, not independent reruns or erased history.

## P2 — required figure is ignored during existing-node reuse (independently reproduced)

`src/annotation/customer/legacy_ledger.py:157-162` strips all HTML and whitespace, then accepts text equality without comparing candidate image frames or native image content. `production.py:95-104` persists REUSED_CURRENT_EXISTING before native make_plan's figure guard; `native_delivery.py:25-32` then takes that old record as the delivery target.

A new synthetic independent input has one valid current native question with same question/answer text but no image, and a source-reviewed candidate with an additional required question image frame. `validate_current` accepts the supplied snapshot, and a single real `existing_candidate` call returns the old node despite the missing figure. Expected outcome is HOLD/no automatic reuse until complete graphical content is matched. Fixed result is **FAIL_REUSE_IGNORES_REQUIRED_FIGURE**. The helper exited0 because it successfully recorded this semantic failure; that is not a product PASS. No production, save, browser or network ran. Raw fixture, returned old record and result are under `writer-counterexample/` in the private review directory.

Fix by proving equivalent image source/content and ordering before reuse, or conservatively HOLD candidates containing image frames. Do not merely use the stripped-text result to bypass existing_fill's existing-frame restriction. This is also relevant to differing embedded native images with identical text.

## P2 — late source image can bind a box to the wrong page (static)

`src/annotation/recognition/review_ui.js:435` installs asynchronous image.onload without a request generation or asset identity. A user switching between two source pages can get a late previous-page image drawn over the canvas. Lines443–445 scale the box using that displayed picture but submit `assetSelect.value`, which can now name the other page. Same-size pages can satisfy backend bbox/association checks while carrying the wrong visible source region.

Bind the loaded image and canvas to an exact asset ID and generation, ignore stale callbacks, and prevent submit unless the selected asset matches the loaded picture. Backend checks alone cannot detect this UI mismatch. This finding is static; its dynamic/browser successor is NOT_RUN after the reproduced reuse failure. It does not run during source-only preparation.

## P2 — same-source OCR state is only checked for the current engine (static, upgrade scope)

`src/annotation/customer/source.py:145-154` looks up local recognition by `[book, raw_sha, engine_identity]`. After an engine/package/code identity change, a prior same-source COMPLETE/INTENT/FAILED_NO_RETRY record under another engine can be missed if no historical-recognition record exists. Lines171–174 can then begin a new full-page recognition. Check same-book/source records across engine versions first; resolve existing evidence instead of rerunning.

This does not block the exact frozen current engine with the demonstrated old historical caches and first missing-page scope. It prevents a general claim that all upgrades/failed-recognition resumptions avoid replay. No OCR reproduction was run and no old model budget was used.

## Other bounded observations

Current native27→printed5 mapping is based on the observed candidate source boxes contained in the existing two frames, not image filename numbering or accepted content. Printed5 currently remains NEEDS_REVIEW; a normal customer's content confirmation is still required. Static native-fill code routes overlapping existing nodes to a plan with is_new_question_insertion=false, zero annotation upserts/deletes, original frame reuse and only absent zone submissions. Nonempty different body is rejected; full readback compares preserved node/info/frames/other body, with narrowly bounded timestamp/new-zone-order allowances. No additional concrete duplication/overwrite defect was found in this specific five-false native27 branch. That is static evidence, not a real save acceptance.

Legacy nine-closure migration retains original claims and failure reconciliations. Production blocks unresolved save states and original unclosed book claims before sends. Current successful candidate hash changes require explicit revision reconciliation. Display failure has a local explicit recheck path without rerunning platform saves/export. These paths were read, not exercised again. Generic portable/migrated paths remain outside current-machine acceptance.

After the first new semantic counterexample, further dynamic production, UI, writer, real save/readback/export and display checks are **NOT_RUN**. No extra full-suite retest is warranted; revise the finite shared defects in the same A30 task, retain both candidates and the failure, and send a fixed minimum delta for this same reviewer. Normal human content/structure review remains permitted; full automatic16/16 is not imposed. CUSTOMER_READY=false, all new platform/write activation=false,1800-a PAUSED.
