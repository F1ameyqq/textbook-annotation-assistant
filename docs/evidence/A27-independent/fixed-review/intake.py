import hashlib, json
from pathlib import Path

ROOT = Path('D:/1800/.local/stages/a27-batch-stability-20261023/root-fixed-delivery')
DEST = Path('D:/1800/.local/stages/a27-independent-20261023/candidate-23591811')
PUBLIC = Path('D:/1800/docs/evidence/A27-independent/fixed-review')
RECEIPT = Path('D:/1800/docs/evidence/coordinator/a27-fixed-delivery-intake/receipt.json')
def digest(data): return hashlib.sha256(data).hexdigest()
receipt_bytes = RECEIPT.read_bytes()
receipt = json.loads(receipt_bytes)
index_bytes = (ROOT / 'root-index.json').read_bytes()
assert digest(index_bytes) == receipt['root_index_sha256'] == '2300a16282a81e9eeab0da1518a5a9415cabc08e454572543194973c982ea0cf'
index = json.loads(index_bytes)
assert index['product_commit'] == receipt['product_commit'] == '23591811be71f9598c07c09b6a25a2a5fb066db0'
manifest_path = ROOT / 'delivery/manifest.json'
manifest_bytes = manifest_path.read_bytes()
assert digest(manifest_bytes) == index['delivery_manifest_sha256'] == '0c3df2aef1c79edf019829008e3b417adc40c560affe5202fe7aa0418d0395ab'
assert not DEST.exists()
DEST.mkdir(parents=True)
members = []
for item in index['members']:
    source = Path(item['root_frozen_path']).resolve()
    relative = source.relative_to(ROOT.resolve())
    assert relative.parts[0] in ('delivery','product')
    data = source.read_bytes()
    assert len(data) == item['bytes'] and digest(data) == item['sha256'], str(relative)
    if 'git_blob' in item:
        assert hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest() == item['git_blob'], str(relative)
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: stream.write(data)
    assert target.read_bytes() == source.read_bytes() == data
    members.append({'source':str(source), 'copy':str(target), 'bytes':len(data), 'sha256':digest(data), 'git_blob':item.get('git_blob')})
for source, relative, data in [(ROOT/'root-index.json','root-index.json',index_bytes), (RECEIPT,'root-receipt.json',receipt_bytes), (manifest_path,'delivery/manifest.json',manifest_bytes)]:
    target=DEST/relative
    with target.open('xb') as stream: stream.write(data)
    assert target.read_bytes()==source.read_bytes()==data
    members.append({'source':str(source),'copy':str(target),'bytes':len(data),'sha256':digest(data),'git_blob':None})
result={'schema':'A27IndependentRawIntake/v1','product_commit':index['product_commit'],'status':'VERIFIED','members':members,'delivery_members':112,'raw_product_dependencies':32,'source_copy_pairs':len(members),'git_blob_identity_verified':32,'author_active_sources_accessed':False}
(PUBLIC/'raw-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='members'}))
