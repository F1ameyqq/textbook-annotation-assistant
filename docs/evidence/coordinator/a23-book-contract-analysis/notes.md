# A23 book identity: fixed-source auxiliary preparation

Status: STATIC_PREPARATION_ONLY. Not formal acceptance, not a new candidate or live authorization. Actual author output was still sealing when assigned and has NOT been read.

Fixed source: 3e5d99f3a740f44cb0f4d09fe37ceb0a34ce4382. No product execution/import/test, browser, network, profile/config/credentials or actual live-output access.

## Exact failure branches

`src/annotation/source/usense/current_readonly/decode.py:147-164` contains the only raising site found under fixed `src/` and `tools/` (line 161). Both conditions share BOOK_IDENTITY_REJECTED:

1. No dictionary anywhere below `body.data` has `str(dictionary.id) == "46007447"`.
2. More than one matching dictionary is found and its projection differs from the first. Projection keys are exactly `id`, `title`, `status`, `question_count`, `page_count`, `updated_at`, retaining only present keys.

Identical projected duplicates pass. Missing versus present projected keys differ. Numeric versus string IDs both match after `str()`, but the retained projections can differ. Extra fields outside that whitelist do not affect duplicate comparison. Recursion stops descending into a dictionary whose own ID matches. Only `id` is recognized; aliases such as `book_id`/`file_id` are not interpreted. None of these mechanisms proves the actual cause.

A missing or empty/non-string title has a different direct branch, BOOK_TITLE_MISSING, after the two conditions above. HTTP 401/403 or business code 401/403 stops as LOGIN_REQUIRED before this parser; other HTTP/envelope failures stop as BUSINESS_READ_FAILED (`decode.py:130-136`). The parser is reached only after HTTP 200 and an integer business `code == 0` have passed the fixed code, assuming the reported error originated at this call.

## Request and expected schema evidence

`policy.py:8-14` fixes the book read to `/qieti/api/claim_book/books` with parameter keys `page`, `pageSize`, `id`; values are one fixed page, size 10 and the fixed target ID. This is a list endpoint, not a proven single-record contract. The current parser allows any nested dictionary/list within `data`; it does not identify a canonical `records`/`books` collection or retain pagination semantics.

The previously captured Script was hash checked before reading: SHA256 d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41, 3065996 bytes. Offsets below are zero-based UTF-8 byte offsets; no source code was executed/copied into Git, and no sidecar was read.

- Offset 1071302: `n0(e)` issues `gn.get(`${qi}/books`, {params:e})` and reads `.data`. If `code === 0`, `data` exists and `data.records` is an array, it aliases records to `data.books` and `data.list`. When role/status filters are absent, it additionally maps selected statuses to a claimed status in the client-side `books` projection. This proves a client-supported `data.records` form and fallback use of `data.books`, not the actual A23 response.
- CORRECTED component attribution: offset 2863741 belongs to a subsequent component after `Verify`, NOT `AnnotateUnified`; its `page_size` call must not be used as current viewer evidence. The initial short analysis misattributed that call; the exact AnnotateUnified chain below supersedes it. No real username/value was read or output.
- The shared `n0` wrapper forwards caller parameters. The actual AnnotateUnified component uses `pageSize`/`id`, matching those probe key names; no pagination-name mismatch has been established. A23's direct page fetch does not call `n0`, so `n0`'s client-only status mapping cannot by itself explain duplicate projection conflict in the raw direct response.

Server schema, server filter behavior, canonical record collection, actual returned target count and actual conflicting fields remain UNKNOWN. Schema mismatch, missing/filtered/paginated target, duplicate representation mismatch and a genuine target identity mismatch remain separate hypotheses.

## Finite output and recoverability

`tools/a16_current_state_probe.py:899-927`: GET_JSON returns HTTP status and parsed JSON to Python; get_once either validates cached exact response bytes or issues the single fixed fetch and requires native capture. `capture:623-639` retains business bytes in the in-memory guard cache. The persistent raw file branch at 640-656 is only for static Scripts.

`collect:1002-1012,1044`: the `book` step is marked DONE by `step(get_once)` BEFORE `book_identity` runs. Thus `steps.book == DONE` can coexist with `book_identity_confirmed == false` and BOOK_IDENTITY_REJECTED. It is not proof that book identity passed.

No book schema, match count, branch reason, record projection or book response hash is persisted before line 1044's parser. The result receives `book` only at line 1061 after directory and frames; `response-schemas.json` at line 1065 contains only directory/frames, not book. The catch/final serialization at 1132-1171 preserves finite error code, steps, authentication, audit and releases, but does not serialize guard.cache. `safe_error:79-83` preserves only exception type and the finite code here.

Consequently the fixed collector's normal persisted facts cannot distinguish zero matches from conflicting projections. They can support retrieval-envelope completion and the exact parser stop, not its actual data branch. This is a static statement about the fixed writer; sealed actual delivery has not yet been inspected and must be checked for any independently retained lawful projection before declaring evidence unavailable.

## One minimum next step

