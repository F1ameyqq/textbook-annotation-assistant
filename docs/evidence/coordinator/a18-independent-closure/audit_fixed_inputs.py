"""Read-only byte and targeted source evidence audit; no product execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/1800-worktrees/a18-independent-fixed')
OUT = Path(__file__).resolve().parent
MANIFEST = Path('D:/1800/docs/evidence/coordinator/a18-fixed-delivery/input-raw-manifest.json')
EXPECTED = 'f9c9c1b40f691fceaaf94d5d8f1d0bee9086303dcf4dbb3f3f0f521725c4f2c1'
BASE = ROOT / 'docs/evidence/A18/current-frontend'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def check(items):
    verified = []
    for entry in items:
        path = ROOT / entry['path']
        raw = path.read_bytes()
        assert len(raw) == entry['size'] and sha(raw) == entry['sha256'], entry['path']
        verified.append({'path': entry['path'], 'size': len(raw), 'sha256': sha(raw)})
    return verified


assert sha(MANIFEST.read_bytes()) == EXPECTED
fixed = load(MANIFEST)
assert len(fixed['members']) == 67
verified = check(fixed['members'])
candidate = load(BASE / 'candidate-manifest.json')
assert sha((BASE / 'candidate-manifest.json').read_bytes()) == 'c0f7ea30ee5a3484544524b5e8c609125113a474d901bd24fc600529509ae8e8'
assert len(candidate['members']) == 22
check(candidate['members'])
author = load(BASE / 'sha256-manifest.json')
assert sha((BASE / 'sha256-manifest.json').read_bytes()) == '3d4c3ffe8f1c4a48fec67ff44edb930c1babdab2bcd8a55cbe438cb38c752f49'
assert len(author['members']) == 59
check(author['members'])
evidence = load(BASE / 'script-evidence.json')
script = Path('D:/1800/.local/stages/a17-excluded-static-live/static-assets/1-d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41.bin').read_bytes()
assert len(script) == 3065996 and sha(script) == evidence['source_sha256']
markers = []
for entry in evidence['markers']:
    raw = entry['marker_ascii'].encode('ascii')
    assert len(raw) == entry['marker_bytes'] and sha(raw) == entry['marker_sha256']
    found, start = [], 0
    while True:
        at = script.find(raw, start)
        if at < 0:
            break
        found.append(at)
        start = at + len(raw)
    assert found == entry['byte_offsets_zero_based'], entry['name']
    markers.append({'name': entry['name'], 'offsets': found, 'marker_sha256': sha(raw)})
assert len(markers) == 24
# Verify actual containing function relations, rather than treating vocabulary co-occurrence as schema proof.
relations = [
    ('uEt-default-GET-query-cache-json', b'async function uEt(){const e=await fetch(`${lEt}?t=${Date.now()}`,{cache:"no-store",headers:{"Cache-Control":"no-cache"}});if(!e.ok)throw new Error(`Version check failed with status ${e.status}`);return e.json()}'),
    ('ED-calls-uEt', b'async function ED(e,{initialize:t=!1}={}){return xb||(xb=(async()=>{try{const n=await uEt(),a=n==null?void 0:n.version;'),
    ('fEt-initializes-ED', b'function fEt(e){e&&(ED(e,{initialize:!0}),document.addEventListener('),
    ('mount-before-fEt', b'.mount("#app");fEt(hu)'),
    ('pageNum-and-annotationType-feed-pre_annotation', b'const a=tR(t);let r=[];a!==null&&r.push(`pageNum=${a}`),r.push(`annotationType=${n}`);const o=r.length>0?`?${r.join("&")}`:"",i=await gn.get(`${Hr}/pre_annotation/${e}${o}`);return Hn(i.data)}')
]
relation_results = []
for name, raw in relations:
    at = script.find(raw)
    assert at >= 0, name
    relation_results.append({'relation': name, 'byte_offset': at, 'bytes': len(raw), 'sha256': sha(raw)})

report = {
    'task': 'A18', 'result': 'PASS_FIXED_INPUT_AND_TARGETED_STATIC_SOURCE',
    'fixed_input_manifest_path': str(MANIFEST), 'fixed_input_manifest_sha256': EXPECTED,
    'fixed_raw_members_verified': len(verified), 'candidate_members_verified': 22,
    'author_delivery_members_verified': 59, 'fixed_members': verified,
    'candidate_manifest_sha256': sha((BASE / 'candidate-manifest.json').read_bytes()),
    'author_manifest_sha256': sha((BASE / 'sha256-manifest.json').read_bytes()),
    'source_sha256': sha(script), 'source_bytes': len(script), 'markers_verified': markers,
    'containing_call_relations_verified': relation_results,
    'version_path_offset': 3064125, 'version_fetch_offset': 3064330,
    'version_is_A17_proven_blocked_XHR_path': False, 'A17_blocked_XHR_path': 'UNKNOWN',
    'six_get_disposition': 'Existing exact wrappers/parameters supported by targeted fragments; no newly proven mandatory correction. Actual response schemas and trigger conditions remain UNKNOWN.',
    'source_executed': False, 'source_copied': False, 'source_sidecar_or_profile_read': False,
    'new_network_requests': 0,
    'coordinator_preservation_reference': {
        'basis': 'Fixed dispatch explicitly declares coordinator raw Git verification; not recomputed over all old members by reviewer',
        'baseline_members': 31599, 'allowed_old_product_modifications': 4,
        'old_evidence_members_preserved': 30374, 'deletions': 0,
        'author_preservation_evidence': 'docs/evidence/A18/current-frontend/product-preservation.json'
    },
    'author_fixed_inputs_unchanged_after_delta': True
}
with (OUT / 'fixed-input-source-audit.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({k:report[k] for k in ('result','fixed_raw_members_verified','candidate_members_verified','author_delivery_members_verified','source_sha256','source_bytes','author_fixed_inputs_unchanged_after_delta')}))
