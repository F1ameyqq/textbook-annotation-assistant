import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(r'D:\1800')
STAGE = ROOT / '.local/stages/C01-review-R1'
TREE = STAGE / 'tree'
OUT = STAGE / 'checks'
OUT.mkdir(exist_ok=True)
TMP = STAGE / 'temp'
TMP.mkdir(exist_ok=True)
CWD = STAGE / 'foreign cwd'
CWD.mkdir(exist_ok=True)
env = dict(os.environ, PYTHONPATH=str(TREE / 'src'), PYTHONDONTWRITEBYTECODE='1',
           PYTHONUTF8='1', TEMP=str(TMP), TMP=str(TMP), PIP_DISABLE_PIP_VERSION_CHECK='1')
records = []

def run(name, args, expected=0, environment=None):
    result = subprocess.run(args, cwd=str(CWD), env=environment or env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8', errors='replace')
    (OUT / (name + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (OUT / (name + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    record = dict(name=name, command=args, cwd=str(CWD), returncode=result.returncode,
                  expected_returncode=expected, passed=result.returncode == expected)
    records.append(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
    return result

run('delivered-unittest', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(TREE / 'tests'), '-p', 'test_contracts*.py', '-v'])
run('original-80-matrix', [sys.executable, '-B', str(ROOT / 'docs/evidence/C01/review/scripts/run_independent_review.py'), '--tree', str(TREE), '--output', str(STAGE / 'original-matrix')])
installed = STAGE / 'installed-package'
run('install-package', [sys.executable, '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-build-isolation', '--target', str(installed), str(TREE)])
installed_env = dict(env, PYTHONPATH=str(installed))
run('installed-provenance', [sys.executable, '-B', '-c', 'import annotation.contracts as c, sys, importlib.metadata as m; print(sys.version); print(c.__file__); print({n:m.version(n) for n in ("annotation-contracts","pydantic","setuptools")})'], environment=installed_env)
for name in ('normal', 'exception', 'unknown', 'choice-assumption'):
    copied = STAGE / 'copied-fixtures' / (name + ' copied fixture')
    shutil.copytree(TREE / 'tests/fixtures/contracts' / name, copied, dirs_exist_ok=True)
    run('cli-' + name, [sys.executable, '-B', '-m', 'annotation.contracts', 'validate', str(copied / 'input.json')], environment=installed_env)
    run('consumer-' + name, [sys.executable, '-B', str(TREE / 'examples/contracts/consume.py'), str(copied), '--roundtrip', str(STAGE / 'roundtrips' / name / 'input.json')], environment=installed_env)
for case in ('snapshot_question_missing_directory', 'action_missing_platform_question'):
    original = ROOT / 'docs/evidence/C01/review/counterexamples' / case / 'input.json'
    run('original-cli-' + case, [sys.executable, '-B', '-m', 'annotation.contracts', 'validate', str(original)], expected=1, environment=installed_env)
run('original-public-apis', [sys.executable, '-B', str(STAGE / 'verify_originals.py'), '--tree', str(TREE)])
(OUT / 'commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(checks=len(records), passed=sum(x['passed'] for x in records), failed=sum(not x['passed'] for x in records)), ensure_ascii=False))
sys.exit(1 if any(not x['passed'] for x in records) else 0)
