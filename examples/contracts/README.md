# Public C01 consumers and fixed examples

These examples demonstrate the **A-side v1 proposal**, pending joint confirmation. They measure contract compatibility only. All source pixels, quality assertions, capabilities and receipts are fabricated; model calls and spend are zero.

Install the checkout using the root packaging instructions. Python 3.9.13 is supported. From the checkout:

```powershell
python examples/contracts/build_fixtures.py
python examples/contracts/consume.py tests/fixtures/contracts/normal
python examples/contracts/consume.py tests/fixtures/contracts/exception
python examples/contracts/consume.py tests/fixtures/contracts/unknown
python examples/contracts/consume.py tests/fixtures/contracts/choice-assumption
```

`build_fixtures.py` fixes timestamps, byte content, resource hashes, artifact input order and policies. Rebuilding must leave the tracked fixtures byte-for-byte unchanged. It uses the public `seal_artifact`, `seal_policy`, reference helpers, load/validate/write API; it contains no recognition, assembly or executor implementation.

`consume.py <fixture-directory> [--roundtrip <output-directory>/input.json]` can run from another current directory using absolute script/input paths. It reads input.json, verifies assets, compares every field in expected.json against a summary made from public models, and optionally copies assets plus writes/reloads the bundle through the public API. Copy the complete fixture directory; input.json alone intentionally fails resource verification. It never imports a delivery or runtime private module. Destination files are explicitly supplied by the caller; original input.json is preserved.

| Example | Checks / plan / receipt / batch |
|---|---|
| normal | Two planning PASS reports; no options so unresolved W is inapplicable; SIMULATED APPLIED; READY_FOR_SUBMISSION and NOT_SUBMITTED. |
| exception | Ordinary-choice W unresolved plus a whole omitted question; EXCEPTION; BLOCKED plan without actions; NOT_EXECUTED; all four scoped denominator entries retained. |
| unknown | Planning PASS, simulated response timeout, UNKNOWN and RECONCILE with no replay; NEEDS_RECONCILIATION and content PENDING. |
| choice-assumption | Ordinary-choice normal flow only under explicit SYNTHETIC_ASSUMPTION / SEPARATE / SYNTHETIC_ONLY policy and SIMULATED mode. No business policy is resolved by this example. |

All exchanges cover the nine kinds, three check stages, immutable graph baseline/revision 2 around a patch, same printed question 1 in separate directories, cross-page multi-frame content, shared material and original-coordinate crop backprojection. An independent whole-page clue in exception detects content absent from the region candidates rather than relying on a candidate count. Exactly three acquired pages are distinct from metadata_page_count=250.

The normal synthetic final content can be checked because it is explicitly fabricated; that does not change the real proposal policy's OCR UNVERIFIED fact. All real final submissions remain HUMAN_ONLY. Target drift, invalid geometry, digest/reference corruption, invalid completion/replay and patch conflicts are exercised by the separate contract failure tests, rather than by attempting platform effects.
