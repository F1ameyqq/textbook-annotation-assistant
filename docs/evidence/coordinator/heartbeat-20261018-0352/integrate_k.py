"""Integrate one already accepted helper into the released T3 branch."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WT = Path('D:/1800-worktrees/a03-t3')
OUT = Path(__file__).with_name('K-integration.json')
assert not OUT.exists()
record = {'scope': 'One accepted helper only; no root product integration or business run', 'commands': []}
def save():
    OUT.write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
def git(*args):
    entry = {'argv': ['git', '-c', 'core.longpaths=true', *args], 'cwd': str(WT), 'timeout_seconds': 60, 'retries': 0, 'preregistered_at_ns': time.time_ns()}
    record['commands'].append(entry)
    save()
    p = subprocess.Popen(entry['argv'], cwd=WT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    entry.update(pid=p.pid, started_at_ns=time.time_ns())
    save()
    out, err = p.communicate(timeout=60)
    entry.update(exit_code=p.returncode, reaped=True, ended_at_ns=time.time_ns(), stdout_sha256=hashlib.sha256(out).hexdigest(), stdout_bytes=len(out), stderr=err.decode('utf8', 'replace'))
    if len(out) < 4096:
        entry['stdout'] = out.decode('utf8', 'replace')
    save()
    assert p.returncode == 0, entry
    return out

base = '765aef597a93fe36060fce65e17b22fe1c3408b8'
product = '1330047dd29890dea0e433ff01b991f615bf78f4'
source = 'ed90664ab15afd1938725441e2bc86db7884f784'
path = 'examples/a03/T1-capture/capture.py'
expected = '3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
assert git('rev-parse', 'HEAD').decode().strip() == base
assert git('status', '--porcelain') == b''
data = git('cat-file', 'blob', source + ':' + path)
assert hashlib.sha256(data).hexdigest() == expected
compile(data, path, 'exec')
assert not (WT / path).exists()
(WT / path).parent.mkdir(parents=True, exist_ok=True)
(WT / path).write_bytes(data)
git('add', '--', path)
assert git('diff', '--cached', '--name-only').decode().splitlines() == [path]
assert git('cat-file', 'blob', ':' + path) == data
assert git('diff', '--name-only', product, 'HEAD', '--', 'src', 'pyproject.toml', 'requirements.txt', 'requirements-dev.txt', 'setup.cfg', 'setup.py') == b''
git('commit', '-q', '-m', 'Integrate accepted A03 T1 capture helper into T3 baseline')
k = git('rev-parse', 'HEAD').decode().strip()
assert git('status', '--porcelain') == b''
assert git('diff', '--name-only', base, k).decode().splitlines() == [path]
record.update(status='INTEGRATED_DEPENDENCY_ONLY', base_commit=base, product_base=product, source_commit=source, K=k, path=path, sha256=expected, compile_check='PASS_NO_IMPORT', raw_index_equal=True, product_tree_unchanged=True, working_tree_clean=True, root_product_integrated=False, whole_A03_integrated=False, remote_push=False)
save()
print(json.dumps({'K': k, 'status': record['status']}))
