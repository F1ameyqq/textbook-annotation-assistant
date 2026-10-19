"""Read-only fixed A09 delivery preflight. Does not import or run product code."""
import hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('D:/1800')
WORKFLOW='0a9c634d160ac7b39f68a1fb3555f409dd408f49'
PRODUCT='29c82b0997be3080f53dfde2afbb1d7457b04197'
DELIVERY='439423ebf4277e3825aba24fed6f56546ef66a2b'
PREFIX='docs/evidence/A09/execution/'
OUT=ROOT/'docs/evidence/coordinator/a09-preflight-20261019'
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1')
def git(*args, data=None):
    return subprocess.run(['git','-c','core.longpaths=true','-C',str(ROOT),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV,check=True).stdout
def tree(ref):
    result={}
    for row in git('ls-tree','-rz',ref).split(b'\0'):
        if row:
            entry,name=row.split(b'\t',1)
            result[name.decode('utf-8')]=entry.decode()
    return result
cache={}
def blob(ref,path):
    key=(ref,path)
    if key not in cache: cache[key]=git('cat-file','blob',ref+':'+path)
    return cache[key]
def obj(path): return json.loads(blob(DELIVERY,PREFIX+path))
def sha(b): return hashlib.sha256(b).hexdigest()
def prefetch(keys):
    keys=list(dict.fromkeys(k for k in keys if k not in cache))
    raw=git('cat-file','--batch',data=''.join(r+':'+p+'\n' for r,p in keys).encode('utf-8'))
    offset=0
    for key in keys:
        end=raw.index(b'\n',offset); parts=raw[offset:end].split(); assert parts[1]==b'blob'
        size=int(parts[2]); cache[key]=raw[end+1:end+size+1]; offset=end+size+2
    assert offset==len(raw)
def verify_members(ref,members):
    seen=set(); total=0
    for m in members:
        p=m['path']; assert p not in seen, p; seen.add(p)
        b=blob(ref,p)
        assert len(b)==m['bytes'] and sha(b)==m['sha256'],p
        if 'git_blob' in m: assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==m['git_blob'],p
        if 'git_tree_entry' in m: assert trees[ref][p]==m['git_tree_entry'],p
        total+=len(b)
    return {'members':len(seen),'bytes':total}
trees={r:tree(r) for r in (WORKFLOW,PRODUCT,DELIVERY)}
for p,e in trees[WORKFLOW].items(): assert trees[PRODUCT].get(p)==e and trees[DELIVERY].get(p)==e,p
for p,e in trees[PRODUCT].items(): assert trees[DELIVERY].get(p)==e,p
new=set(trees[DELIVERY])-set(trees[WORKFLOW])
allowed_prefixes=('src/annotation/source/b_q4/','src/annotation/delivery/q4_offline/','tests/fixtures/a09/','examples/a09/','docs/evidence/A09/execution/')
allowed_exact={'src/annotation/quality/q4_offline.py','config/policies/a09-q4-offline-v1.json','docs/a09-q4-offline-simulation.md','docs/tasks/A09-Q4-execution-report.md'}
for p in new: assert p.startswith(allowed_prefixes) or p in allowed_exact or re.fullmatch(r'tests/test_a09_[^/]+\.py',p),p
manifest=obj('delivery-member-manifest.json')
assert manifest['frozen_product_commit']==PRODUCT and manifest['workflow_commit']==WORKFLOW
assert {m['path'] for m in manifest['members']} | {PREFIX+'delivery-member-manifest.json'}==new
product_members=obj('product-raw-members.json')['frozen_new_members']
runtime_members=obj('candidate-1/runtime-members.json')
prefetch([(DELIVERY,m['path']) for m in manifest['members']]+[(PRODUCT,m['path']) for m in product_members+runtime_members])
delivery_verified=verify_members(DELIVERY,manifest['members'])
product_verified=verify_members(PRODUCT,product_members)
runtime_verified=verify_members(PRODUCT,runtime_members)
inputs=obj('input-raw-manifest.json')
verified_input_names=[]
for m in inputs['inputs']:
    b=Path(m['own_path']).read_bytes() if 'own_path' in m else blob(m['revision'],m['path'])
    assert ('bytes' not in m or len(b)==m['bytes']) and sha(b)==m['sha256'],m['name']
    verified_input_names.append(m['name'])
original=Path(inputs['original_stage_source']).read_bytes()
assert len(original)==1440149 and sha(original)=='b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673'
bindings={'docs/approvals/A09-Q4-offline-business-approval.json':'5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010','docs/reviews/q4-first-lesson/proposal.json':'e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe'}
for p,h in bindings.items(): assert sha(blob(PRODUCT,p))==h
summary=obj('candidate-1/trial/summary.json')
assert summary['identity']['actual_head']==PRODUCT==summary['identity']['frozen_head']
assert summary['normal_attempts']==summary['successful_normal_closures']==summary['business_dispatches']==1
assert summary['actual_questions_added']==1 and summary['actual_frames_added']==4
assert summary['approval_comparison_differences']==[] and len(summary['refusals'])==10
assert all(x['rejected'] and x['new_frames']==x['new_questions']==x['business_dispatches']==0 and x['before_sha256']==x['after_sha256'] for x in summary['refusals'])
expected=[('Q','image','viewer-10',[334,975,581,1077]),('Q','text','viewer-10',[100,1118,592,1193]),('Q','text','viewer-10',[99,1202,220,1235]),('A','text','viewer-173',[324,239,342,257])]
for actual,(role,kind,img,box) in zip(summary['actual_frames'],expected):
    assert (actual['platform_role'],actual['platform_type'],actual['box']['image']['asset_id'],actual['box']['bbox'])==(role,kind,img,box)
assert summary['platform_calls']==summary['pushes']==summary['B_messages']==summary['A08_CLI_calls']==summary['B_producers_executed']==0
launch=obj('candidate-1/launch-1.json'); release=obj('candidate-1/release.json')
assert launch['frozen_head']==release['frozen_head']==PRODUCT
assert launch['supervisor_exit_code']==0 and launch['supervisor_released'] and launch['original_process_handle_waited']
assert release['exit_code']==0 and release['child_released'] and release['waited_original_handle'] and not release['timed_out']
assert release['elapsed_seconds']<180 and launch['within_240_seconds'] and release['background_services']==0
def dt(s):
    s=re.sub(r'(\.\d{6})\d+',r'\1',s).replace('Z','+00:00')
    return datetime.fromisoformat(s)
for start,end in [(launch['supervisor_kernel_creation_time'],launch['supervisor_end_time']),(release['child_kernel_creation_time'],release['child_ended_at'])]: assert 0<(dt(end)-dt(start)).total_seconds()<240
pids=[launch['supervisor_pid'],release['child_pid']]
ps="@("+','.join(str(p) for p in pids)+") | ForEach-Object { $wantedPid=$_; $p=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$wantedPid); if ($null -eq $p) { [pscustomobject]@{queried_pid=$wantedPid;found=$false} } else { [pscustomobject]@{queried_pid=$wantedPid;found=$true;creation_time=$p.CreationDate.ToUniversalTime().ToString('o')} } } | ConvertTo-Json -Compress"
query=subprocess.run(['powershell','-NoProfile','-Command',ps],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode('utf-8-sig')
current=json.loads(query)
for q in current:
    if q['found']:
        end=launch['supervisor_end_time'] if q['queried_pid']==pids[0] else release['child_ended_at']
        assert dt(q['creation_time'])>dt(end),'Original PID still active or ambiguous'
result={'status':'PREFLIGHT_PASS_NOT_ACCEPTANCE','at':datetime.now(timezone.utc).isoformat(),'workflow':WORKFLOW,'product':PRODUCT,'delivery':DELIVERY,'old_workflow_entries_unchanged':len(trees[WORKFLOW]),'all_product_entries_unchanged':len(trees[PRODUCT]),'new_paths':len(new),'delivery_manifest':delivery_verified,'delivery_manifest_sha256':sha(blob(DELIVERY,PREFIX+'delivery-member-manifest.json')),'product_manifest_verified':product_verified,'runtime_manifest_verified':runtime_verified,'input_names_verified':verified_input_names,'original_zip_verified':True,'approval_and_proposal_binding':True,'reported_normal_attempts':1,'reported_successes':1,'reported_dispatches':1,'reported_zero_write_refusals':10,'four_approved_roles_types_and_boxes_match_summary':True,'original_handle_release_records_valid':True,'live_pid_query':current,'coordinator_new_business_runs':0,'coordinator_product_tests':0,'scope':'Delivery/raw-byte/release and archived summary preflight only; independent review still required'}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'preflight.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(result,ensure_ascii=True))
