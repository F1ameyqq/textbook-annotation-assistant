# A24 exact fields: auxiliary frozen-script notes

Status: STATIC AUXILIARY ONLY. No formal acceptance, actual payload approval, new stage or live authority.

- The frontend Choice option is `xuanze`; Multiple choice is separately `duoxuan`. No literal Single choice option is declared in these excerpts. All three question-info state fields start empty. A nonblank tishi is required by the ordinary save guard. With explicit xuanze and untouched category/number, the static payload is `{"tishi":"xuanze","tilei":null,"tihao":null}`.
- Declared tilei constants: `changkaoti`, `yicuoti`, `haoti`, `yazhouti`. These are frontend constants, not a verified backend enum. A currently rendered tilei selector and a tihao enum are not established.
- Q / W / A map to `question` / `choice` / `answer`, all `question_level`. Manual new capture defaults content_type to `text`; preannotation image/table types map accordingly. Cropping a JPEG does not itself imply `content_type=image`.
- Annotation order is a tentative frontend order string; top-level and body question_order are null for insertion. Zone image indices restart at zero. Current legal append order and actual page mapping remain unknown.
- The save wrapper accepts numeric code 0 or 200 and unwraps data; nonnumeric-code objects pass through. The caller uses parsed question_order or a local fallback. It consumes append_at_global_end and inserted_question_node only for an optional fast path. The success toast precedes awaited refresh work; neither toast nor fallback proves a save receipt.
- Signature fields consumed: `accessid`, `host`, `policy`, `signature`, `dir`, optional `securityToken`, and `expire`. Expire is multiplied by 1000, with a 300000 ms cache margin.
- Multipart fields, in order: `key`, `policy`, `OSSAccessKeyId`, `success_action_status=200`, `signature`, `Content-Type=image/jpeg`, optional `x-oss-security-token`, `file`. Upload checks response.ok and returns a locally assembled URL; no receipt body/hash is parsed here.
- Existing static signature retry, upload-403 retry, and Axios 401 refresh/resend paths are documented, not authorized.

All complete findings and exact source excerpts are in notes.json. Each evidence slice is strictly decoded UTF-8 and bound to its byte offset, byte length and SHA256.

## Preserved auxiliary failure

One read-only exploratory end-anchor locator exited 1 with `ValueError: F19`; it produced no files and performed no product or real action. Its original error is retained in notes.json. That entry was not rerun; subsequent new static extraction used known fixed offsets and a different historical-field fragment.

## Source identities

- D:/1800/.local/stages/a17-excluded-static-live/static-assets/1-d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41.bin
  SHA256: `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`; bytes: 3065996
- D:/1800/docs/evidence/coordinator/a24-first-save-request-plan/notes.json
  SHA256: `cc89d0866488a880d616cce3bbb2fe170dcf005c3e146d601b43eecc752a6286`; bytes: 15249
- D:/1800/docs/evidence/coordinator/a24-save-mapping-analysis/notes.json
  SHA256: `dec9362c6107bcdbd0a8a0ef1b3c9c270059eb9d83c9cd41715df44298195e66`; bytes: 28321

## Evidence index

