"""Export immutable git blobs, without checkout/archive text conversions."""
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')
COMMIT = '5c9285720c8628c5198bedeadfc9f6bc7826a914'
BASE = '39341c98d73c354d639f3beeb55429f55d0e9be5'
STAGE = Path('D:/1800/.local/stages/A02-review/frozen-5c928572')
OUT = Path(__file__).resolve().parent

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

def main():
    STAGE.mkdir(parents=True, exist_ok=False)
    listing = git('ls-tree', '-r', '-z', COMMIT)
    entries = []
    process = subprocess.Popen(['git', '-C', str(REPO), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for record in listing.split(b'\0'):
            if not record:
                continue
            metadata, path_bytes = record.split(b'\t', 1)
            mode, kind, oid = metadata.decode('ascii').split()
            path = path_bytes.decode('utf-8')
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError((mode, kind, path))
            destination = STAGE / path
            destination.resolve().relative_to(STAGE.resolve())
            process.stdin.write(oid.encode('ascii') + b'\n')
            process.stdin.flush()
            header = process.stdout.readline().decode('ascii').split()
            assert header[:2] == [oid, 'blob'], header
            size = int(header[2])
            data = process.stdout.read(size)
            assert process.stdout.read(1) == b'\n'
            assert len(data) == size
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            disk = destination.read_bytes()
            actual_oid = hashlib.sha1(b'blob ' + str(len(disk)).encode('ascii') + b'\0' + disk).hexdigest()
            assert actual_oid == oid, path
            entries.append({'path': path, 'git_blob': oid, 'size': size, 'sha256': hashlib.sha256(disk).hexdigest()})
    finally:
        process.stdin.close()
        process.wait()
    changed = git('diff', '--name-only', BASE, COMMIT).decode('utf-8').splitlines()
    prefixes = ('src/annotation/delivery/planner/', 'src/annotation/delivery/mock/', 'src/annotation/quality/targetcheck/', 'tests/fixtures/a02/', 'examples/a02/', 'docs/evidence/A02/execution/')
    invalid = [p for p in changed if not (p.startswith(prefixes) or p == 'docs/tasks/A02-execution-report.md' or (p.startswith('tests/test_a02') and p.endswith('.py')))]
    ancestors = {}
    for ref in (BASE, '3fe492ce10bf93711ce57d305bc716f8b29345b7', '4e42668ab28eda37a37285285d2f6c595d3bba12'):
        ancestors[ref] = subprocess.run(['git', '-C', str(REPO), 'merge-base', '--is-ancestor', ref, COMMIT]).returncode
    result = {'commit': COMMIT, 'base': BASE, 'stage': str(STAGE), 'files': entries, 'changed_paths': changed, 'out_of_scope': invalid, 'ancestor_exit_codes': ancestors,
              'source_worktree_head': git('rev-parse', 'HEAD').decode().strip(), 'source_worktree_status': git('status', '--short').decode().splitlines()}
    (OUT / 'frozen-export.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert not invalid and not any(ancestors.values())
    print(json.dumps({'commit': COMMIT, 'files_verified': len(entries), 'changed_paths': len(changed), 'out_of_scope': invalid, 'stage': str(STAGE)}))

if __name__ == '__main__':
    main()
