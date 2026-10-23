import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023/root-fixed-code-r1')
PRIVATE = Path('D:/1800/.local/stages/a28-independent-20261023/code-r1-review')
PUBLIC = Path('D:/1800/docs/evidence/A28-independent/code-r1-review')
EXPECTED = '1036011eff529dba5ff24f5bd556324f825b44677e49a91bf4c568629b2a7ced'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


raw = (ROOT / 'root-index.json').read_bytes()
assert sha(raw) == EXPECTED
index = json.loads(raw)
assert index['commit'] == '4658243f2055c38846713d2292e5f3ac44cc216e'
assert len(index['members']) == 244
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
for name, expected in [('fixed-delivery-r1.json', '98b99b1257bcf5669745a7cc7efe93949dea6930fe5486c85c7bd996464d9825'),
                       ('raw-manifest.json', 'b6e3e02b0ecc846e9df2dae633fc448bec6262afdf9b89003d02c88c820e3134')]:
    assert sha((PRIVATE / 'inputs' / name).read_bytes()) == expected
result = {'schema': 'A28IndependentCodeIntake/v1', 'status': 'PASS_FROZEN_BYTES_AND_GIT_BLOB_IDENTITIES',
          'commit': index['commit'], 'root_index_sha256': EXPECTED,
          'members_verified': 244, 'git_raw_blobs_verified_and_restored': git_count,
          'workspace': str(PRIVATE / 'workspace'), 'members': members,
          'active_author_workspace_reads': 0}
out = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
write(PUBLIC / 'intake.json', out)
print(json.dumps({'members': 244, 'git_blobs': git_count, 'intake_sha256': sha(out)}))
