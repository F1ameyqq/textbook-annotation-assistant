"""Public CLI reproduction, 28-scenario reconciliation, frozen evidence receipts."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];STAGE=Path('D:/1800/.local/stages/A04-review/coordinate-R1');ROOT=STAGE/'frozen input with spaces'
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',TEMP=str(STAGE),TMP=str(STAGE),PYTHONIOENCODING='utf-8')
output=OUT/'public-entry-package'
args=[sys.executable,'-m','annotation.source.usense','offline','--input',str(ROOT/'tests/fixtures/a04/source'),'--output',str(output),'--as-of','2026-10-16T13:00:00+00:00']
p=subprocess.run(args,cwd=str(STAGE),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
(OUT/'reproduction/public-offline-cli.log').write_bytes(p.stdout);assert p.returncode==0
entry=json.loads((output/'evidence/entry-result.json').read_text(encoding='utf-8'))
consumer=[sys.executable,'-c','import sys; from annotation.contracts import load_bundle; b=load_bundle(sys.argv[1]); print("PUBLIC_LOADER_ARTIFACTS="+str(len(b.artifacts)))',str(output/'bundle.json')]
c=subprocess.run(consumer,cwd=str(STAGE),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
(OUT/'reproduction/public-moved-consumer.log').write_bytes(c.stdout);assert c.returncode==0
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(OUT/'reproduction/public-entry.json',{'args':args,'cwd':str(STAGE),'returncode':p.returncode,
 'consumer_args':consumer,'consumer_cwd':str(STAGE),'consumer_returncode':c.returncode,
 'entry':entry,'observation':'Generic offline CLI still emits WAITING_ACCEPTED_COMMIT despite accepted dependency; not a current coordinator blocker'})

ind=json.loads((OUT/'independent/results.json').read_text(encoding='utf-8'))
render=json.loads((OUT/'independent-renderer/result.json').read_text(encoding='utf-8'))
prior=json.loads((OUT.parent/'review-scenarios.json').read_text(encoding='utf-8'))
mapping=[]
for scenario in prior['scenarios']:
    sid=scenario['id'];status='PASS';evidence=[];note=''
    if sid=='P01':evidence=['snapshot-check.json'];note='Exact delta scope and public tree identity; A01 dependency present'
    elif sid.startswith('O'):
        evidence=['independent/results.json','reproduction/public-entry.json'];note='Public source/snapshot, relocated complete package, independent decode and digest checks'
    elif sid.startswith('F'):
        number=int(sid[1:]);rows=[r for r in ind['results'] if r['case'].startswith(sid+'-')]
        if sid=='F14':rows=[r for r in ind['results'] if r['case']=='F12-F14-mutating-routes-before-fetch']
        if sid=='F12':rows=[r for r in ind['results'] if r['case']=='F12-F14-mutating-routes-before-fetch']
        assert rows,sid
        status='REWORK' if any(r['status']=='FAIL' for r in rows) else 'PASS'
        evidence=['independent/results.json'];note='Independent offline cases: '+', '.join(r['case'] for r in rows)
        if number in (12,13,14):evidence.append('independent-renderer/result.json');note+='; real temporary browser to localhost, policy URL facade, no platform network'
        if sid=='F06':note='HTML/404 rejected; 24-byte truncated PNG accepted by parser and public CLI/loader. A04-CR1-01'
        if sid=='F15':note+='; only synthetic marker tested, no real credential value inspected'
    elif sid.startswith('R'):
        status='BLOCKED';evidence=['historical-live-evidence-review.json']
        note='Fresh platform observation not authorized this round; author historical failure not independent current evidence'
        if sid=='R05':evidence+=['independent/results.json','independent-renderer/result.json'];note+='; OFFLINE mapping 13 numeric/binding/domain probes plus 12 new pixel references PASS, cannot replace live R05'
        if sid=='R06':evidence+=['independent-renderer/result.json','reviewer-release.json'];note+='; reviewer local context/server/owned PIDs released; no real profile acquired'
    elif sid=='D01':evidence=['snapshot-check.json','sha256-manifest.json','closure-checks.json'];note='Original D01 scenario means evidence closure; separate project D01 clean installation NOT_TESTED'
    mapping.append({'id':sid,'clauses':scenario['clauses'],'level':scenario['level'],'status':status,
      'evidence_refs':evidence,'detail':note})
assert len(mapping)==28
save(OUT/'scenario-matrix.json',{'target_commit':'a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39',
 'source_preparation':'docs/evidence/A04/review/review-scenarios.json',
 'counts':{s:sum(x['status']==s for x in mapping) for s in ['PASS','REWORK','BLOCKED']},
 'scenarios':mapping,'complete_A04_acceptance':False,'dependency_release':False})

live=[];execroot=ROOT/'docs/evidence/A04/execution/coordinate-R1'
for label in ['live-01','live-02','live-03','transport-diagnostic-01','transport-diagnostic-02']:
    folder=execroot/label
    paths=[p for p in folder.rglob('*.json') if p.name in ('failure.json','diagnostic.json','session-release.json')]
    records=[]
    for path in paths:
        data=path.read_bytes();rel=path.relative_to(ROOT).as_posix()
        records.append({'path_in_frozen_input':rel,'sha256':hashlib.sha256(data).hexdigest(),
                        'data':json.loads(data)})
    assert records,label
    live.append({'attempt':label,'classification':'EXECUTOR_HISTORICAL_NOT_RERUN','records':records,
                 'complete_capture_present':(folder/'capture.json').exists()})
release=json.loads((execroot/'checks/final-profile-release-check.json').read_text(encoding='utf-8'))
save(OUT/'historical-live-evidence-review.json',{'target_commit':'a86eca6ec87ced20dc3a8bcc8f2c87d329e87c39',
 'attempts':live,'executor_final_release':release,'independently_current_profile_inspected':False,
 'meaning':'Exact frozen historical failure/release records only; no permanent-idle claim or live acceptance'})
save(OUT/'reviewer-release.json',{'source':'independent-renderer/result.json',**render['release'],
 'actual_platform_requests':0,'authorized_credentials_read':0,'authorization_profile_lease_acquired':False,
 'mock_session_failures':'F11 uses synthetic helper, synthetic profile leases and mocked driver only',
 'author_renderer_replay':{'mode':'nonpersistent temporary Edge only','MODE':'author-renderer-replay/MODE.json',
  'observation':json.loads((OUT/'author-renderer-replay/MODE.json').read_text(encoding='utf-8'))},
 'claim_limit':'No current real-profile process/lock inspection; only own local test processes observed'})
print(json.dumps({'public_cli_rc':p.returncode,'consumer_rc':c.returncode,'matrix':{s:sum(x['status']==s for x in mapping) for s in ['PASS','REWORK','BLOCKED']},
 'local_renderer':render['status'],'historical_attempts':len(live)}))
