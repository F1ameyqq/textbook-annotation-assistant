# Offline Usense regression gate

Publication note (2026-10-23): GitHub rejected the workflow addition because the current OAuth credential lacks `workflow` scope. The reviewed configuration is retained as [a non-executable template](ci/offline-usense.yml.example). It is not installed under `.github/workflows`, and no remote CI run is claimed. The local command below is available without that permission.

From a clean checkout, with Python 3.12 on Windows:

```powershell
python -I -S tools/run_offline_ci.py --report offline-ci-report.json
```

No pip install, repository installation, private files, account, Edge, Playwright,
OCR models or credentials are required. The launcher resolves `src` and `tests`
from its own location, so it also works from another current directory. The
interpreter must start directly with `-I -S` to ignore user site packages and
`PYTHONPATH`. The runner refuses an invocation without those flags. It does not
spawn another Python process; each discovery scope uses a separate unittest
loader and results record. All test mocks must clean up their own state.

The gate runs these separate unittest discovery scopes:

| Suite | Discovery | Minimum tests |
| --- | --- | ---: |
| content | `tests/test_usense_live*.py` | 143 |
| runtime | `tests/usense_live/test_*.py` | 51 |
| quality | `tests/quality/test_*.py` | 28 |

The first two scopes reproduce the 194 tests recorded at `ee463c8`. Quality adds
consumer-risk cases for stable identity after reordering, image multiplicity and
cross-zone loss, unresolved intent replay, coherently rehashed bad readback,
missing raw evidence, source-page/crop mismatches, and the launcher's own guards.
Fixtures contain generated text, IDs, bytes and URLs; URLs are never fetched.

Five source-binding negative cases failed against the baseline validators: the
hash membership check allowed two pages to share one source, mixed sources on
one page, or two paths to identical source bytes. The insertion and main-finalize
validators now require one consistent source path/hash for each viewer page and
two distinct sources for pages 10 and 173. This adds no fields or contract version.
It checks provenance consistency; a reviewer and an authoritative source manifest
are still needed to establish the semantic identity of completely relabelled
inputs. No real saved question or historical plan is rewritten by these checks.

The runner installs a Python audit hook before discovery to reject outgoing
connections, DNS, UDP sends, process creation and shell execution. Actual browser
and model imports are blocked; existing fake modules remain usable. Windows
CPython implements `socketpair` using a private loopback connection, which asyncio
needs even with a fake browser. Only the captured standard-library socketpair
function has this exception; ordinary loopback connections remain blocked.
This is an accidental-I/O guard for trusted tests, not a hostile-code sandbox.

The launcher fails on a unittest failure/error, skip,
expected failure or reduced test count. Its JSON report separates each suite and
keeps error details. `--suite content`, `--suite runtime` and `--suite quality`
are available for separate-process diagnosis. Quality guard tests run in a dedicated
discovery directory because audit hooks intentionally last for the interpreter's
whole lifetime; they must not be imported into a shared legacy-suite process.

`.github/workflows/offline-usense.yml` runs exactly the command above on
`windows-latest` with Python 3.12. Checkout credentials are not persisted; workflow
permissions are read-only. The workflow installs no project dependencies and
uploads the JSON report even on failure. GitHub's checkout/setup/upload steps
need GitHub network access; the unit-test interpreter cannot access the platform.

The full historical suite remains a separate diagnostic command:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -v
```

That suite requires `requirements-b.txt` dependencies and contains historical
fixtures/environment gates. It is not silently excluded and claimed green by
this focused CI. Local execution and a checked-in workflow do not establish a
remote Actions run, a real save/readback, OCR accuracy or business acceptance.

On 2026-10-23 the fixed baseline's original 194 focused tests passed. The final
gate ran 222 tests with no failures, errors or skips. A separate full diagnostic
with OpenCV ran 1381 tests (4 failures, 11 errors, 2 skips). Five diagnostic
root-path import errors were checked in a 60-test supplement (one existing formula
fixture binding error, one skip). A six-test environment follow-up resolved three
loopback permission errors, skipped absent optional OCR metadata, and reproduced
two existing synthetic refine assertions. Two CLI failures and two setup errors
also remain in old mathematical-role fixtures. The full historical suite remains
non-green; its results must be reported separately from this 222-test gate.

Earlier launcher experiments that spawned nested interpreters encountered
Windows `WinError 10013` on asyncio's local socketpair. The final command starts
the isolated test interpreter directly, without a second launch layer. Audit
hooks remain active for all three scopes. The Actions job supplies a ten-minute
overall timeout. If the host disallows even CPython's local socketpair, this is
an environment failure and must not be converted into a passing test or skip.
