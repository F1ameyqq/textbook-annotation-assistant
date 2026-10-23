"""Read-only finite native/output verification; no renderer or platform run."""
import base64,hashlib,io,json,posixpath,re,sys,traceback,zipfile
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,unquote
from PIL import Image
P=Path('D:/1800/.local/stages/a28-independent-20261023/native-v1-review')
O=Path('D:/1800/docs/evidence/A28-independent/native-v1-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,v):
 b=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f:f.write(b)
 return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def norm(p):return str(p).replace('\\','/').lower()
def unique(pairs):
 result={}
 for k,v in pairs:
  assert k not in result,'DUPLICATE_JSON_KEY';result[k]=v
 return result
def loads(b):return json.loads(b,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
members=loads((O/'intake.json').read_bytes())['members']
def pick(suffix):
 rows=[r for r in members if norm(r['source_path'])==norm('D:/1800/.local/stages/a28-complete-lesson-production-20261023')+suffix.lower()];assert len(rows)==1,suffix
 return rows[0]
def raw(suffix):
 r=pick(suffix);b=Path(r['copy']).read_bytes();assert sha(b)==r['sha256'];return b
def read(suffix):return loads(raw(suffix))
by_source={norm(r['source_path']):r for r in members}
def read_ref(ref):
 r=by_source[norm(ref['path'])];b=Path(r['copy']).read_bytes();assert sha(b)==ref['sha256'] and len(b)==ref.get('bytes',len(b));return b
def normalized(s):return re.sub(r'<br\s*/?>','\n',s.replace('\r\n','\n'),flags=re.I)
ZONES={'question':'question','choice':'option','answer':'answer','analysis':'analysis'}
def signature(record):
 values=[]
 for zone,field in ZONES.items():
  v=record.get(field)
  if v is None or v=='' or v==[]:values.append('')
  elif zone=='choice':
   assert type(v) is list and all(type(x) is str for x in v);values.append('\n'.join(normalized(x) for x in v))
  else:assert type(v) is str;values.append(normalized(v))
 return (*values,record.get('tishi') or None,record.get('tihao') or None)
class HTML(HTMLParser):
 def __init__(self,source):
  super().__init__(convert_charrefs=True);self.ids=set();self.formulas={};self.images=[];self.links=[];self.resources=[];self.articles=[];self.feed(source)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:assert a['id'] not in self.ids;self.ids.add(a['id'])
  if tag=='article':self.articles.append(a)
  if tag=='span' and 'formula' in a.get('class','').split():self.formulas[a['id']]=a['data-tex']
  if tag=='img':self.images.append(a);self.resources.append(a['src'])
  if tag=='a':self.links.append(a)
  if tag in ('script','iframe','source') and 'src' in a:self.resources.append(a['src'])
  if tag=='link' and 'href' in a:self.resources.append(a['href'])
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
seen=[]
try:
 assert len(members)==276
 for m in members:
  a=Path(m['root_frozen']).read_bytes();b=Path(m['copy']).read_bytes();assert a==b and sha(b)==m['sha256'] and len(b)==m['bytes']
 fixed=read('/native-delivery-fixed.json');manifest=read('/fixed-native-delivery-01/raw-manifest.json')
 assert len(manifest['members'])==274 and sha(raw('/native-delivery-fixed.json'))=='8ac91a0445ffbc6385786eace0a48ffb88e0ffcc47dc3ea4f1b37b93ad5802f9'
 assert sha(raw('/fixed-native-delivery-01/raw-manifest.json'))=='48e215a734016d7d01bcf7f632b388af13da563ea974175c8b960dc9cf4951bf'
 for a,b in zip(manifest['members'],members[:274]):
  for k in ('source_path','frozen_path','sha256','bytes'):assert a[k]==b[k]
 actual_intake=loads(Path('D:/1800/docs/evidence/A28-independent/actual-v1-review/intake.json').read_bytes())
 actual_rows={norm(r['source_path']):r for r in actual_intake['members']}
 def actual_suffix(suffix):
  rows=[r for k,r in actual_rows.items() if k.endswith(suffix.lower())];assert len(rows)==1
  b=Path(rows[0]['copy']).read_bytes();assert sha(b)==rows[0]['sha256'];return loads(b)
 actual_result=loads(Path('D:/1800/docs/evidence/A28-independent/actual-v1-review/result.json').read_bytes())
 assert actual_result['status']=='ACCEPTED_FIXED_FOUR_SAVES_FRESH_READBACKS_AND_OWN_RELEASE_ONLY'
 assert actual_result['fixed_actual_sha256']==fixed['production_actual']['sha256']
 capture=read('/native-export-01/runs/usense-readonly-a28-native-export-01/capture-summary.json')
 response=read('/native-export-01/runs/usense-readonly-a28-native-export-01/export-response.json')
 native=raw('/native-export-01/runs/usense-readonly-a28-native-export-01/46007447_paper_questions.jsonl')
 assert sha(native)==capture['platform_export']['sha256']==response['sha256']==fixed['native_export']['sha256']
 assert len(native)==response['bytes'] and response['status']==200 and response['counts']=={'context':1,'native':1}
 assert capture['save_attempts']==capture['login_attempts']==capture['retries']==0
 release=capture['release'];assert release['context_created'] and release['context_closed'] and release['runtime_stopped'] and release['context_runtime_release_confirmed']
 assert release['errors']==[] and release['pending_callbacks']==0 and not release['automatic_login_performed']
 authority=read('/native-export-01/authority.json');once=read('/native-export-01/launch-once.json')
 assert once['authority_id']==authority['authority_id'] and once['attempts_spent']==1 and once['attempts_remaining']==0
 assert authority['limits']=={'contexts':1,'native_export_gets':1,'writes':0,'login':0,'retries':0}
 assert dt(authority['not_before'])<=dt(capture['started_at'])<dt(response['observed_at'])<dt(capture['finished_at'])<dt(authority['expires_at'])
 intent=read('/native-export-01/runs/usense-readonly-a28-native-export-01/export-request-intent.json')
 assert intent['attempts']==1 and intent['retries']==0 and intent['method']=='GET'
 events=read('/native-export-01/runs/usense-readonly-a28-native-export-01/network-events.json')
 assert all(e['method']=='GET' for e in events)
 matching=[e for e in events if e.get('url_sha256')==sha(intent['url'].encode())]
 assert len(matching)==2 and {e['layer'] for e in matching}=={'context','native'} and all(e['allowed'] for e in matching)
 lines=native.decode('utf-8-sig').splitlines();assert len(lines)==26 and all(line.strip() for line in lines)
 records=[loads(line) for line in lines];assert all(type(r) is dict for r in records)
 mapping=read('/new-four-delivery/mapping.json')
 assert mapping['native_sha256']==sha(native) and mapping['nine_unique_native_record_matches']==9
 used=set();verified=[]
 for row in mapping['mappings']:
  key=row['logical_key'];process=actual_suffix('/live-01/'+key+'/reader-process-result.json');run=process['result']['run_id'];order=row['stable_target']['question_order']
  base='/live-01/'+run+'/';expected=[]
  for zone in ZONES:
   response_zone=actual_suffix(base+f'q{order}_{zone}.json');d=response_zone['data']
   assert response_zone['message']=='success' and response_zone['code'] in (0,200)
   if d=={'success':False,'message':'未找到标注结果'}:expected.append('')
   else:assert d['success'] is True;expected.append(normalized(d['ocr_result']))
  info=actual_suffix(base+f'q{order}_info.json')['data'];expected.extend((info['tishi'],info['tihao']))
  matches=[i for i,r in enumerate(records) if signature(r)==tuple(expected)]
  assert len(matches)==1 and matches[0] not in used;used.add(matches[0]);i=matches[0]
  acceptance=actual_suffix('/live-01/'+key+'/acceptance.json');assert row['stable_target']==acceptance['comparison']['new_identity'] and row['stable_target']['info_id']==info['id']
  assert records[i]==row['record'] and i==row['native_record_index_zero_based']
  verified.append({'logical_key':key,'native_line':i+1,'stable_target':row['stable_target'],'basis':'unique full zones plus type and tihao, bound to accepted fresh readback'})
 old_closure_path=Path('D:/1800/docs/evidence/coordinator/a26-final-native-delivery-closure/receipt.json')
 old_closure=loads(old_closure_path.read_bytes());oldzip_path=Path(old_closure['portable_package']['independent_zip'])
 oldzip_raw=oldzip_path.read_bytes();assert sha(oldzip_raw)==old_closure['portable_package']['zip_sha256']=='7b1718ff909b013e0426dad890189dfa22bea5c101a6535a166544cc7c0c0bfc'
 oldzip=zipfile.ZipFile(io.BytesIO(oldzip_raw));old_prefix='A26-lesson2-five/'
 oldmap=loads(oldzip.read(old_prefix+'mapping.json'))
 assert len(oldmap['mappings'])==5
 for old in oldmap['mappings']:
  expected=signature(old['record']);matches=[i for i,r in enumerate(records) if signature(r)==expected]
  assert len(matches)==1 and matches[0] not in used;used.add(matches[0]);i=matches[0]
  current=next(r for r in mapping['old_five_current_content_only_matches'] if r['printed_question']==old['printed_question'])
  assert current['current_record']==records[i] and current['stable_target']==old['stable_target']
  verified.append({'logical_key':'q'+str(old['printed_question']),'native_line':i+1,'stable_target':old['stable_target'],'basis':'unique full zones plus type and tihao, byte-bound accepted A26 export'})
 assert len(used)==9
 zipraw=raw('/lesson-nine-delivery.zip');assert sha(zipraw)==fixed['artifact']['zip']['sha256']=='9f3ee0898149cac060feb52142f327e83d03deafb906bde203b084f606b3a1ba' and len(zipraw)==4339747
 z=zipfile.ZipFile(io.BytesIO(zipraw));names=z.namelist();assert len(names)==len(set(names))==140 and z.testzip() is None
 assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n for n in names)
 package=loads(z.read('package-manifest.json'));assert len(package['members'])==139
 assert set(names)=={r['path'] for r in package['members']}|{'package-manifest.json'}
 for row in package['members']:
  b=z.read(row['path']);assert len(b)==row['bytes'] and sha(b)==row['sha256'] and b==raw('/lesson-nine-delivery/'+row['path'])
 assert z.read('package-manifest.json')==raw('/lesson-nine-delivery/package-manifest.json')
 oldnames=[n for n in names if n.startswith('native-delivery-01/')];assert len(oldnames)==59
 for n in oldnames:assert z.read(n)==oldzip.read(old_prefix+n.removeprefix('native-delivery-01/'))
 nine=loads(z.read('nine-unit-index.json'));assert nine['denominator']==9 and len(nine['entries'])==9
 assert [r['logical_key'] for r in nine['entries']]==['q1','q2','q3','q4','q5','q6','q7','q8','q8-variant']
 docs={n:HTML(z.read(n).decode('utf8')) for n in names if n.endswith('.html')}
 entry=docs['index.html'];assert [a['data-logical-key'] for a in entry.links if 'data-logical-key' in a]==[r['logical_key'] for r in nine['entries']]
 for row in nine['entries']:
  file,anchor=row['href'].split('#');assert anchor in docs[file].ids
  assert any(a.get('href')==row['href'] and a.get('data-logical-key')==row['logical_key'] for a in entry.links)
 for filename,doc in docs.items():
  for src in doc.resources:
   if src.startswith('data:'):continue
   parsed=urlsplit(src);assert not parsed.scheme and not parsed.netloc
   path=posixpath.normpath(posixpath.join(posixpath.dirname(filename),unquote(parsed.path)));assert path in names,(filename,src)
  for a in doc.links:
   src=a.get('href','');parsed=urlsplit(src)
   if parsed.scheme or parsed.netloc:continue
   path=posixpath.normpath(posixpath.join(posixpath.dirname(filename),unquote(parsed.path))) if parsed.path else filename
   assert path in names,(filename,src)
   if parsed.fragment:assert parsed.fragment in docs[path].ids,(filename,src)
 newdoc=docs['new-four-delivery/index.html'];source_doc=docs['new-four-delivery/source-images.html']
 formulas=read('/new-four-delivery/formula-index.json');assert len(formulas)==len(newdoc.formulas)==35
 for row in formulas:
  assert newdoc.formulas[row['id']]==row['tex'] and row['raw_delimited_tex']=='$'+row['tex']+'$'
 for row in mapping['mappings']:
  for zone,field in ZONES.items():
   text='\n'.join(row['record'][field]) if zone=='choice' else row['record'][field]
   expected=re.findall(r'\$([^$]+)\$',text)
   assert [f['tex'] for f in formulas if f['logical_key']==row['logical_key'] and f['zone']==zone]==expected
 image_index=read('/new-four-delivery/image-index.json');assert len(newdoc.images)==len(image_index)==4 and len(source_doc.images)==8
 prior_intake=loads(Path('D:/1800/docs/evidence/A28-independent/code-r1-review/intake.json').read_bytes());prior_hashes={r['sha256'] for r in prior_intake['members']}
 for image,row in zip(newdoc.images,image_index):
  b=base64.b64decode(image['src'].split(',',1)[1],validate=True);assert sha(b)==row['sha256'] and b==z.read('new-four-delivery/'+row['filename'])
  assert row['sha256'] in prior_hashes and row['source_crop_sha256'] in prior_hashes
  im=Image.open(io.BytesIO(b));im.load();assert im.size==(row['width'],row['height'])
  crop=z.read('new-four-delivery/'+row['source_crop_filename']);assert sha(crop)==row['source_crop_sha256']
 display_rows=[]
 for label,formula_count,image_count in [('new-four-display-01',35,4),('new-four-source-display-01',0,8)]:
  display=read('/'+label+'/display-check.json');assert display['status']=='AUTOMATED_LAYOUT_CHECK_PASSED_MANUAL_VISUAL_PENDING'
  assert display['platform_requests']==0 and display['network_requests']==display['console_errors']==display['page_errors']==display['release_errors']==[]
  assert display['browser_closed'] and display['runtime_stopped'] and display['context_closed'] and not display['original_profile_used'] and not display['old_five_redisplayed']
  dom=display['dom'];assert dom['errors']==[] and dom['articleCount']==4 and dom['documentWidth']<=dom['viewportWidth']
  assert len(dom['formulas'])==formula_count and len(dom['images'])==image_count
  assert all(f['containers']==1 and f['merror']==0 and f['insideArticle'] and f['svgCount']==1 and f['width']>0 and f['height']>0 for f in dom['formulas'])
  assert all(im['complete'] and im['naturalWidth']>0 and im['naturalHeight']>0 and im['aspectError']==0 for im in dom['images'])
  if formula_count:assert {f['id']:f['tex'] for f in dom['formulas']}==newdoc.formulas
  for shot in display['screenshots']:
   b=read_ref(shot);im=Image.open(io.BytesIO(b));im.load();assert im.width>0 and im.height>0
   seen.append({'kind':shot['kind'],'source':shot['path'],'sha256':sha(b),'dimensions':[im.width,im.height],'direct_visual_review':'PASS'})
  display_rows.append({'mode':display['mode'],'screenshots':len(display['screenshots']),'formula_count':formula_count,'image_count':image_count})
 assert len(seen)==55 and Counter(s['kind'] for s in seen)=={'article':8,'formula':35,'image':12}
 # The model directly viewed exactly these 55 root-copy images before this check.
 put(O/'visual-review.json',{'schema':'A28IndependentNativeVisualReview/v1','status':'PASS','screenshots':seen,
  'observations':'All four native articles readable; 35 formulas/units without missing glyphs or clipping; question images and eight source/remote comparisons match; q8 variant explicitly links prior truck dimensions.',
  'old_five_screenshots_reopened':0,'browser_runs_by_reviewer':0})
 holder_results=[];nonzero=[]
 for ref in fixed['release']['holder_records']:
  h=loads(read_ref(ref));prefix=norm(ref['path']).removesuffix('/process.process.json').split('/')[-1]
  assert h['exit_code']==0 and h['errors']==[] and h['resumed'] and h['job_assigned_before_resume'] and h['job_active_processes_after']==0 and h['owned_os_release_confirmed']
  for k in ('launcher_exit_signaled','thread_handle_closed','process_handle_closed','job_handle_closed'):assert h[k]
  obs=h['observed_processes'];assert len({(r['pid'],r['creation_filetime']) for r in obs})==len(obs)
  assert all(r['exit_signaled'] and r['handle_closed'] for r in obs)
  for stream in ('stdout','stderr'):
   b=raw('/'+prefix+'/process.'+stream);assert sha(b)==h[stream]['sha256'] and len(b)==h[stream]['bytes']
  for r in obs:
   if r['exit_code']!=0:nonzero.append({'holder':prefix,**r})
  holder_results.append({'holder':prefix,'held_processes':len(obs),'job_active_after':0,'main_exit_code':0,'owned_release':True})
 assert len(nonzero)==2 and all(Path(r['image']).name=='identity_helper.exe' and r['exit_code']==3221226029 for r in nonzero)
 assert {(r['pid'],r['creation_filetime'],r['exit_code']) for r in nonzero}=={(r['pid'],r['creation_filetime'],r['exit_code']) for r in fixed['release']['nonzero_owned_child_exits']}
 seconds=(dt(fixed['timings']['artifact_fixed_at'])-dt(fixed['timings']['task_started_at'])).total_seconds();assert seconds==4582.093802
 put(O/'verification.json',{'schema':'A28IndependentNativeVerification/v1','status':'PASS_FINITE_NINE_UNIT_NATIVE_DISPLAY_AND_PORTABLE_DELIVERY',
  'root_raw_pairs':276,'declared_raw_members':274,'strict_native_records':26,'accepted_unique_full_content_matches':9,'mappings':verified,
  'export_gets':1,'export_saves':0,'export_login':0,'export_retry':0,'old_A26_byte_identical_files':59,'old_A26_zip_sha256':sha(oldzip_raw),
  'zip_sha256':sha(zipraw),'zip_bytes':len(zipraw),'zip_files':140,'zip_manifest_members':139,'all_package_members_equal_root_frozen_bytes':True,
  'nine_unit_navigation_and_anchors':'PASS','new_formulas':35,'new_question_images':4,'source_gallery_images':8,'directly_viewed_screenshots':55,
  'old_screenshots_reopened':0,'display_checks':display_rows,'all_HTML_asset_references_offline':True,'holders':holder_results,
  'nonzero_owned_child_exits':nonzero,'nonzero_child_exit_cause':'UNKNOWN','nonzero_child_specific_artifact_effect':'No defect found in 55 frozen screenshots, DOM checks, native mappings or package hashes; no universal health claim.',
  'production_seconds':42.639465,'preparation_to_final_fixed_seconds':seconds,'postproduction_commands':5,'whole_task_unattended':False,
  'limitations':['Only nine uniquely mapped records accepted, other native records not reaccepted.','Old directory attribution retained; offline navigation follows logical lesson units.',
   'Observed desktop screenshots accepted; no new browser, print or mobile run.','Whole-task initial start and zero user actions are author-declared; process interval is raw-timestamp verified.'],
  'reviewer_platform_calls':0,'reviewer_test_suites':0,'reviewer_active_source_reads':0})
 print(json.dumps({'status':'PASS','unique_records':9,'zip_files':140,'screenshots':55,'nonzero_child_exits_retained':2}))
except BaseException as exc:
 put(O/'verification-failure-corrected2.json',{'status':'STOP_FIRST_REVIEW_FAILURE','type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'successors':'NOT_RUN'})
 raise
