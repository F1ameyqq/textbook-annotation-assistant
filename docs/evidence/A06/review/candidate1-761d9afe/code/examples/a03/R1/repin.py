"""Update only native implementation pins from the staged raw Git blobs.

Stage implementation changes first. Does not change schemas/oracles or adoption
scope. Run before freeze; never mutate pins in an executing candidate.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'src/annotation/contracts/a03_native/data'


def staged(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', ':' + path])


def main():
    profile = json.loads((DATA / 'profile.json').read_bytes())
    # These unchanged helpers are dependencies of the reusable pure result too.
    # Their actual bytes must participate, rather than relying on file mtimes.
    dependencies = ['contracts/a03_bridge/_json.py', 'contracts/a03_bridge/_resources.py',
        'contracts/a03_bridge/_schema.py', 'contracts/a03_bridge/_errors.py',
        'contracts/models.py', 'contracts/integrity.py', 'contracts/recovery_schema.py']
    existing = {row[0] for row in profile['implementation_pins']}
    profile['implementation_pins'].extend(['@annotation/' + path, ''] for path in dependencies
        if '@annotation/' + path not in existing)
    for row in profile['implementation_pins']:
        path = 'src/' + row[0][1:] if row[0].startswith('@') else 'src/annotation/contracts/a03_native/' + row[0]
        row[1] = hashlib.sha256(staged(path)).hexdigest()
    profile_raw = (json.dumps(profile, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8')
    (DATA / 'profile.json').write_bytes(profile_raw)
    adoption = json.loads((DATA / 'adoption.json').read_bytes())
    adoption['profile_sha256'] = hashlib.sha256(profile_raw).hexdigest()
    (DATA / 'adoption.json').write_bytes((json.dumps(adoption, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8'))


if __name__ == '__main__':
    main()
