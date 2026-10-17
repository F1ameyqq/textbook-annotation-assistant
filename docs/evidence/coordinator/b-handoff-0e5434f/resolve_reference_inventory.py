"""Classify the first audit's mixed B reference inventory without rerunning tests."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ZIP = ROOT / '.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip'

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def walk(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, item in value.items():
            yield from walk(item, pointer + '/' + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, pointer + '/' + str(index))

audit = json.loads((OUT / 'package-audit.json').read_bytes())
with zipfile.ZipFile(ZIP) as outer:
    data = {name: outer.read(name) for name in outer.namelist()}
    documents = {name: json.loads(raw) for name, raw in data.items() if name.endswith('.json')}
    with zipfile.ZipFile(BytesIO(data['inputs/inline-observed.zip'])) as inner:
        inner_json_names = [name for name in inner.namelist() if name.endswith('.json')]
        for name in inner_json_names:
            documents['inputs/inline-observed.zip!' + name] = json.loads(inner.read(name))
    binary_names_not_semantically_inspected = ['inputs/inline-observed.zip!' + name for name in inner.namelist() if name.endswith('.sqlite3')]
by_hash = {}
for name, raw in data.items():
    by_hash.setdefault(sha(raw), []).append(name)
continuation = documents['inputs/receipt-documents/continuation/continuation-evidence.json']['payload']
acquisition_hash = sha(canonical(continuation['acquisition_receipt']))
classified = []
for finding in audit['unresolved_formal_reference_identities']:
    reference = finding['reference']
    record = dict(finding)
    digest = reference.get('sha256', reference.get('crop_sha256', reference.get('content_hash')))
    if digest in by_hash:
        record.update({'classification': 'RESOLVED_AS_RESOURCE_BYTES', 'paths': by_hash[digest],
                       'note': 'B trial input_refs permits resource-shaped references; no A ArtifactRef kind/revision is invented.'})
    elif digest == acquisition_hash and reference.get('artifact_id') == 'anonymous-source-get-resource-173':
        record.update({'classification': 'RESOLVED_AS_EMBEDDED_ACQUISITION_RECEIPT',
                       'path': 'inputs/receipt-documents/continuation/continuation-evidence.json#/payload/acquisition_receipt',
                       'note': 'Digest binds the embedded receipt object; its symbolic ID is not an A artifact envelope.'})
    else:
        candidates = []
        ref_only = 0
        for name, doc in documents.items():
            for pointer, value in walk(doc):
                if value.get('artifact_id') != reference.get('artifact_id'):
                    continue
                if 'payload' in value or len(value) > 3:
                    candidates.append({'path': name + '#' + pointer, 'keys': list(value)})
                else:
                    ref_only += 1
        record.update({'classification': 'UNRESOLVED_HISTORICAL_ARTIFACT_IN_JSON',
                       'matching_envelope_candidates': candidates, 'reference_only_occurrences': ref_only,
                       'note': 'No corresponding envelope in outer or nested JSON. Ask whether this is required input or optional archival lineage; do not fabricate it or declare B internals failed.'})
    classified.append(record)
result = {
    'scope': 'Clarifies mixed reference shapes from package-audit.json; that initial inventory is not a list of seven missing files.',
    'archive_sha256': audit['archive_sha256'], 'outer_json_documents': sum(name.endswith('.json') for name in data),
    'inner_json_documents': len(inner_json_names), 'classified_references': classified,
    'binary_members_not_semantically_inspected': binary_names_not_semantically_inspected,
    'new_model_or_platform_calls': 0, 'A_contract_mapping_confirmed': False,
    'next_dependency': 'A/B agree B trial reference semantics, historical baseline requirement and limited HOLD reader mapping.'
}
with (OUT / 'reference-resolution.json').open('x', encoding='utf-8', newline='\n') as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({'classifications': [x['classification'] for x in classified],
                  'unresolved': [x['reference'] for x in classified if x['classification'].startswith('UNRESOLVED')]}, ensure_ascii=False))
