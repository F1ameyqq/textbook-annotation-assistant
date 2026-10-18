# C01 unknown fixed exchange fixture

Version: c01-fixtures-1; contract 1.0.0-a-proposal; A-side implementation proposal, pending joint confirmation.

The fake save response times out. Results remain UNKNOWN/INDETERMINATE/RECONCILE and replay_allowed=false. Batch pauses in NEEDS_RECONCILIATION with content PENDING, never COMPLETED.

Every image, question, capability, quality assertion, platform identity and receipt is **SYNTHETIC**. No original textbook, login, browser, paid model, OCR, algorithm or platform executor was used. The proposal policy's bounded A05 note describes its policy provenance; it does not turn this fixture into A05 evidence.

The closed exchange includes all nine artifact kinds, three CheckReports (PRE_APPLY/TARGET/POST_APPLY), and both QuestionGraph revisions around a ReviewPatch. Three tiny original P5 grayscale pages are 80 x 100 pixels. Metadata says 250 pages while exactly three are acquired and scoped; metadata never asserts all pages were fetched.

question-alpha spans pages a1/a2, and alpha/child share fragment-shared. question-alpha and question-beta print the same label 1 in different directories. Stable IDs and answer relations prevent matching by the printed label alone. The alpha-answer crop uses processed x=2*x+10, y=2*y+200; inverse (processed-[10,200])/2 returns its original [5,25,65,35] box. These are fixed facts, not an extraction algorithm. The patch changes only alpha's printed label from 1? in revision 1 to 1 in revision 2; all checks/plans use revision 2 and the old revision remains available.

From an installed checkout (any current directory):

```powershell
python <checkout>/examples/contracts/consume.py <copied-fixture-directory>
python <checkout>/examples/contracts/consume.py <copied-fixture-directory> --roundtrip <output-directory>/input.json
```

`consume.py` loads and validates resources with the public contracts API, compares the complete deterministic summary against expected.json, and optionally writes a self-contained copy. All expected values, hashes, ordered lists, decisions and status combinations use exact equality; no numeric tolerances are needed for these fabricated integer/half-open boxes. Rebuild all fixtures with `python examples/contracts/build_fixtures.py`; time, resource bytes and input order are fixed. A failure exits nonzero with the public validation error location.
