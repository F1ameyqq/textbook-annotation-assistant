"""Static, offline comparison of the exact proposed capture and supplement."""
import ast,hashlib,json
from pathlib import Path
from PIL import Image
PUB=Path(__file__).resolve().parent;STAGE=Path('D:/1800/.local/stages/a25-independent-20261023/transport-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def constants(path):
 v={}
 for node in ast.parse(path.read_bytes()).body:
  if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
   for n in node.targets:
    if isinstance(n,ast.Name):v[n.id]=node.value.value
 return v
def main():
 private=STAGE/'private';raw=(private/'next-capture-plan.json').read_bytes();plan=json.loads(raw)
 assert sha(raw)=='51ed313709d56bf7064a0a65e2bd41fe138ab8d185e3b1fb852ff7d988121313'
 assert plan['product_commit']=='afc9d761294203e7cfb8086a82f1a7fdd8724372' and plan['status']=='PROPOSED_NOT_ACTIVATED' and plan['new_attempts_activated']==0
 package=STAGE/'snapshot/src/annotation/runtime/usense_live';digest=sha(canonical([{'path':p.name,'sha256':sha(p.read_bytes())} for p in sorted(package.glob('*.py'))]));assert digest==plan['implementation_sha256']
 now=constants(package/'core.py');old=constants(Path('D:/1800/.local/stages/a25-independent-20261023/review-initial-20261023/snapshot/src/annotation/runtime/usense_live/core.py'))
 for key in ['ORIGIN','TARGET','APPROVED_CERT_DER','APPROVED_SPKI']:assert now[key]==old[key]
 assert now['SCHEMA']=='UsenseLiveReadConfig/v2'
 assert plan['tls']['origin']==now['ORIGIN'] and plan['tls']['leaf_der_sha256']==now['APPROVED_CERT_DER'] and plan['tls']['spki_sha256_base64']==now['APPROVED_SPKI'] and plan['tls']['probe_seconds']==10
 assert plan['original_round']['spent']==1 and plan['original_round']['remaining']==0 and plan['original_round']['reopened'] is False
 assert plan['requested_attempts']==1 and plan['scope']=={'book_id':'46007447','printed_questions':[17,18,19,20,21],'native_orders':[18,19,20,21,22],'viewer_pages':[12,173],'source':True,'max_contexts':1,'max_inert_navigations':1,'seconds':900,'business_json_gets':40,'save_attempts_for_capture':0,'new_origin_allowed':False}
 assert plan['transport']=={'mode':'HTTP_CONNECT_PROXY','proxy_server':'http://127.0.0.1:7897'}
 assert plan['proxy_credentials'] is False and plan['auto_detection'] is False and plan['fallback'] is False
 argv=plan['configure_argv_template'];args=argv[argv.index('configure')+1:]
 def value(flag):return args[args.index(flag)+1]
 assert value('--profile')==plan['profile']=='D:/1800/.local/browser-profiles/937cbc0b7541861c7c68'
 assert value('--proxy-server')==plan['transport']['proxy_server'] and value('--seconds')=='900'
 assert args[args.index('--orders')+1:args.index('--pages')]==['18','19','20','21','22']
 assert args[args.index('--pages')+1:args.index('--source')]==['12','173']
 assert '--login' not in args and value('--reviewer')=='01a166e8-3f23-7192-a560-4724adca74b1'
 settings=(private/'evidence/local-proxy-settings-01.json').read_bytes();assert sha(settings)==plan['transport_setting_evidence_sha256']
 bindings=json.loads((private/'inputs/historical-source-url-bindings.json').read_bytes());image_facts=[]
 for row,name,command,dimensions in zip(plan['source_images']['images'],['historical-viewer-12.jpg','historical-viewer-173.jpg'],['command-0014.json','command-0015.json'],[(1220,1692),(1148,1621)]):
  image=private/'inputs'/name;image_raw=image.read_bytes();assert sha(image_raw)==row['sha256']
  with Image.open(image) as im:assert im.size==dimensions and im.format=='JPEG'
  cmdraw=(private/'inputs'/command).read_bytes();cmd=json.loads(cmdraw);assert sha(cmd['url'].encode('utf-8'))==row['expected_url_sha256']
  corresponding=next(v for v in bindings['inputs'] if v['command_sha256']==sha(cmdraw));assert corresponding['image_urls'][0]['url_sha256']==row['expected_url_sha256']
  image_facts.append({'viewer':row['viewer'],'bytes':len(image_raw),'sha256':sha(image_raw),'dimensions':list(dimensions),'historical_url_sha256':row['expected_url_sha256'],'fresh_remote_bytes_claim':False})
 assert plan['source_images']['current_images_already_acquired'] is False and plan['source_images']['image_downloads_in_this_proposal']==0 and plan['source_images']['OCR_replays']==0
 assert plan['ledger']['created'] is False and plan['ledger']['root_initialization_pending'] is True and len(plan['ledger']['required_bindings'])==5
 correction=Path('D:/1800/docs/tasks/A25-printed-number-correction-20261023.md');correction_raw=correction.read_bytes();target=STAGE/'supplement';target.mkdir(exist_ok=False)
 with (target/correction.name).open('xb') as f:f.write(correction_raw)
 save(PUB/'supplement-input.json',{'source':str(correction),'copy':str(target/correction.name),'bytes':len(correction_raw),'sha256':sha(correction_raw),'role':'Current authoritative label correction; exact original plan remains unchanged','printed_questions':[1,2,3,4,5],'historical_global_orders_before_Q7_split':[17,18,19,20,21],'reported_native_orders_to_verify':[18,19,20,21,22]})
 result={'schema':'A25IndependentNextReadonlyPlanReview/v1','result':'ACCEPTED_BOUNDED_READONLY_PLAN_FOR_ROOT_BINDING','plan_sha256':sha(raw),'supplement_sha256':sha(correction_raw),'required_root_binding':['exact product and implementation digest','exact original plan SHA256 plus this correction SHA256','fresh single attempt authority, config, window, output and launch record; no old-round reset','recheck original profile exclusive ownership before launch; no profile content read'],'product_commit':plan['product_commit'],'implementation_sha256':digest,'printed_questions_current':[1,2,3,4,5],'historical_global_orders_before_Q7_split':[17,18,19,20,21],'native_orders_pending_current_identity':[18,19,20,21,22],'scope_gets':{'inert_navigation':1,'business_json':40,'original_origin_only':True},'max_contexts':1,'seconds':900,'proxy':plan['transport'],'tls_constants_equal_parent':True,'historical_images_verified':image_facts,'historical_image_reuse':'Only after all current metadata URL digest/index/geometry/frame relations pass; remote-byte freshness remains unproven','ledger_initialization':'NOT_AUTHORIZED_BY_THIS_READONLY_PLAN; defer until five current keys and B/A reconciliation are bound by root','source_candidates_write_readback_export':'NOT_RUN','root_cause_of_original_EOF':'UNKNOWN','live_activation':False,'new_live_calls_by_reviewer':0,'code_or_plan_blocking_findings':[]}
 save(PUB/'plan-review.json',result);print(json.dumps({'result':result['result'],'implementation_sha256':digest,'supplement_sha256':sha(correction_raw),'printed_questions':[1,2,3,4,5],'business_json_gets':40,'activated':False}))
if __name__=='__main__':main()
