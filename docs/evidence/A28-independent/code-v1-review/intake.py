import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023/root-fixed-code-v2')
PRIVATE = Path('D:/1800/.local/stages/a28-independent-20261023/code-v1-review')
PUBLIC = Path('D:/1800/docs/evidence/A28-independent/code-v1-review')
EXPECTED = '02bf8bc293d38a7ffbc0c57499c7196ad95f21ba69d6d4e3c56076d525211758'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


raw = (ROOT / 'root-index.json').read_bytes()
assert sha(raw) == EXPECTED
index = json.loads(raw)
assert index['commit'] == '48cbd114e59713d50438a478174b0b9396eee523'
assert len(index['members']) == 208
write(PRIVATE / 'root-index.json', raw)
members = []
git_count = 0
for item in index['members']:
    frozen = Path(item['root_frozen'])
    assert frozen.parent == ROOT
    data = frozen.read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], frozen.name
    copy = PRIVATE / 'inputs' / frozen.name
    write(copy, data)
    record = {**item, 'copy': str(copy)}
    if item['kind'] == 'git_blob':
        git_sha = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
        assert git_sha == item['git_blob'], item['repository_path']
        relative = Path(item['repository_path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        source = PRIVATE / 'workspace' / relative
        write(source, data)
        record['isolated_source'] = str(source)
        git_count += 1
    members.append(record)
assert git_count == 31
for name, expected in [('fixed-delivery.json', 'dfc14eb0b86bc4a03f0f21e7c784a444d0137b60cf9c104d9cdffcf5d1cbf27f'),
                       ('raw-manifest.json', '67db3aee2ede4ee51dfd04bf70dee0cd094b238b33233025b90ea2c4c01ca52c')]:
    assert sha((PRIVATE / 'inputs' / name).read_bytes()) == expected
result = {'schema': 'A28IndependentCodeIntake/v1', 'status': 'PASS_FROZEN_BYTES_AND_GIT_BLOB_IDENTITIES',
          'commit': index['commit'], 'root_index_sha256': EXPECTED,
          'members_verified': 208, 'git_raw_blobs_verified_and_restored': git_count,
          'workspace': str(PRIVATE / 'workspace'), 'members': members,
          'active_author_workspace_reads': 0}
out = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
write(PUBLIC / 'intake.json', out)
print(json.dumps({'members': 208, 'git_blobs': git_count, 'intake_sha256': sha(out)}))
