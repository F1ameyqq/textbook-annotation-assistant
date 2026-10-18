"""Static coverage accounting and retain the authorised own continuation delta."""
import hashlib
import json
from pathlib import Path

ROOT=Path('D:/1800-worktrees/a03-r1-final-review-19ab03c8')
PREVIOUS=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=Path(__file__).resolve().parent
AUTHOR=ROOT/'docs/evidence/A03/R1/final-correction'
REVIEW=ROOT/'route-project/docs/evidence/A03/R1/final-correction'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def code(v):return v.get('code')or'/'.join(r['code']for r in v.get('issues',[]))
def main():
    result={}
    for label,root in [('author',AUTHOR),('independent',REVIEW)]:
        g1=load(root/'run/cases/L2/G1.json');assert len(g1)==15
        normal=[]
        for row in g1:
            if 'report'in row:
                assert row['report']['payload']['decision']!='PASS'
                normal.append(dict(key=row['key'],layer='QUALITY_VALUE',code=row['report']['payload']['decision']))
            else:
                c=code(row['result']);layer='STRUCTURE'if c.startswith('SHAPE_')else row['result']['layer']
                normal.append(dict(key=row['key'],layer=layer,code=c))
        assert sum(r['layer']=='STRUCTURE'for r in normal)==5
        l4=load(root/'run/cases/L4/result.json')['controls'];assert len(l4)==4
        assert [code(r['result'])for r in l4]==['RESOLUTION_FORK','EXACT_REF','EXACT_REF','REFERENCE_HASH_MISMATCH']
        g=load(root/'run/cases/G2-G3/result.json');assert len(g['controls'])==11 and g['G2_calls']==7 and g['G3_calls']==4
        assert g['conversion_marker']['status']=='INCOMPLETE'
        marker=root/'run/cases/G2-G3/interrupted-conversion/conversion-incomplete.json'
        assert load(marker)==g['conversion_marker']and not marker.with_name('bundle.json').exists()
        before=(PREVIOUS/'docs/evidence/A03/R1/review/business/cases/M1/captures/after-release-finish/runtime.sqlite3')if label=='independent'else None
        if before is not None:
            assert(root/'run/cases/G2-G3/transaction-copy.sqlite3').read_bytes()==before.read_bytes()
        b=load(root/'run/cases/L2/representations.json')
        assert b['B_consumers_identical']and b['single_B_refs']==b['mixed_B_refs']and b['legacy_generation']==0
        gv=load(root/'run/cases/G5/result.json')
        assert gv['G5_calls']==2 and code(gv['old_report_read'])=='NATIVE_REPORT_READ_NOT_FRESH'
        assert code(gv['foreign_head_different_snapshot'])=='RECOVERY_CHAIN_INVALID'
        result[label]=dict(G1=normal,L4=[dict(key=r['key'],code=code(r['result']),layer=r['layer'])for r in l4],
            G2_G3=[dict(key=r['key'],code=code(r['result'])if'result'in r else'ARCHIVE_READ_NO_NATIVE_AUTHORITY')for r in g['controls']],
            G5=dict(old_report='NATIVE_REPORT_READ_NOT_FRESH',wrong_head='RECOVERY_CHAIN_INVALID',layer='PURE_VALUE'),
            B_representations_identical=True,partial_layer_limits_preserved=True)
    assert result['author']['G1']==result['independent']['G1']
    assert result['author']['L4']==result['independent']['L4']
    # Bind author's already-frozen continuation copies, never its live source.
    index=load(AUTHOR/'continuation-files/index.json')
    snapshot=ROOT/index['current_database'].replace('\\','/')
    assert sha(snapshot.read_bytes())==index['current_database_sha256']
    assert snapshot.read_bytes()==(AUTHOR/'run/cases/L2/captures/after-release/runtime.sqlite3').read_bytes()
    for row in index['new_live_files']:
        raw=(ROOT/row['retained']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256']
    result['author_frozen_continuation']=dict(files=len(index['new_live_files']),database_bound_to_L2_capture=True,author_live_followed=False)
    own=PREVIOUS/'docs/evidence/A03/R1/review';live=own/'business/cases/M2-sufficient/runtime'
    old=load(own/'L1/captures/after-release/SQL.json')['runtime']['tables']
    new=load(REVIEW/'run/cases/L2/captures/after-release/SQL.json')['runtime']['tables']
    oldfiles={r['path']:r for r in old['files']};newfiles={r['path']:r for r in new['files']}
    def actual(path):
        file=Path(path)
        file=file if file.is_absolute()else live/file
        assert file.resolve().is_relative_to(live.resolve())
        return file
    for path,row in oldfiles.items():
        assert path in newfiles and newfiles[path]==row
        assert sha(actual(path).read_bytes())==row['sha']
    retained=[];destination=OUT/'continuation-files';destination.mkdir(exist_ok=False)
    delta=[actual(p)for p in sorted(set(newfiles)-set(oldfiles))]
    delta_expectations={str(actual(p)):newfiles[p]['sha']for p in set(newfiles)-set(oldfiles)}
    oldbooks={b['key']for b in old['books']}
    delta += [live/'gates'/(b['key']+'.lock')for b in new['books']if b['key']not in oldbooks]
    for source in delta:
        assert source.resolve().is_relative_to(live.resolve())
        raw=source.read_bytes();target=destination/source.relative_to(live);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb')as stream:stream.write(raw)
        if str(source)in delta_expectations:assert sha(raw)==delta_expectations[str(source)]
        retained.append(dict(source=str(source),retained=str(target.relative_to(OUT)).replace('\\','/'),bytes=len(raw),sha256=sha(raw)))
    live_db=live/'runtime.sqlite3';capture=REVIEW/'run/cases/L2/captures/after-release/runtime.sqlite3'
    assert live_db.read_bytes()==capture.read_bytes()
    continuation=dict(original_identity=str(live),old_files_unchanged=len(oldfiles),new_live_files=retained,
        current_database_capture='runs/run/cases/L2/captures/after-release/runtime.sqlite3',current_database_sha256=sha(capture.read_bytes()),
        live_source_restored_or_deleted=False,old_report_or_index_modified=False)
    (destination/'index.json').write_text(json.dumps(continuation,indent=2)+'\n',encoding='utf-8')
    result['independent_continuation']=continuation
    (OUT/'coverage-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='FINITE_KEYS_AND_CONTINUATION_VERIFIED',G1=15,L4_gates=4,G2=7,G3=4,G5=2,
        author_continuation_files=len(index['new_live_files']),own_continuation_files=len(retained))))

if __name__=='__main__':main()
