# -*- coding: utf-8 -*-
"""Compare the fixed data export to accepted raw readers; no product/OCR/rendering."""
import ast,hashlib,json,re
from pathlib import Path,PureWindowsPath
P=Path(__file__).resolve().parent
S=Path('D:/1800/.local/stages/a25-independent-20261023/final-recovery-actual-review-20261023')
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(p):return PureWindowsPath(str(p)).as_posix().lower()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def main():
 facts=json.loads((P/'actual-facts.json').read_bytes());er=json.loads((S/'export/registry.json').read_bytes());ar=json.loads((S/'registry.json').read_bytes());old=json.loads(Path('D:/1800/.local/stages/a25-independent-20261023/five-save-actual-review-20261023/registry.json').read_bytes());old4=json.loads(Path('D:/1800/.local/stages/a25-independent-20261023/remaining-two-actual-review-20261023/registry.json').read_bytes());known={**old,**old4,**ar};used={};matching=0
 for k,v in er.items():
  if k in known:
   p=Path(known[k]);b=p.read_bytes();assert Path(v).read_bytes()==b;matching+=1;used[str(p)]={'path':str(p),'bytes':len(b),'sha256':sha(b)}
 def local(suffix):return Path(next(v for k,v in er.items() if k.endswith(suffix)))
 data=json.loads(local('/readback-data.json').read_bytes());verification=json.loads(local('/content-verification.json').read_bytes());assert len(data['rows'])==5
 assert data['platform_paper_export_endpoint_called'] is False and data['platform_native_paper_export_verified'] is False
 assert verification['new_platform_requests']==verification['new_image_downloads']==verification['new_ocr_or_model_calls']==0
 script=local('/package-final-readback-data.py');tree=ast.parse(script.read_text(encoding='utf-8'))
 assert not any(isinstance(n,ast.Import) and any(x.name in ['requests','httpx','socket','subprocess'] for x in n.names) for n in ast.walk(tree))
 rows=[];zones=['question','choice','answer','analysis','knowledge_point'];all_native_files=set()
 for i,row in enumerate(data['rows'],1):
  original=facts['cumulative'][i-1];source=facts['reader_source_maps'][str(i)];q=i+17
  assert row['printed_question']==i and row['historical_global_order']==i+16 and row['target']==original['target'] and row['reader_run']==original['reader_run'] and set(row['zones'])==set(zones)
  prefix=norm(source['run_prefix']);capture=json.loads(Path(er[prefix+'/capture-summary.json']).read_bytes());names=['directory','frames','source',f'q{q}_annotations',f'q{q}_info',*[f'q{q}_{z}' for z in zones],'page_12','page_173'];assert set(capture['captures'])==set(names)
  raw={}
  for name in names:
   key=prefix+'/'+name+'.json';b=Path(er[key]).read_bytes();cap=capture['captures'][name];assert sha(b)==cap['sha256'] and len(b)==cap['bytes'];raw[name]=json.loads(b);all_native_files.add(key)
  assert raw[f'q{q}_info']['data']['id']==row['target']['info_id'] and raw[f'q{q}_info']['data']['file_id']==row['target']['book_id'] and int(raw[f'q{q}_info']['data']['order_in_level'])==q
  suffix='/target-'+sha(row['target']['node_id'].encode())[:24]+'/plan.json';pp=Path(next(v for k,v in er.items() if k.endswith(suffix)));plan=json.loads(pp.read_bytes());assert plan['target']==row['target']
  images=[];formulas=[]
  for zone in zones:
   record=row['zones'][zone];key=norm(record['raw_response_path']);assert key==prefix+f'/q{q}_{zone}.json';b=Path(er[key]).read_bytes();native=json.loads(b)['data'];assert sha(b)==record['raw_response_sha256']
   if native['success'] is True:
    text=native['ocr_result'];assert type(text) is str and record['state']=='PRESENT' and record['text']==text and record['text_sha256']==sha(text.encode('utf-8')) and text==plan['expected']['zones'][zone]['data']['ocr_result']
    for ref in re.findall(r'<img src="([^"]+)"',text):
     assert any(a['image_path']==ref for a in raw[f'q{q}_annotations']['data']);images.append({'zone':zone,'image_ref':ref,'matches_current_annotation_image_path':True})
    formulas.extend({'zone':zone,'raw_inline_tex':x} for x in re.findall(r'\$([^$]*)\$',text))
   else:assert native['success'] is False and record['state']=='ABSENT' and record['text'] is None and record['text_sha256'] is None
  assert images==row['image_references_in_actual_saved_text'] and len(images)==1 and formulas==row['formula_strings_in_actual_saved_text'] and row['content_text_equals_accepted_plan_expected'] is True
  rows.append({'printed_question':i,'native_order':q,'node_id':row['target']['node_id'],'info_id':row['target']['info_id'],'reader_run':row['reader_run'],'original_native_files':12,'exact_raw_copies':True,'all_five_zone_text_state_and_hash_bindings':True,'current_annotation_image_url_matches':1,'verbatim_inline_formula_strings':len(formulas),'visual_rendering':'NOT_OBSERVED','underlying_acceptance':original['readback_acceptance'],'original_readback_status_in_export':row['readback_status']})
 assert len(all_native_files)==60
 result={'schema':'A25IndependentReadbackDataExportResult/v1','status':'ACCEPTED_FIVE_FRESH_READER_RAW_DATA_EXPORT_ONLY','raw_package_members':76,'manifest_sha256':'2b44c551610c07983e55c8cf90e5ee7dd1e94e551dddaf1ac83a7d810a9b37e8','known_actual_original_copies_identical':matching,'native_reader_originals':60,'rows':rows,'stable_ids_and_reader_sources_match_final_actual':True,'paper_native_export':'NOT_RUN','image_or_formula_actual_visual_rendering':'NOT_RUN_NOT_OBSERVED','new_platform_OCR_render_or_product_comparison_execution':0,'author_pending_review_labels_retained_as_original_metadata':True,'reused_fixed_files':used}
 with (P/'export-result.json').open('xb') as f:f.write(enc(result))
 print(json.dumps({'status':result['status'],'raw_native_files':60,'stable_targets':5,'matching_old_source_copies':matching}))
if __name__=='__main__':main()
