import hashlib
import json
from pathlib import Path

INDEX = Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023/root-content-v1/root-index.json')
EXPECTED = '240db7c66faea2528cacb32b954130df642488c39f9d9d82d9b0c9a4de03d1ae'
PRIVATE = Path('D:/1800/.local/stages/a28-independent-20261023/content-v1-review')
PUBLIC = Path('D:/1800/docs/evidence/A28-independent/content-v1-review')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


index_bytes = INDEX.read_bytes()
assert sha(index_bytes) == EXPECTED
index = json.loads(index_bytes)
assert index['source_manifest_sha256'] == '22b0390244e8063c6ba35764538cc46c09ce56f4d7d772378ae94b4101e899e7'
write(PRIVATE / 'root-index.json', index_bytes)
members = []
seen = set()
for item in index['members']:
    frozen = Path(item['frozen'])
    assert frozen.parent == INDEX.parent
    assert item['source'].casefold() not in seen
    seen.add(item['source'].casefold())
    data = frozen.read_bytes()
    assert len(data) == item['bytes'], frozen
    assert sha(data) == item['sha256'], frozen
    copy = PRIVATE / 'inputs' / frozen.name
    write(copy, data)
    assert copy.read_bytes() == data
    members.append({**item, 'copy': str(copy)})
assert len(members) == 36
result = {'schema': 'A28ContentIndependentIntake/v1', 'status': 'PASS_FROZEN_BYTES_ONLY',
          'root_index': str(INDEX), 'root_index_sha256': EXPECTED,
          'bundle_manifest_sha256': index['source_manifest_sha256'],
          'members_verified': len(members), 'index_copy': str(PRIVATE / 'root-index.json'),
          'members': members, 'activity': {'original_source_paths_read': 0,
              'active_author_reads': 0, 'network': 0, 'browser': 0, 'product_tests': 0}}
data = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
write(PUBLIC / 'intake.json', data)
print(json.dumps({'members_verified': len(members), 'intake_sha256': sha(data)}))
