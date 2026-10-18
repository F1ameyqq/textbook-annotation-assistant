"""Export the fixed delivery as raw Git blobs into a new isolated local repo."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE = Path('D:/1800')
ROOT = Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT = SOURCE / 'docs/evidence/A03/R1/review'
FINAL = '54e86adfaf144093a688b62fe0dad5190ceb2fa6'
CANDIDATE = '6097a06de937fee8876feccedf46920510850b83'
BASE = 'd5f777590e72eb070af0497afdb144d60c61b95d'
CALLS = []

def command(args, cwd=SOURCE, data=None):
    p = subprocess.Popen(args, cwd=cwd, stdin=subprocess.PIPE if data is not None else None,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(data, timeout=60)
    CALLS.append(dict(argv=args, cwd=str(cwd), pid=p.pid, exit_code=p.returncode,
                      waited=True, stderr=stderr.decode('utf-8', 'replace'),
                      stdout_sha256=hashlib.sha256(stdout).hexdigest()))
    if p.returncode:
        raise RuntimeError(CALLS[-1])
    return stdout

def git(args, data=None):
    return command(['git', '-c', 'core.longpaths=true', '-C', str(SOURCE)] + args, data=data)

def main():
    if ROOT.exists():
        assert {p.name for p in ROOT.iterdir()} == {'.git'}, 'Existing execution bytes must never be overwritten'
        assert command(['git', '-C', str(ROOT), 'remote', 'get-url', 'origin']).decode().strip().replace('\\', '/') == str(SOURCE).replace('\\', '/')
    else:
        command(['git', '-c', 'core.longpaths=true', 'clone', '--shared', '--no-checkout',
                 str(SOURCE), str(ROOT)])
    # The following raw files, rather than a checkout, are the execution bytes.
    command(['git', '-C', str(ROOT), 'symbolic-ref', 'HEAD', 'refs/heads/a03-r1-review'], cwd=ROOT)
    command(['git', '-C', str(ROOT), 'update-ref', 'HEAD', FINAL], cwd=ROOT)
    paths = git(['ls-tree', '-r', '--name-only', FINAL]).decode().splitlines()
    selected = [p for p in paths if p.startswith(('src/', 'examples/a03/', 'tests/',
                'docs/evidence/A03/R1/execution/')) or
                (p.startswith('docs/tasks/') and p.endswith('.md') and 'A03' in p) or
                p in ('docs/architecture.md', 'docs/contracts-v1.md', 'pyproject.toml',
                      'requirements.txt', 'AGENTS.md')]
    packed = git(['cat-file', '--batch'], ''.join(FINAL + ':' + p + '\n' for p in selected).encode())
    position = 0
    identities = []
    for path in selected:
        end = packed.index(b'\n', position)
        oid, kind, size = packed[position:end].decode().split()
        assert kind == 'blob'
        start = end + 1
        raw = packed[start:start + int(size)]
        position = start + int(size) + 1
        destination = ROOT / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        identities.append(dict(path=path, blob=oid, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    assert position == len(packed)
    report = dict(final=FINAL, candidate=CANDIDATE, base=BASE, isolation=str(ROOT),
                  exported=identities, command_log=CALLS, python=sys.version,
                  python_executable=sys.executable, old_databases_opened=False)
    (OUT / 'snapshot-index.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(identities), bytes=sum(r['bytes'] for r in identities), isolation=str(ROOT))))

if __name__ == '__main__':
    main()