| ID | Fact | Byte offset | Length | SHA256 |
| --- | --- | ---: | ---: | --- |
| F01 | question_info_initial_state_and_declared_options | 2668890 | 1033 | `fee62758912a9d82e4d0a92f33395ea2796e1119eb029a5419df78d3ca85ee51` |
| F02 | rendered_tishi_select_values | 2807760 | 450 | `c55a4621f10a66019027642b89f9ba66ee023f38f34014a06ed73daa66ee292e` |
| F03 | Q_A_W_key_to_annotation_type | 2699943 | 227 | `7b31f6c61bf638dd9c315af661135da8f4569a88bebca0b3ede9b4a0b9fc35b5` |
| F04 | annotation_level_and_order_helper | 2659358 | 580 | `07d7edcb67ebf07cdc302fb1eccbb5fcc9b6066855bff632d5ceb20c414eacf3` |
| F05 | question_choice_capture_content_type | 2727523 | 1402 | `3c4ac366a1c2d7d4fe75d01dda1c46c44f0434a38b054457eab0338b5a3ba9d5` |
| F06 | answer_capture_content_type | 2730261 | 1119 | `7856658dd1de22ad94de1a901a344bbb88effa0407574d8ca12d5ae20106e4dd` |
| F07 | save_validation_tentative_order_zone_indices_and_frame_fields | 2747857 | 1783 | `1351222cb7aba08b97aceb5354fcf5f3f8c9bdfcc11539211c5186edfbc41887` |
| F08 | body_zone_payload_and_empty_zone_deletion | 2751110 | 1061 | `a25631786f69d63d2c3b757c19ce232c2912364e4688a62f7870a6e97d1cffc1` |
| F09 | final_commit_payload | 2752171 | 856 | `ae4d8cb7628b4b8d9bed899b03b1a44aa0277d87d425fe6efffa9bf42e739e86` |
| F10 | response_envelope_unwrap | 1069105 | 192 | `d112894ccf3bc7bf103b1bfb6549d2ee2142906567516e9c0b9779e5cc3f4bac` |
| F11 | commit_post_wrapper | 1083248 | 95 | `34548ec469d6bf7963ab9b34648792b9b8c77727236a3a148d0b8ae28a29fa72` |
| F12 | ordinary_save_success_and_error_paths | 2753238 | 1109 | `61cad4ad4fc59c9776e001eb7a0d7ffcdf7cb91a14375c938c608102f98eff79` |
| F13 | insert_response_consumption_and_refresh_fallbacks | 2682488 | 1803 | `aeceb9bb0ad5bbe96007d99bff00171c0f10e43005031d3902a1d66666d4fbad` |
| F14 | signature_get_wrapper | 1078788 | 136 | `53148066d1e3c883a90f8a097899832f4cedb8e67242fe73bea0b7daaec2371f` |
| F15 | signature_cache_margin_and_retry_delay_constants | 2658364 | 15 | `34649fa795e9ffc0b4d8e7360fa5c82cd0b3d3f26ff770a76e3ee348071faeef` |
| F16 | signature_expire_cache_inflight_and_retry | 2744438 | 497 | `e3601eeb19737604c215ad6a89b025098f93d771df7f28a9184c02c1c66cd836` |
| F17 | multipart_fields_upload_response_and_403_retry | 2744935 | 871 | `ee5a04331837faaa28dc0b66511afa5dc33931eef89eb13092a85ce21aafc4ec` |
| F18 | crop_filename_and_existing_path_branch | 2745806 | 632 | `170f2f58011e8aabdf1462aa711e94c00df39be241e27d25f28e8a4b1b2aef3c` |
| F19 | historical_question_info_load_and_empty_fallback | 2719241 | 235 | `d28a53dadaf1bc2f58b6cee4f24c1ae1ccff890692fa8f265bf87ea8f1e978f4` |
| F20 | axios_business_error_and_401_refresh_resend | 1067893 | 1212 | `dc1eb399d6c90f867d065e757bd7f8100f80fb353231a49fa4340ddce54aab9a` |

## Remaining unknowns

- Backend accepted tishi/tilei/tihao enums, validation and persistence semantics remain unknown; frontend constants are not server schema.
- Current candidate exact title/type/category/number, content_type policy, bbox, page binding, insertion directory and legal order remain unbound.
- Actual signature host/dir/policy/accessid/signature/expire/securityToken and byte/hash-bound upload objects were not observed.
- Actual save receipt schema, authoritative saved order, complete write set and complete old-body preservation remain unproved.
- No full-body completeness guarantee follows from frontend zone arrays, null defaults, receipt fallback or refresh behavior.
- No live activation, current permissions, credential submission, upload, save, retry, OCR or product acceptance is created by these notes.

Released after synchronous static reads and the two authorized notes writes; no retained process, session, handle or helper.
