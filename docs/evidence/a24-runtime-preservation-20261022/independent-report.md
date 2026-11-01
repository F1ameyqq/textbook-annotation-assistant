# A24 runtime raw-preservation V3 independent final review

## Decision

**PASS_OFFLINE_ENGINEERING_INCREMENT_BOUNDED.** The frozen V3 ZIP may be published as a bounded local engineering increment for the reviewed snapshot/request-wrapper and identity-bound raw business-row preservation paths. It is **not** approval for a live save, refresh, reopen, platform upload, or a claim that every export format is losslessly protected.

Historical R1 `ERROR`/`HOLD` records remain unchanged. Actual save, refresh, independent reopen, and platform qualification remain `NOT_RUN` / `NOT_ESTABLISHED`.

## Frozen candidate integrity

- ZIP: `a24-runtime-preservation-v3-final-frozen.zip`
- bytes: `2,030,853`
- SHA256: `3bfdced673694f848fece63383107fc615d4c5bfc7f870addff3996078928f67`
- members: `688`; uncompressed bytes: `9,197,674`
- unsafe member paths: `0`; `ZipFile.testzip()`: `PASS`
- the five files listed in `frozen-source-manifest.json` match their declared byte counts and SHA256 values.

## Independently verified behavior

Code audit and executed tests establish the following within the bounded scope:

- declared response subtrees are replaced by typed masks while wrapper object order, array position, JSON scalar type, additions, deletions, and key order remain observable;
- empty-root, array-index, duplicate/overlapping, filtered-array, and unused multi-request residual bindings reject as `RAW_RESPONSE_RESIDUAL_UNBOUND`;
- every masked projected array row must bind to a stable question/frame/directory identity, while recursive `children_path` remains explicitly unsupported;
- direct-view and projected raw entities preserve old question/frame/directory/content records, including unknown members, key order, and `0` versus `false`;
- an unchanged wrapper plus the legal one-question/six-frame append still passes;
- runner baseline/reconcile comparisons retain strict `json_same` semantics.

Executed against the extracted frozen source with the required bundled Python and `PYTHONDONTWRITEBYTECODE=1`:

- package focused raw-preservation suite: **13 PASS**;
- independent fixed patch expectations: **9 PASS**;
- independent wrapper-append expectation: **1 PASS**;
- independent V3 residual-mask expectations: **5 PASS**;
- schema readiness: **14 PASS**;
- archived target preservation: **8 PASS**;
- historical preservation: **6 PASS / 1 SKIP**;
- scope-boundary evidence: **2 PASS** (these two tests demonstrate a limitation; they are not acceptance passes).

The first execution of the V3 residual suite produced 4/5 because the supposed unbound multi-request fixture actually consumed its only request. The test precondition was corrected by adding a genuinely unused second request; the corrected frozen test then produced 5/5. This was a test-fixture error, not a candidate failure.

## Required publication boundary: complete-export metadata

`decode_complete_export()` retains each complete question row as `raw_record`/`raw_record_json`, including unknown question fields. However, the conditional `A24CompleteExportCodec/v1` metadata row is projected to five declared fields and its full raw row is not included in `raw_business_projection` or `raw_business_residuals`. A post-append change confined to an unknown complete-export metadata field can therefore pass `check_preservation()`.

This is a real, executable scope gap, frozen in `test_complete_export_metadata_scope_boundary.py`. It is not currently an actual-route false pass: the OBSERVED owner authority requires every profile phase to use `A24NaturalExportCodec/v1`, and the natural route still requires evidence-bound qualification that remains `UNBOUND`. Accordingly:

- do not claim lossless preservation for all export formats;
- do not qualify or activate `A24CompleteExportCodec/v1` for a real write until its metadata raw row is preserved or that route is explicitly rejected;
- the approved statement is limited to the verified snapshot/request wrapper and identity-bound raw question/frame/directory/content paths.

## Frozen independent tests

- `test_fixed_patch_expectations.py` — SHA256 `d80b54e78482464558409f847a9176397849a667f551429cb54cc89d5482d307`
- `test_wrapper_append_expectation.py` — SHA256 `884e09450a74ca6a2167a3a9486eefc361cfd9cdf3eb2b578d5f4d8168c2a7fa`
- `test_v3_residual_mask_expectations.py` — SHA256 `5ba54a2aaaa53961f7b32f53f1638107c4cc7efeb79390a16c273039d90e5bcc`
- `test_complete_export_metadata_scope_boundary.py` — SHA256 `213ddf2a325c044ae6e43e983e1a39bfa2f7c0f717e69ec2fb90ba0ecd9a5a32`

No browser, network, website, upload, live save, refresh, reopen, paid call, source edit, or shared-repository commit was performed by this review.
