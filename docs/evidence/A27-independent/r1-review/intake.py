import hashlib,json
from pathlib import Path
ROOT=Path('D:/1800/.local/stages/a27-batch-stability-20261023/r1-profile-equivalence/root-fixed-delivery')
DEST=Path('D:/1800/.local/stages/a27-independent-20261023/candidate-ebca4c71')
PRIOR=Path('D:/1800/.local/stages/a27-independent-20261023/candidate-23591811')
PUBLIC=Path(__file__).resolve().parent
RECEIPT=Path('D:/1800/docs/evidence/coordinator/a27-r1-fixed-delivery-intake/receipt.json')
sha=lambda b:hashlib.sha256(b).hexdigest()
rb=RECEIPT.read_bytes();receipt=json.loads(rb)
ib=(ROOT/'root-index.json').read_bytes();index=json.loads(ib)
mb=(ROOT/'delivery/manifest.json').read_bytes()
assert sha(ib)==receipt['root_index_sha256']=='540efe4e335bbf18bbe891b96d3a9e3f244c0d6d40f54df2a09c7afc14766ae6'
assert sha(mb)==index['delivery_manifest_sha256']=='1aaa90ff70d6cdb788c174d3dbc683f90310e0e656defed341376335bbc57c50'
assert index['product_commit']==receipt['product_commit']=='ebca4c71a70bdfb5fbccc023d00e0207ae532470'
prior=json.loads((PUBLIC.parent/'fixed-review/raw-manifest.json').read_bytes())
for item in prior['members']:
    for key in ('source','copy'):
        data=Path(item[key]).read_bytes()
        assert (len(data),sha(data))==(item['bytes'],item['sha256']),item[key]
assert not DEST.exists();DEST.mkdir(parents=True)
members=[]
for item in index['members']:
    source=Path(item['root_frozen_path']).resolve();relative=source.relative_to(ROOT.resolve())
    assert relative.parts[0] in ('delivery','product')
    data=source.read_bytes();assert (len(data),sha(data))==(item['bytes'],item['sha256'])
    if 'git_blob' in item: assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob']
    target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(data)
    assert target.read_bytes()==source.read_bytes()==data
    members.append({'source':str(source),'copy':str(target),'bytes':len(data),'sha256':sha(data),'git_blob':item.get('git_blob')})
for source,relative,data in [(ROOT/'root-index.json','root-index.json',ib),(RECEIPT,'root-receipt.json',rb),(ROOT/'delivery/manifest.json','delivery/manifest.json',mb)]:
    target=DEST/relative
    with target.open('xb') as f:f.write(data)
    assert target.read_bytes()==source.read_bytes()==data
    members.append({'source':str(source),'copy':str(target),'bytes':len(data),'sha256':sha(data),'git_blob':None})
newpm=json.loads((DEST/'delivery/product-manifest.json').read_bytes())
oldpm=json.loads((PRIOR/'delivery/product-manifest.json').read_bytes())
old={m['path']:m for m in oldpm['members']};new={m['path']:m for m in newpm['members']}
changed=sorted(p for p in new if p not in old or new[p]['sha256']!=old[p]['sha256'])
assert changed==sorted(receipt['changed_paths'])
assert set(old)<=set(new)
for m in json.loads(mb)['members']:
    data=(DEST/'delivery'/m['path']).read_bytes();assert (len(data),sha(data))==(m['bytes'],m['sha256'])
previous={
 'report.md':PUBLIC.parent/'fixed-review/report.md','result.json':PUBLIC.parent/'fixed-review/result.json',
 'independent_controls_v2.py':PUBLIC.parent/'fixed-review/independent_controls_v2.py',
 'control-artifacts.json':PUBLIC.parent/'fixed-review/control-artifacts.json',
 'profile-alias-witness.json':Path('D:/1800/.local/stages/a27-independent-20261023/test-output/independent-02/profile-alias-witness.json')}
for leaf,path in previous.items():assert (DEST/'delivery/frozen-review-inputs'/leaf).read_bytes()==path.read_bytes()
result={'schema':'A27IndependentR1RawIntake/v1','status':'VERIFIED','members':members,'source_copy_pairs':len(members),
 'delivery_members':72,'raw_product_dependencies':34,'git_blob_identity_verified':34,'changed_paths':changed,
 'prior_product_dependencies_byte_identical':len(old)-sum(p in old for p in changed),'prior_source_copy_pairs_unchanged':len(prior['members']),
 'prior_formal_review_bound_files_identical':len(previous),'author_active_workspace_accessed':False}
(PUBLIC/'raw-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='members'}))
