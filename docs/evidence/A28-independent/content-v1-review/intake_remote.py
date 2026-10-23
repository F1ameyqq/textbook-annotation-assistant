import hashlib
import json
from pathlib import Path

root = Path('D:/1800/.local/stages/a28-complete-lesson-production-20261023/root-remote-crops-01')
private = Path('D:/1800/.local/stages/a28-independent-20261023/content-v1-review/remote')
public = Path('D:/1800/docs/evidence/A28-independent/content-v1-review')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


raw = (root / 'root-index.json').read_bytes()
index = json.loads(raw)
assert len(index['members']) == 47
assert index['members'][0]['sha256'] == 'a08c9ff26f7c392ac48decdb2e77c3b1d217eb0aa55240acb72a85e493f64cad'
write(private / 'root-index.json', raw)
members = []
for entry in index['members']:
    frozen = Path(entry['frozen'])
    assert frozen.parent == root
    data = frozen.read_bytes()
    assert len(data) == entry['bytes'] and sha(data) == entry['sha256']
    copy = private / 'inputs' / frozen.name
    write(copy, data)
    assert copy.read_bytes() == data
    members.append({**entry, 'copy': str(copy)})
result = {'schema': 'A28ContentRemoteIndependentIntake/v1',
          'status': 'PASS_FROZEN_BYTES_ONLY', 'root_index_sha256': sha(raw),
          'root_index_copy': str(private / 'root-index.json'),
          'proof_sha256': index['members'][0]['sha256'],
          'members_verified': len(members), 'members': members,
          'new_network_requests': 0}
data = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
write(public / 'remote-intake.json', data)
print(json.dumps({'members': len(members), 'root_index_sha256': sha(raw), 'intake_sha256': sha(data)}))
