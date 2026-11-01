# A24 runtime-preservation V3 public-package consumption review

## Result

**PASS_PUBLIC_PACKAGE_CONSUMPTION_BOUNDED.** The new public ZIP is internally complete and its public one-command replay succeeds exactly as declared. This closes only the bounded synthetic/runtime-package consumption check; it does not qualify a real platform format or authorize platform use.

## Exact package

- path: `handoffs/b/a24/a24-runtime-preservation-v3-20261022.zip`
- bytes: `506,731`
- SHA256: `2f97801dc13bc040b1eefb97b02932c2c7cbfee887297eedf579cd6998c52638`
- `runtime.json` SHA256: `e28545d2bbd23129b00773f8ba5099fe651d6f14d7769b03c0911676c84edfd3`
- members: `128` = `runtime.json` + `115` source members + `12` synthetic test/fixture members
- manifest-declared payload members checked: `127/127`
- hash mismatches / missing / extra / unsafe / duplicate / symlink members: `0 / 0 / 0 / 0 / 0 / 0`

## Actual public replay command

```powershell
python tools/replay_a24_runtime_preservation.py --out <new independent directory>
```

Actual exit: `0`. Receipt result: `PASS_SYNTHETIC_RUNTIME_REGRESSIONS`.

| Suite | Expected | Observed | Exit | Qualified |
|---|---:|---:|---:|---|
| `tests/a24_runtime_raw_preservation` | 13 | 13 | 0 | true |
| `tests/a24_schema_readiness` | 14 | 14 | 0 | true |
| `tests/a24_archived_target_preservation` | 8 | 8 | 0 | true |
| `tests/a24_readonly_trial` | 6 | 6 | 0 | true |
| `tests/independent_runtime_preservation` | 15 | 15 | 0 | true |

Total: **56/56 PASS, 0 FAIL, 0 ERROR, 0 SKIP**. All five suites emitted a plain `OK`; no skipped marker was present. The replay receipt SHA256 is `f7bdf5ba908eb4449a0cde12fb201ff1533e2c457e86937c6030d2fed3e2f1e8`.

## Public-content boundary

The archive contains only the runtime manifest, source tree, and synthetic tests/fixtures. It contains no member with a persisted browser/login-state path and no SQLite/database, HAR, archive-within-archive, browser-image, document, certificate, or private-key extension. The only image-like fixture is a `100x100` PGM whose `10,000` pixels are all value `255`; its associated text and JSON records explicitly mark themselves synthetic/offline.

Source code necessarily contains references to `localStorage`, authorization headers, and credential-field names, and two tests contain explicit `SENTINEL` token strings. These are program/test literals, not captured Cookie/profile/login state or real credential values. No private business original, historical JSONL input, current page image, browser profile, Cookie store, or login-state artifact is present.

## Retained limits

- `evidence_mode`: synthetic
- `platform_calls`: `0`
- `model_calls`: `0`
- `real_platform_format_qualified`: `false`
- `platform_use_allowed`: `false`
- prior `A24CompleteExportCodec/v1` metadata-row preservation limitation remains in force;
- actual save, refresh, independent reopen, business acceptance, and platform qualification remain unestablished.

The shared repository was not edited, committed, or pushed by this review. Only the new quality-owned replay/output directory was written.
