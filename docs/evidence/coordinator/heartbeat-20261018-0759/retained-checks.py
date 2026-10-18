"""Read retained JSON only; no product imports, SQLite, or business calls."""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'docs/evidence/A03/R1/final-review'
checks=[]
def check(name, value):
    assert value, name
    checks.append(name)
def result(name):
    return json.loads((BASE/'runs/run/cases'/name/'result.json').read_text(encoding='utf-8'))
a=json.loads((BASE/'audit.json').read_text(encoding='utf-8'))['groups']['independent']
l2=result('L2');e=result('L3-execute');r=result('L3-reconcile');s=result('L3-second');g=result('G6-first');h=result('G6-reopen');f=result('F')
check('ten stages once, completed, waited, within 240s',len(a['matrix'])==10 and len({x['phase'] for x in a['matrix']})==10 and all(x['status']=='ENDED' and x['process']['exit_code']==0 and x['process']['waited'] and not x['process']['alive'] and not x['process']['timeout'] and x['process']['elapsed_seconds']<240 for x in a['matrix']))
check('two native targets, three dispatch',sum(x.get('native_targets',0) for x in [l2,e,r,s,g,h,f])==2 and sum(x.get('dispatch',0) for x in [l2,e,r,s,g,h,f])==3)
check('book A pending retained and B independent success',l2['A_before']['pending']==l2['A_after']['pending'] and l2['A_after']['pending_count']==2 and l2['B_status']['pending_count']==0)
check('UNKNOWN to ABSENT to fresh UNKNOWN',e['status']['pending_count']==1 and r['status']['pending_count']==0 and r['reconcile']['resolutions'][0]['classification']=='ABSENT' and s['status']['pending_count']==1 and s['status']['paused'])
check('fresh plan/action/intent, original receipt preserved',e['plan']['content_hash']!=s['plan']['content_hash'] and e['status']['actions'][0]['id']!=s['status']['actions'][-1]['id'] and a['capture_pairs'][3]['intents'][0]['receipt']==a['capture_pairs'][4]['intents'][0]['receipt'])
check('persistent call budget, zero reopen read/effect',g['reconcile']['call_id']==h['reconcile']['call_id'] and g['reconcile']['attempt_count']==3 and h['reconcile']['attempt_count']==0 and g['export']['recovery_calls']==h['export']['recovery_calls'] and h['reconcile']['target_effects_during_reconcile']==0)
check('six released captures, terminal process records',len(a['capture_pairs'])==6 and all(x['released'] and x['SQL_matches'] for x in a['capture_pairs']) and len(a['completions'])==32 and all(not x['alive'] and x['wait_basis'] in ['EXPLICIT_WAITED','PINNED_NATIVE_WAIT_THEN_POLL'] for x in a['completions']))
check('F read-only byte stability',f['before']==f['after'] and all(f[x]==0 for x in ['claim','dispatch','publisher','reconcile']))
check('correct guard scope retained',a['bounded']['L4']['dispatch']==0 and a['bounded']['G2_G3']['transaction_bytes_unchanged'] and a['bounded']['G5']['dispatch']==0 and a['bounded']['M_L1_G4_new_business']==0 and a['bounded']['legacy_generation']==0)
output={'status':'PASS','checks':checks,'candidate':'19ab03c849bfab3dcde2dc86be37c59f3add1ebe','business_runs':0,'SQL_connections':0,'product_imports':0,'inputs':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'audit.json',BASE/'manifest.json']},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
Path(__file__).with_name('retained-checks.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(output,ensure_ascii=False,indent=2))
