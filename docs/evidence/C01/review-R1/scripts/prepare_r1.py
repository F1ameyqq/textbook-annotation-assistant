import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(r'D:\1800')
STAGE = ROOT / '.local/stages/C01-review-R1'
EVIDENCE = ROOT / 'docs/evidence/C01/review-R1'
WORKTREE = Path(r'C:\Users\ASUS\.codex\worktrees\c01-contracts\1800')
HEAD = '4e42668ab28eda37a37285285d2f6c595d3bba12'
CODE = 'cb684f90a2cd7bd7064ce1f30b7d024a49389132'
FIRST = 'b8c4341d277d205dddfae22b26c245b646a1cea2'
BASE = '30bc00cbaa3e40d78fd8d5cac98e81bd354763b2'
STAGE.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(['git', '-C', str(WORKTREE), *args], encoding='utf-8').strip()

assert git('rev-parse', 'HEAD') == HEAD
assert git('status', '--porcelain=v1', '--untracked-files=all') == ''
delta = git('diff', '--name-only', FIRST + '..' + HEAD).splitlines()
expected_delta = {'src/annotation/contracts/validation.py', 'docs/contracts-implementation-v1.md',
                  'tests/test_contracts_platform_refs.py', 'docs/tasks/C01-rework-R1-report.md'}
assert set(delta) == expected_delta, delta
assert git('diff', '--name-only', CODE + '..' + HEAD) == 'docs/tasks/C01-rework-R1-report.md'
protected = [ROOT / 'docs/tasks/C01-review-report.md'] + [p for p in (ROOT / 'docs/evidence/C01/review').rglob('*') if p.is_file()]
baseline = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(protected)}
(EVIDENCE / 'protected-baseline.json').write_text(json.dumps(baseline, indent=2) + '\n', encoding='utf-8')
paths = git('diff', '--name-only', BASE + '..' + HEAD).splitlines()
archive = STAGE / 'delivery.zip'
subprocess.run(['git', '-C', str(WORKTREE), 'archive', '--format=zip', '-o', str(archive), HEAD, '--', *paths], check=True)
tree = STAGE / 'tree'
tree.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    z.extractall(tree)
files = [dict(path=name, bytes=(tree / name).stat().st_size,
              sha256=hashlib.sha256((tree / name).read_bytes()).hexdigest()) for name in paths]
manifest = dict(commit=HEAD, implementation_commit=CODE, rework_base=FIRST, original_base=BASE,
                worktree=str(WORKTREE), branch=git('branch', '--show-current'), worktree_status='',
                delta_paths=delta, files=files, protected_files=len(baseline),
                archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                diff_check=git('diff', '--check', FIRST + '..' + HEAD))
(EVIDENCE / 'delivery-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(commit=HEAD, files=len(files), delta_paths=delta, protected_files=len(baseline), tree=str(tree)), ensure_ascii=False))
