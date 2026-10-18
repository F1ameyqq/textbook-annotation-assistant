"""Create-only retention of this review; never follows routing junctions into old evidence."""
import hashlib
import json
from pathlib import Path
import re

MAIN=Path('D:/1800')
ROOT=Path('D:/1800-worktrees/a03-r1-final-review-19ab03c8')
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'route-project/docs/evidence/A03/R1/final-correction'
REPORT=MAIN/'docs/tasks/A03-R1-final-delta-review-report.md'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    destination=OUT/'runs';destination.mkdir(exist_ok=False)
    retained=[];excluded=[]
    for file in sorted(SOURCE.rglob('*')):
        if not file.is_file():continue
        rel=file.relative_to(SOURCE)
        if 'runtime-view'in rel.parts:
            excluded.append(str(rel).replace('\\','/'));continue
        raw=file.read_bytes();target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb')as stream:stream.write(raw)
        assert sha(target.read_bytes())==sha(raw)
        retained.append(dict(source=str(file),retained=str(target.relative_to(MAIN)).replace('\\','/'),bytes=len(raw),sha256=sha(raw)))
    missing=[]
    for label,url in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
        if url.startswith(('http:','https:')):continue
        path=(REPORT.parent/url).resolve()
        if path.name=='manifest.json':continue
        if not path.exists():missing.append(dict(label=label,url=url))
    assert not missing,missing
    # All continuation resources were retained by their own authorised delta,
    # while the primary DB already exists as the raw L2 stationary capture.
    continuation=json.loads((OUT/'continuation-files/index.json').read_bytes())
    assert sha((OUT/continuation['current_database_capture']).read_bytes())==continuation['current_database_sha256']
    for row in continuation['new_live_files']:
        raw=(OUT/row['retained']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256']
    archive=dict(retained_files=retained,excluded_reconstructible_raw_view=excluded,
        exact_raw_view_candidate='9992cd8aba10987d25dd0dc0d0874abec02b27ef',
        routing_junctions_traversed_by_archive=False,missing_report_links=missing,
        previous_evidence_copied=False,author_live_followed=False)
    (OUT/'archive-audit.json').write_text(json.dumps(archive,indent=2)+'\n',encoding='utf-8')
    files=sorted([p for p in OUT.rglob('*')if p.is_file()and p.name!='manifest.json']+[REPORT])
    members=[dict(path=str(p.relative_to(MAIN)).replace('\\','/'),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in files]
    manifest=dict(final_delivery='19ab03c849bfab3dcde2dc86be37c59f3add1ebe',frozen_package='9992cd8aba10987d25dd0dc0d0874abec02b27ef',
        product='6097a06de937fee8876feccedf46920510850b83',conclusion='ACCEPTED_FIXED_FINITE_OFFLINE_DELTA',
        members=members,excluded=['manifest self','reconstructible fixed raw-view',
        'previous review/report/captures: exact references only','author source live state: never accessed'],
        new_targets=2,dispatch=3,new_M_L1_G4_legacy_business=0,no_product_or_index_changes=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    assert all(sha((MAIN/r['path']).read_bytes())==r['sha256']for r in members)
    print(json.dumps(dict(status='SEALED',members=len(members),bytes=sum(r['bytes']for r in members),
        report_sha256=sha(REPORT.read_bytes()),manifest_sha256=sha((OUT/'manifest.json').read_bytes()),links='PASS')))

if __name__=='__main__':main()