After the actual raw delivery is fixed, check its already-retained facts once. If there is no lawful book projection, do not infer the missing response or repeat A23. Make the next necessary change a narrow list-contract adaptation plus a finite pre-parser projection in the existing collector: record envelope/data container types, allowlisted collection names, item count, target-match count and either NO_TARGET or CONFLICTING_TARGET_PROJECTIONS with only conflicting field names. Do not save arbitrary rows, account fields, request values or raw response text.

Select a canonical collection and adjust request parameters only from a proven current interface contract; do not silently accept aliases, conflicting identities or the first available book. Retain exact target ID/title and visible picker cross-checks. If identity passes, immediately continue the already scoped directory/frames/source/two-image work in that same context. This does not require a generic diagnostic system, authentication changes or an extra diagnosis-only round. Any new live budget/scope binding remains the coordinator's explicit stage decision; A23's consumed attempt and original evidence stay unchanged.

## Fixed raw hashes and release

- decode.py: 7f58f972dea9a986d2701851e5fe9afa77fbda3f547120b9ac86ab0be1fbb43c
- policy.py: 5b5d17e0b6a34d73301564450b164057da1577ba6bcbeee9247977cefa552974
- tools/a16_current_state_probe.py: 1e57c2a61caa7cbfd5b8345c6e41275e8b408ad68d5e7b037e7bb51c00d728ca

Auxiliary work complete. No child/background process retained; no live authority created. Root task/coordination/product files unchanged.
## Authorized sealed-result supplement

After the preparation above, the coordinator authorized reading exactly two files from actual final 454c6ff4a89580e6209b4c45fd6bc74a5e603d83: `docs/evidence/A23/session-completion/live-delivery/execution-report.md` and `book-evidence-limits.json`. Those fixed files confirm book response body, safe structure and separate raw HTTP status were not retained; actual container/nesting/ID values and the precise rejection alternative are UNKNOWN. No active directory or private live output was read. The normal-writer evidence limit above is therefore also explicitly acknowledged by the sealed author delivery, pending formal independent actual-result review.

The concrete adaptation target is the known list wrapper, not a replacement identity detector: the existing recursive parser already traverses `data.records` and `data.books`, so merely teaching it nested lists is not a demonstrated fix. A canonical collection adapter could prevent comparing divergent aliases only if their relationship is explicitly supported; it cannot make a missing target present. Preserve absence/conflict stops and capture the small safe structure before parsing. The original fixed query already uses keys supported elsewhere in n0's callers; adding username or expanding pagination is not justified by this failure alone. This preparation grants no extra request or source.
## Exact AnnotateUnified chain: identity field and pagination

This focused chain supersedes any earlier attribution of the later `kn()` call to the current viewer. All offsets are zero-based UTF-8 bytes of the same hash-checked Script.

1. AnnotateUnified begins at 2658385. At 2661068-2661230 it destructures `userBooks:j`, `userBooksPage:ie`, `bookSearchForm:se`, `loadUserBooks:oe` from `vyt({loggedInUsername:_, loggedInUserRole:S, pdfs:b})`.
2. `vyt` at 2639325 initializes page=1 and pageSize=10. Its `loadUserBooks` function calls `qze` with username and role from the existing component state; page/pageSize and trimmed id/title come from its search form. Status and administrator-dependent teamName are also supplied. On code0 it uses exactly `w.data.records || w.data.books || w.data.list || []`; it sets the list and `total`. It does not concatenate or recursively search multiple aliases.
3. `qze` at 1071798 supplies the known `/claim_book/books` wrapper with page, pageSize, status_list, id, title, team_name, username, role and is_admin. Status_list derives from the requested status or the role-dependent fixed set. No current runtime username, role, returned list or permission scope has been read here.
4. `Qse` at 2701955 reads route `query.bookId`, puts it into `se.value.id`, clears other search terms, sets page=1 and awaits `oe()`. It then finds `j.value.find(row => String(row.id) === bookId)`. Failure presents the existing not-found/no-annotation-permission message; the static message does not identify the actual server cause.
5. `GB` at 2706350 receives the selected row and, after its existing duplicate-check confirmation function, assigns `w.value=N.id` and `x.value=N.title`, then passes `N.id` to subsequent selected-book work. The later commit payload source at 2752193 uses `file_id:w.value`. Thus book-list identity is `id`; `file_id` is the downstream API parameter carrying that selected ID, not an alternate list identity key. No `book_id` list alias is established by this chain. For target 46007447, a valid row must therefore match that value in `id` under the proven list selection.

Concrete differences from the probe: page/pageSize names and default size 10 agree. The probe supplies only page/pageSize/id and omits the viewer's username/role/status_list/team/search context. The viewer chooses a single records/books/list branch; the probe traverses all data descendants and rejects any differing projection of the target. These are verified source differences, not proof of which one caused A23.

For the concentrated successor, retain the chosen-list identity contract and make any additional current-user/filter parameters explicit in its bounded request plan; do not add unbounded pagination or accept file_id/book_id as identity aliases. Preserve one safe observed response-shape projection before parsing. Continue the same scoped source-read sequence immediately on proven target match, while absence or conflict remains a real stop. No separate generic diagnostic stage is needed.