"""Finalize only this independent evidence directory after captured probe stdout."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def digest(data):
    return hashlib.sha256(data).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

# run-02 executed the same code except the final manifest self-exclusion fix.
# Restore the exact executed script in its run archive and verify its recorded hash.
run02_script = (ROOT / 'probe.py').read_text(encoding='utf-8').replace(
    "manifest = {k: v for k, v in hashes(EVIDENCE).items() if k != 'sha256-manifest.json'}",
    'manifest = hashes(EVIDENCE)')
run02_hash = digest(run02_script.encode('utf-8'))
assert run02_hash == read(ROOT / 'runs/run-02/environment.json')['script_sha256']
(ROOT / 'runs/run-02/probe.py').write_text(run02_script, encoding='utf-8')
environment = read(ROOT / 'environment.json')
assert digest((ROOT / 'probe.py').read_bytes()) == environment['script_sha256']
results = read(ROOT / 'results.json')
receipt = {
    'target_commit': results['target_commit'],
    'final_run': 'run-03',
    'working_directory': 'D:/1800',
    'argv': [environment['python_executable'], '-B'] + environment['command_argv'],
    'observed_exit_code': 0,
    'stdout_path': 'stdout.txt', 'stdout_sha256': digest((ROOT / 'stdout.txt').read_bytes()),
    'case_count': len(results['cases']), 'actual_counts': results['counts'],
    'exit_code_semantics': 'Probe completed and recorded failures; exit 0 is not feature acceptance.',
    'script_hash_matches_final_run': True,
    'run02_archived_script_hash_matches_recorded_run': True,
    'read_only_snapshot_file_count': results['snapshot_file_count'],
    'snapshot_unchanged': results['pristine_frozen_snapshot_unchanged'],
    'old_products_unchanged': results['old_baseline_products_unchanged'],
}
write(ROOT / 'command-receipt.json', receipt)
files = {p.relative_to(ROOT).as_posix(): digest(p.read_bytes())
         for p in sorted(ROOT.rglob('*')) if p.is_file() and p != ROOT / 'sha256-manifest.json'}
write(ROOT / 'sha256-manifest.json', {'files': files})
assert all(digest((ROOT / relative).read_bytes()) == expected for relative, expected in files.items())
print(json.dumps({'files_verified': len(files),
                  'report_sha256': files['REPORT.md'], 'results_sha256': files['results.json'],
                  'manifest_sha256': digest((ROOT / 'sha256-manifest.json').read_bytes())}, indent=2))
