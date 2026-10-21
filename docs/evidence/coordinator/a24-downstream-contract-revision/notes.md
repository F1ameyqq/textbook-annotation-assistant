# A24 downstream contract static preparation

Auxiliary only; fixed final `a1250758d0fc14e8c7d5c827ece2c207a4d99aac`. No actual response/body, user context, active workspace, profile, sidecar, network, product import/run/test was read or used. No new budget or executable candidate. Actual BOOK_TARGET_ABSENT cause remains UNKNOWN.

## Concrete differences to combine into the same A24 revision

1. **Frames:** the request is already the official no-page GET. Official `kS -> Hn(wrapKey=annotations)` returns an object consumed as `.annotations`; it supports both a data array and object data containing `annotations`. Current `decode.inventory` lines 334-339 only accepts `frames.data` as an array. Add a small endpoint-specific decoder with explicit shape evidence, not recursive alias merging. Missing is not empty. Hn also accepts numeric business code 200 and unwrapped bodies; current common `business()` accepts only numeric 0. Those are proven compatibility differences, not proof of the current server shape.
2. **Source/pages:** source path and `annotationType=mr_pre` match. The official frontend reads `source`, `oss_page_url_pattern`, `oss_image_url_pattern`, `total_pages`; it does not require returned `file_id`. Current probe line 1081 rejects missing file_id. If official metadata says OSS with a page pattern, `Mo` does not call the legacy pre_annotation endpoint: it fetches a page JSON URL derived from the current pattern, then synthesizes the page object. This branch is absent from the current probe.
3. **Directory:** GET and `code0/data.directory_data` match. Official `vp -> Eg -> C0` clones the tree and assigns global question order 1..N in DFS array order, overwriting local labels/order in the cloned UI state. Current inventory trusts raw `order_in_level`. Keep `raw_order_in_level`, `raw_label`, and separately `frontend_derived_global_order`/traversal position; disagreement must remain visible. Do not rewrite raw evidence or infer save order. Strict string IDs and boolean flags are narrower than the frontend; no actual type mismatch has been observed.
4. **Source mapping:** OSS resource index is explicitly pageNum-1 (14 -> 13, 173 -> 172). The page JSON contributes blocks; the image URL comes independently from the image template. The synthesized file_id is the caller's ID, not returned server identity. Legacy resource index remains whatever the actual response supplies. Current original byte decoding is still the dimension authority; displayed-canvas and save-page mapping remain unproven.
5. **Evidence whitelist:** current bounded structure omits `annotations`, `source`, the two pattern field names, and `blocks`. Add only presence/type/length for these concrete fields before adapters, so an unsupported response is distinguishable without exposing raw bodies or pattern/query/token values.

## Minimal mutually exclusive page plan

Keep the one source metadata GET. Choose one branch from its valid actual response, never probe both. For legacy, retain page14/page173 GETs. For OSS, replace each page GET budget with exactly one URL derived from that response; no extra GET is added and no fallback follows an attempted request.

Exact template operation is `String(pattern).replace("%d", String(index)).replace("{pageIndex}", String(index))`, replacing the first occurrence of each in that order. Do not guess paths/extensions. Register the exact expanded URL to the original logical page budget before either barrier can send, and disable the alternate legacy URL. Require canonical HTTPS, no userinfo/query/fragment/redirect/path ambiguity, the already allowed main/OSS origin, and approved `/upload_images/46007447/` namespace. An actual pattern outside those constraints remains unsupported and stops; this note does not grant new origins or paths. Validate each image URL independently with the current original-source constraints. Two layers share reservations/cache identity; original image GETs remain one each.

Official page JSON loader returns Axios `.data`: array means blocks, or object `.blocks` array. Official fallback tolerates 403/404/missing by empty blocks, but the bounded collector must distinguish explicit empty from unknown/failed and not manufacture a known-empty result. Do not execute the captured loader. Use the existing guarded transport, no Authorization/cookie export to OSS, and preserve finite facts/hash of the real JSON separately from derived page metadata.

Official `PdfViewerWithDivUnified` returns an absolute `http...` image URL unchanged; relative images are base-path plus token query. The latter is outside present public no-query image authority, so stop instead of appending token or broadening policy. Canvas fits loaded Image width/height; there is no proved metadata dimensions field. Static derivation is not current display or save-page proof.

Full exact URLs can transiently enter Python/native for guards and caches. Do not claim browser-only handling; no account/token/query values may be logged or persisted.

## Evidence

Raw file hashes and all source fragments are in `notes.json`. Offsets below are zero-based UTF-8 bytes in the previously authorized Script SHA `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41` (3065996 bytes).

- Hn_numeric_code_and_wrapKey: offset 1069105, 192 bytes, SHA256 `d112894ccf3bc7bf103b1bfb6549d2ee2142906567516e9c0b9779e5cc3f4bac`.
- directory_GET: offset 1082583, 91 bytes, SHA256 `a4652b00216bb48abbe1b4a624a2a1aa5a474fb4585953bf0035be3f50c3c294`.
- frames_GET_and_unwrap: offset 1078292, 206 bytes, SHA256 `b21799a14eae2087db932580244e206febb805926456e9cbceb6ec3626444f3f`.
- page_number_template_and_page_JSON: offset 1075903, 384 bytes, SHA256 `c8df862c7e73fe6a10c976da449ca3b263a650506d7ad27f317db20b8c1b9d64`.
- source_metadata_GET_and_cache: offset 1076287, 439 bytes, SHA256 `99693bfaa7bb4a8814658cec88b889e2deadb3ade92d1ac325ed8c35c445b2a4`.
- OSS_page_synthesis: offset 1076726, 550 bytes, SHA256 `b87eada935d68158b0f7d1fdacac1409991a3dcefea61660a981c974ef19d927`.
- source_branch_and_legacy_page_GET: offset 1077276, 729 bytes, SHA256 `fd5499ce50fe1c9cc89ace997c7ce6932ddad62958737d7805dd2b24b41948a3`.
- directory_viewer_fetch: offset 2694917, 493 bytes, SHA256 `07adedbbad690793634c6457122bb4e22ed0bc7962d61955dc09719f7808489b`.
- directory_viewer_global_reindex: offset 2681911, 501 bytes, SHA256 `73068ab3cc54ec289a2b8608f58cd7feb1cf6f8e176c3c0df9c9ee488f4baa4d`.
- frames_viewer_consumer: offset 2677743, 112 bytes, SHA256 `03183ac046243fe79ffe8568b11a748e0cdb22f960b0b1771661fdca019e162f`.
- viewer_page_load_call: offset 2712280, 480 bytes, SHA256 `9ae7472f91c56eed78f6f7da6db32f18c76e1ea30bbe24107c75def14f5cd14a`.
- viewer_image_URL: offset 2610785, 240 bytes, SHA256 `fd31863fd09cc03550d947928d7b3c292d5f08184a207852baabb5d2744a7c63`.
- viewer_intrinsic_dimensions: offset 2611377, 303 bytes, SHA256 `bd44a9f6577177d8580b658a8860fdd22204acc93f4d631342c9703bd9909c53`.
- viewer_image_draw: offset 2624920, 1200 bytes, SHA256 `53ea07d4793ea4598d0ff485d9de6f5a08baf983c8911eeda8bf2beaec12773f`.

Static helper event retained: initial wrong source path returned Git128; corrected with fixed-tree inventory. No product/live operation occurred. All auxiliary resources released.
