# -*- coding: utf-8 -*-
"""Map original frozen V/R criteria to actual bounded evidence, without new tests."""
import json
import re
import subprocess
from evidence import OUT,ROOT,EV,document,text,sha,write
WF='c728ce1587cb68a22a212cb48d71facf584ec426'
def rows(path,prefix):
    body=text(path,WF);found={}
    for n,line in enumerate(body.splitlines(),1):
        match=re.match(r'^\|\s*('+prefix+r'\d{2})\s*\|(.*)$',line)
        if match:found[match[1]]={'source':path,'workflow':WF,'line':n,'original_criterion':line}
    return found
original={**rows('docs/tasks/A03-runtime-recovery.md','V'),**rows('docs/tasks/A03-independent-review.md','R')}
assert set(original)=={'V%02d'%i for i in range(1,11)}|{'R%02d'%i for i in range(1,19)}
author=document(EV+'p2-coverage-map.json');entries=[]
for row in author['V']+author['R']:
    identity=row['id'];status='PARTIAL' if row['status'] not in ('NOT_RUN','NOT_RUN_FULL','NOT_RUN_NATIVE','NOT_RUN_NEGATIVE_MATRIX') else row['status']
    refinement='Only the actual fixed local/N1-N5 evidence in this review; no original criterion waived.'
    if identity in ('V08','R14'):
        status='PARTIAL_N7_FAILED_ASSERTION_INIT_NOT_REACHED';refinement='Actual old-entry refusal occurred; exact outer diagnostic symbol is not an existing written requirement. Original N7 stays FAILED; incomplete initialization NOT_REACHED.'
    elif identity in ('V09','R15'):refinement='Actual 1.1 JSON historical read plus validated R7 static 1.3 only; no legacy archive-validator acceptance or conversion execution.'
    elif identity in ('V07','R02'):refinement='N3 reaches schema-valid direct semantic comparison with each named FAIL, not negative PRE admission; N4/N5 exact authority refusals are recorded.'
    elif identity in ('V06','R13'):refinement='Two actual admissions on the same hold, with normal generation/head progression and real expiry; distinct hold-id replacement and qualified clearing NOT_RUN.'
    elif identity=='R04':status='PASS_FIXED_SYNTHETIC_N1_ONLY';refinement='Actual separate SQLite transactions, effect-after-commit exit87, independent count=1 and fresh read; no real-platform or arbitrary-writer guarantee.'
    elif identity=='R01':status='PASS_FROZEN_REVIEW_SCOPE_ONLY';refinement='Exact target, raw input/preservation and bounded independent runs verified; integration is not granted.'
    entries.append({**original[identity],'id':identity,'author_status':row['status'],'independent_status':status,
      'actual_covered':row['covered'],'remaining_original_scope':row['remaining'],'review_refinement':refinement})
path='docs/tasks/A03-P2-R8-native-bridge-implementation.md';spec=WF+':'+path
data=subprocess.run(['git','-c','core.longpaths=true','cat-file','--batch'],cwd=ROOT,input=(spec+'\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
header,body=data.split(b'\n',1);parts=header.decode().split();assert len(parts)==3 and parts[1]=='blob';n=int(parts[2]);raw=body[:n];assert body[n:]==b'\n'
import hashlib
assert hashlib.sha1(b'blob '+str(n).encode()+b'\0'+raw).hexdigest()==parts[0]
dest=OUT/'input/supplement/R8-native-bridge-implementation.md';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
write(OUT/'supplemental-input-index.json',{'role':'one original N1-N7 authority document only, not extra author pins',
 'files':[{'commit':WF,'path':path,'file':dest.relative_to(OUT).as_posix(),'bytes':n,'sha256':sha(raw),'raw_git_sha1':parts[0]}]})
body=raw.decode('utf8');assert '| N6 ' in body and '| N7 ' in body
minimum=[
 {'gap':'Creation anchor derivation under complete UNKNOWN history and formal dependency control','existing_basis':['N6','R02','R15'],'current':'NOT_RUN'},
 {'gap':'Initialization interruption before formal completion and fail-closed reopen','existing_basis':['N7 unreached branch','V08','R14'],'current':'NOT_REACHED'},
 {'gap':'Resolve the exact diagnostic assertion against the existing fail-closed contract','existing_basis':['N7 failed outer-code assertion','V08','R14'],'current':'FAILED test assertion; no mandatory product change established'},
 {'gap':'Hold clearing or distinct hold replacement, if an integration path will resume writes','existing_basis':['N2 remaining lifecycle','V07','R13'],'current':'NOT_RUN; same-hold PRE admission does not grant writer authority'}]
value={'status':'ALL_28_ORIGINAL_CRITERIA_REVIEWED_NO_WAIVER','entries':entries,'N6':'NOT_RUN','N7_original':'FAILED',
 'minimum_unclosed_interfaces_for_coordinator':minimum,
 'other_existing_requirements_retained':['native normal and explicit-not-applied demonstrations in original task section 6',
 'multi-action tail and sufficient/insufficient ABSENT','same-book multi-scope/run and native multi-book isolation',
 'two-owner race and other crash points','legacy archive/conversion and real/ORIGINAL/OBSERVED/S01 boundary',
 'old-report reuse/VERIFIED tampering and denominator/skip/max-attempt boundaries'],
 'integration_limit':'This review does not choose waivers or release I01. Future broad coverage remains mapped, not new invented tasks; B/S01 dependencies stay separate.',
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'p2-independent-coverage-review.json',value)
print(json.dumps({'status':value['status'],'criteria':len(entries),'supplemental_authority_files':1,'new_product_tests':0}))
