"""File-only seal/check after the bounded stop. Does not import product code."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-native-bridge'
BASE = '8ad45dd07214ae406a3fab28d76a4b5abd6eef03'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT, input=data)


def paths():
    result = set(git('diff', '--name-only', BASE).decode().splitlines())
    for directory in ('src/annotation/contracts/a03_native', 'examples/a03/P2-R8-native-bridge',
                      'tests/fixtures/a03/P2-R8-native-bridge', 'docs/evidence/A03/execution/P2-R8-native-bridge'):
        result.update(path.relative_to(ROOT).as_posix() for path in (ROOT / directory).rglob('*') if path.is_file())
    result.add('docs/tasks/A03-P2-R8-native-bridge-delivery.md')
    result.discard('docs/evidence/A03/execution/P2-R8-native-bridge/manifest.json')
    return sorted(result)


def inspect_files():
    report = ROOT / 'docs/tasks/A03-P2-R8-native-bridge-delivery.md'
    links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', report.read_text(encoding='utf-8'))
    for link in links:
        if not (report.parent / link.split('#', 1)[0]).resolve().exists():
            raise RuntimeError('broken delivery link: ' + link)
    package = ROOT / 'src/annotation/contracts/a03_native'
    profile = json.loads((package / 'data/profile.json').read_bytes())
    for logical, expected in profile['implementation_pins']:
        path = ROOT / 'src/annotation' / logical[len('@annotation/'):] if logical.startswith('@annotation/') else package / logical
        if sha(path.read_bytes()) != expected:
            raise RuntimeError('frozen implementation bytes changed: ' + logical)
    for logical, expected in profile['schema_pins']:
        if sha((package / 'data' / logical).read_bytes()) != expected:
            raise RuntimeError('schema bytes changed')
    for folder in OUT.rglob('started.json'):
        completed = json.loads(folder.with_name('completed.json').read_bytes())
        if completed.get('alive') is not False:
            raise RuntimeError('owned process incomplete')
    return len(links)


def seal():
    links = inspect_files()
    rows = [{'path': name, 'bytes': (ROOT / name).stat().st_size, 'sha256': sha((ROOT / name).read_bytes())} for name in paths()]
    result = {'base': BASE, 'source_target': '334577d922d224789191a8b4d7127513692ada95',
        'contract_commit': '352b1475fff85a034b839a712ee499ba4c1ec5e6',
        'status': 'REVIEW_N1_BLOCKED', 'scope': 'all R8 new/modified files and raw evidence; exclude this manifest only',
        'delivery_links_checked': links, 'entries': rows}
    with (OUT / 'manifest.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'entries': len(rows), 'bytes': sum(r['bytes'] for r in rows), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes())}))


def check():
    inspect_files()
    manifest = json.loads((OUT / 'manifest.json').read_bytes())
    indexed = {}
    for line in git('ls-files', '--stage').decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, blob, stage = metadata.split()
        if stage != '0':
            raise RuntimeError('unmerged stage')
        indexed[path] = blob
    entries = manifest['entries']
    if set(paths()) != {row['path'] for row in entries}:
        raise RuntimeError('manifest coverage differs')
    request = []
    for row in entries:
        current = (ROOT / row['path']).read_bytes()
        if len(current) != row['bytes'] or sha(current) != row['sha256']:
            raise RuntimeError('frozen file differs: ' + row['path'])
        if row['path'] not in indexed:
            raise RuntimeError('not staged: ' + row['path'])
        request.append(indexed[row['path']])
    stream = git('cat-file', '--batch', data=('\n'.join(request) + '\n').encode())
    offset = 0
    for row in entries:
        end = stream.index(b'\n', offset)
        header = stream[offset:end].decode().split()
        length = int(header[2])
        body = stream[end + 1:end + 1 + length]
        if length != row['bytes'] or sha(body) != row['sha256']:
            raise RuntimeError('raw staged Git blob differs: ' + row['path'])
        offset = end + length + 2
    print(json.dumps({'raw_staged_blobs_verified': len(entries), 'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
        'product_execution': False, 'tests_rerun': False}))


if __name__ == '__main__':
    if sys.argv[1] == 'seal':
        seal()
    elif sys.argv[1] == 'check':
        check()
    else:
        raise SystemExit('unknown file-audit operation')
