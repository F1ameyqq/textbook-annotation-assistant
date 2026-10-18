# R12-R1 bounded first-run driver

Run from an exact frozen candidate checkout with the existing compatible Python environment. No installation or platform access is used.

```powershell
$env:PYTHONPATH = "$((Get-Location).Path)/src;$((Get-Location).Path)/examples/a03/P2-R12-R1-unknown-projection"
$env:PYTHONDONTWRITEBYTECODE = '1'
python -X utf8 -B examples/a03/P2-R12-R1-unknown-projection/run.py --output docs/evidence/A03/execution/P2-R12-R1-unknown-projection/validation/independent-01
```

`run.py` creates a new output directory, runs L1 then U1--U5 once, and stops on the first failure. It never overwrites or retries. Parent watchdog is 90 seconds per scene, business children 45 seconds. Native recovery retains the original 2 second observer budget and one attempt. Author and independent runs need separate fresh directories.

`prepare_static.py --create-fixture` was used only before freezing to build the unexecuted singleton legacy fixture through the public explicit converter. Its output is already frozen; do not regenerate inputs for validation. `archive.py` performs static Git provenance and sealing only. The passive `sitecustomize.py` records actual Python import paths at normal exit without changing business behavior.

At each required stage, `captures` retains both actual SQLite binary copies and capture records. SQL reads only those immutable copies. Copies are sequential, and keeper/writer state is recorded per file; they are not cross-database atomic snapshots. Native explicit report publication is outside this validation. Field reset remains `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`.
