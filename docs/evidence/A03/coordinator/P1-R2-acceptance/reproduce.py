"""Coordinator replay of the frozen independent prefix audit, not runtime tests."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
COMMIT = '940a5de33a24b1a3a9ded6e69ade1dd0609ed83a'
STAGE = ROOT / '.local/stages/A03-review-P1-R2' / COMMIT
SCRIPT = ROOT / 'docs/evidence/A03/review/P1-R2/prefix-agent/audit_prefix.py'
spec = importlib.util.spec_from_file_location('frozen_independent_prefix_audit', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
audit = module.Audit((STAGE / 'examples/a03/P1-R2/data').resolve())
cases = [audit.positive(name) for name in (
    'unattempted-absence-commit', 'partial-with-complete-absent',
    'original-unknown-preserved', 'recovered-report-binding')]
neighbors = audit.neighbors('partial-with-complete-absent', OUT / 'coordinator-mutants.json')
bindings = []
for path, expected in sorted(audit.inputs.items()):
    repo_path = 'examples/a03/P1-R2/data/' + path
    raw = subprocess.check_output(['git', 'cat-file', 'blob', COMMIT + ':' + repo_path], cwd=ROOT, timeout=10)
    assert hashlib.sha256(raw).hexdigest() == expected, repo_path
    assert (audit.base / path).read_bytes() == raw, repo_path
    bindings.append({'path': repo_path, 'bytes': len(raw), 'sha256': expected})
result = {'target_commit': COMMIT, 'result': 'STATIC_DESIGN_REPRODUCTION_PASSED',
    'scope': 'Four positive graphs and three authored plus three independently rechained negatives; no implementation executed',
    'script': str(SCRIPT), 'script_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    'actual_import': module.__file__, 'python': sys.version, 'cwd': str(Path.cwd()),
    'cases': cases, 'neighbors': neighbors, 'git_bound_inputs': bindings,
    'P2_functionality': 'NOT_EXECUTED', 'platform_model_calls': 0}
with (OUT / 'coordinator-check.json').open('x', encoding='utf-8', newline='\n') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'result': result['result'], 'positive_cases': len(cases),
    'authored_negatives': len(neighbors['authored']), 'independent_negatives': len(neighbors['independent_rechain_mutants']),
    'git_bound_inputs': len(bindings), 'runtime_executed': False}))
