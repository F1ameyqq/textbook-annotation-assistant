"""Update only producer/profile/adoption identity pins and check new syntax."""
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
    for path in (ROOT / 'examples/a03/P2-R8-R1-producer').glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for path in (ROOT / 'tests').glob('test_a03_r8_r1*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    producer = ROOT / 'src/annotation/quality/synthetic_precheck.py'
    ast.parse(producer.read_text(encoding='utf-8'), filename=str(producer))
    profile_path = PACKAGE / 'data/profile.json'
    adoption_path = PACKAGE / 'data/adoption.json'
    profile = json.loads(profile_path.read_bytes())
    matches = [row for row in profile['implementation_pins'] if row[0] == '@annotation/quality/synthetic_precheck.py']
    if len(matches) != 1:
        raise RuntimeError('producer pin not unique')
    matches[0][1] = sha(producer)
    write(profile_path, profile)
    adoption = json.loads(adoption_path.read_bytes())
    adoption['profile_sha256'] = sha(profile_path)
    write(adoption_path, adoption)
    print(json.dumps({'producer_sha256': sha(producer), 'profile_sha256': sha(profile_path),
        'adoption_sha256': sha(adoption_path), 'schema_changed': False, 'helper_contract_changed': False}))


if __name__ == '__main__':
    main()
