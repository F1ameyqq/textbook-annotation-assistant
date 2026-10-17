"""Update only the projection implementation pin and profile adoption identity."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / 'src/annotation/contracts/a03_native'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def main():
    for path in (ROOT / 'examples/a03/P2-R8-R2-projection').glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for path in (ROOT / 'tests').glob('test_a03_r8_r2*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    source = ROOT / 'src/annotation/runtime/storage/__init__.py'
    ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    profile_path, adoption_path = PACKAGE / 'data/profile.json', PACKAGE / 'data/adoption.json'
    profile = json.loads(profile_path.read_bytes())
    rows = [row for row in profile['implementation_pins'] if row[0] == '@annotation/runtime/storage/__init__.py']
    if len(rows) != 1:
        raise RuntimeError('projection pin must be unique')
    rows[0][1] = sha(source)
    write(profile_path, profile)
    adoption = json.loads(adoption_path.read_bytes())
    adoption['profile_sha256'] = sha(profile_path)
    write(adoption_path, adoption)
    print(json.dumps({'projection_sha256': sha(source), 'profile_sha256': sha(profile_path),
        'adoption_sha256': sha(adoption_path), 'native_commit_reconciliation_changed': False,
        'contracts_schema_producer_changed': False}))


if __name__ == '__main__':
    main()
