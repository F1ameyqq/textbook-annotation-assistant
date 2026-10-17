# -*- coding: utf-8 -*-
"""Frozen author records only, never imports or calls candidate code."""
import json
from pathlib import Path
from evidence import OUT,EV,TARGET,BASE,MAP,INDEX,raw,document,sha,write,author_key
release=document(EV+'process-release.json');assert len(release['records'])==15
records=[]
for row in release['records']:
    folder=row['path'].rsplit('/',1)[0];p=EV+folder+'/'
    pre=document(p+'preregistered.json');start=document(p+'started.json');end=document(p+'completed.json')
    expected=1 if row['pid'] in (66208,66792) else 0
    assert row['pid']==start['pid']==end['pid'] and row['exit_code']==end['exit_code']==expected
    assert pre['argv'] and pre['cwd'] and 0<pre['timeout_seconds']<=90
    assert not row['alive'] and not row['timed_out'] and not end['alive'] and not end.get('timed_out',end.get('timeout',True))
    streams={n:raw(p+n+'.txt') for n in ('stdout','stderr')}
    for n,b in streams.items():
        if n+'_sha256' in end:assert sha(b)==end[n+'_sha256']
    if 'script_pins' in pre:
        for source,digest in pre['script_pins'].items():
            rev=TARGET if (TARGET,source) in MAP else BASE
            assert sha(raw(source,rev))==digest==sha(raw(p+'script-snapshots/'+Path(source).name))
    else:
        source='tests/test_a03_p2_r9_r1_owner_lifecycle.py' if folder.startswith('validation/owner-r1-01/processes/') else 'src/annotation/runtime/recovery/native_observation.py'
        assert pre['script_sha256']==sha(raw(source))==sha(raw(p+'script-snapshot.py'))
        if 'input_sha256' in pre:assert sha(raw(p+'request.json'))==pre['input_sha256']
    records.append({'record':folder,'pid':end['pid'],'exit_code':end['exit_code'],'argv':pre['argv'],'cwd':pre['cwd'],
      'timeout_seconds':pre['timeout_seconds'],'alive':False,'timed_out':False,'stdout_sha256':sha(streams['stdout']),'stderr_sha256':sha(streams['stderr']),
      'registration_sha256':sha(raw(p+'preregistered.json')),'completion_sha256':sha(raw(p+'completed.json')),
      'classification':'ORIGINAL_BORROW_FAILURE_PRESERVED' if expected else 'COMPLETED'})
CRLF={'src/annotation/__init__.py','src/annotation/contracts/__main__.py','src/annotation/contracts/cli.py','src/annotation/contracts/integrity.py','src/annotation/contracts/models.py'}
def identity(source,digest):
    b=raw(source)
    if sha(b)==digest:return 'RAW_GIT_BYTES'
    assert source in CRLF and b'\r\n' not in b and sha(b.replace(b'\n',b'\r\n'))==digest
    return 'EXPLICIT_EXISTING_LF_TO_CRLF'
identities=[];indices=[];imports=[]
for group in ('D1','standalone','borrow'):
    p=EV+'runs/'+group+'/';body=raw(p+'product-source-index.json');indices.append(sha(body));source=json.loads(body)
    assert len(source)==65 and document(p+'preregistered.json')['product_source_index_sha256']==sha(body)
    rows=[{'source':r['path'],'actual_sha256':r['sha256'],'representation':identity(r['path'],r['sha256'])} for r in source]
    assert {r['source'] for r in rows if r['representation']!='RAW_GIT_BYTES'}==CRLF;identities.append({'group':group,'rows':rows})
for entry in INDEX:
    if entry['commit']==TARGET and entry['path'].startswith(EV+'validation/owner-r1-01/imports/') and entry['path'].endswith('.json'):
        for name,r in document(entry['path'])['modules'].items():
            source=author_key(r['path']);imports.append({'record':entry['path'],'module':name,'actual_file':r['path'],'sha256':r['sha256'],'representation':identity(source,r['sha256'])})
assert len(set(indices))==1
write(OUT/'author-process-review.json',{'status':'FIFTEEN_ORIGINAL_PROCESSES_AND_ACTUAL_SOURCE_IDENTITIES_RECONCILED','records':records,
 'source_index_sha256':indices[0],'source_index_identity':identities,'actual_imports':imports,'author_borrow':'FAILED_PRESERVED','author_D2':'NOT_RUN',
 'original_failure_stderr_sha256':'bc895733e5e37d479f5da9c57f73b29f23694a30a5b09e02a833a11cc7436fb5','product_calls_by_auditor':0,'OS_profile_scan':False})
print('{"status":"FIFTEEN_ORIGINAL_PROCESSES_AND_ACTUAL_SOURCE_IDENTITIES_RECONCILED","processes":15,"product_calls":0}')
