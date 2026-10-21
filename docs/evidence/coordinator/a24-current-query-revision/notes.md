# A24 current official book-query preparation

STATIC ONLY. Fixed source 3d53a0b670c04cf84387cd77d69b0a9571741328 plus the original hash-checked A17 Script. No active author/live directory or actual response was read. The reported empty list does not establish a permissions, filter, account or query root cause. This is a same-A24 revision proposal, not a new stage, budget or authorization.

## What a target route actually does

AnnotateUnified's mounted callback reads localStorage key `user`, JSON-parses it, assigns username from `O.username` and role from `O.role || "user"`, then calls `Qse()` without awaiting it (Script byte 2696333/2696535). Qse is called once in this component's initialization; the other identifier occurrence is its definition. With nonempty `query.bookId` and no selected book, Qse sets form.id to the trimmed target, clears title/status/teamName, resets page=1 and awaits loadUserBooks. The known chain vyt -> qze -> n0 issues one books GET. There is no pagination loop or intrinsic duplicate GET in that narrow chain; user search/reset/page controls can call it again. Missing/falsy username causes vyt to return without sending.

This does NOT make target-route navigation fit the existing six-GET plan. Once it finds String(row.id) matching the target, Qse invokes GB. GB may wait for the existing duplicate-check confirmation; if it proceeds, it sets selected row.id/title and invokes an import-ID summary, directory load, default-page loading and OCR-task summary. vue contains two Mo calls for page1; Mo has source/cache branches, so two function calls are not proof of two HTTP requests. Additional endpoint examples proven by wrappers are `/qieti/api/annotate_ocr/structured-upload/import-id/{book_id}` and `/qieti/api/verify_annotation/unified-ocr-task/summary`. Neither is part of the six fixed GETs. Qse finally removes bookId/from through router.replace, not proof of a second Document navigation, but incompatible with treating an unchanged query-bearing URL as the sole final identity string.

The automatic mounted GET can also race the collector's later viewer/session admission: current probe native barrier lines 537-538 rejects business GETs before `auth.authenticated`, while collect admits the viewer at 1059-1060. Do not solve this by weakening the authentication prerequisite or silently permitting the additional GB calls.

## Exact official query contract

Endpoint stays `/qieti/api/claim_book/books`. Current qze object order is:

`page, pageSize, status_list, id, title, team_name, username, role, is_admin`.

- page=1 and pageSize=10 come from vyt's defaults and target reset; id is the fixed target 46007447, the same identity field as row.id.
- title and team_name are empty strings because the target-route setup clears both. They are retained as `title=` and `team_name=`, not omitted. There is no extra team lookup required for this target query. `status` and `teamName` are helper-input names; the request keys are status_list and team_name.
- username is the existing page-local `JSON.parse(localStorage.getItem("user")).username`. The current component does not trim it. No username is read from local configuration or invented.
- role originates in that same existing object. The actual frontend default `O.role || "user"` is documented, not evidence of the current role. Proposed narrow adapter accepts a present, nonempty string role/username from the existing object and stops on missing/non-string context; it does not invent a privileged or fallback identity. It never converts an arbitrary role object/number to an authorized role.
- For status_list, qze compares `String(role || "").trim()` against `admin` and `delivery_admin`. It chooses exactly the public literal eight-state or four-state set recorded in notes.json. With cleared status, it does not take an arbitrary caller-supplied status.
- is_admin is exactly raw `role === "admin"`. In particular delivery_admin does not make is_admin true; whitespace-trimmed equality must not replace that expression. The raw role value is sent unchanged. No role selection or account switching is permitted.

The captured client has no per-client paramsSerializer override. Its serializer preserves scalar insertion order, omits null/undefined values, keeps empty strings and converts booleans to lowercase `true`/`false`. Default encoder z5e is `encodeURIComponent` followed by `%3A -> :`, `%24 -> $`, `%2C -> ,`, `%20 -> +`; literal plus and ampersand are still encoded by encodeURIComponent. Values are encoded exactly once. A plain URLSearchParams implementation differs for some punctuation and should not be called byte-identical without a deliberate canonical comparison. Known key order and empty fields should be fixed in the new plan. The current policy parses unique query keys with keep_blank_values and sorts pairs, so semantic comparison can coexist with one canonical serialized URL.

## Minimal same-A24 implementation plan

Keep the original viewer URL and existing protected-viewer/session admission. Do not click the picker, call Qse/GB, or invoke the client's Axios wrapper: its response interceptor can refresh/retry or redirect on 401. Reuse the current guarded page-fetch path with redirect:error and no retry.

After viewer admission, prepare the one target books query inside the original page/frame using only the existing user object's username/role and the fixed public derivation above. A no-network preparation evaluation can return the relative encoded query URL to the coordinator process solely for ephemeral guard registration. Do not return the user object or token. There is no need for an additional profile request, token injection, generic discovery layer or new browser system.

The URL necessarily contains the account query value. Existing native events and Python route/cache/key code may transiently process it; do not claim all account values remain only in JavaScript. Retain that URL only in process memory. Its exact query values, full URL, derived account fingerprint, headers and arbitrary error text must never enter logs, result files, task documents or Git. Only approved key names, fixed target ID, finite binding/result status and existing safe response projections persist. Existing diagnostic lines 108-138 already omit query values; extend allowed key names only if useful. The token remains page-local: the send evaluation reads the existing access_token solely to populate the Authorization header and never returns or records it.

Register the exact current query once in the existing policy immediately before the first book request. Bind it to original frame/context, fixed method/origin/path/id/page/pageSize, the nine unique keys and typed fixed derivations. Replace the old book key rather than leaving two alternate allowed URLs. Both interceptors and get_once must map this query to the SAME logical BUSINESS_BOOK slot/counter/cache; no new context-parameter budget, no second URL-derived quota and no rebinding after an attempt. Before send, recompute the query from current page context and require exact equality with the prepared query; a changed context stops without sending. Existing duplicate/in-flight/cached-response rules remain, with at most one native send reservation. Unknown callback/HTTP/business failure stops and does not choose the old query as a fallback.

When the response validates the canonical target record, immediately continue the other five already scoped GETs and two registered originals in the same context. Preserve finite response facts before parsing, source/page mapping limits and UNKNOWN write eligibility. A zero target result remains a factual stop, not proof that the query fix failed or that permissions are wrong. Same-A24 first-save preparation can proceed in parallel; source/current-save evidence still determines the concrete write checkpoint.

Only a small related offline delta is needed: exact nine-key generation/encoding/empty/boolean cases; missing or changed page context sends zero; both guards share one BOOK slot including reordered/duplicated query rejection; no account/token leakage in failure reports; success continues existing five GETs/two originals. Do not rerun old suites. Formal candidate acceptance and root's explicit next bounded checkpoint binding still precede any new live operation; the spent A24 attempt is unchanged.

## Evidence and release

notes.json records exact byte offsets, lengths and SHA256 values for small source regions, public status literals, fixed source hashes, and the one read-only excerpt-helper bounds error. No source Script was executed, copied into Git, or reread through a sidecar. No runtime account values were inspected. Auxiliary complete; no retained process.
