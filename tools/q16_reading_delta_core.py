"""Independent four-task content delta checks; no producer or platform imports."""
import copy,json,re
from pathlib import Path
class Reject(ValueError):pass
def need(ok,code):
 if not ok:raise Reject(code)
def same(a,b,code):need(type(a) is type(b) and json.dumps(a,ensure_ascii=False,separators=(',',':'))==json.dumps(b,ensure_ascii=False,separators=(',',':')),code)
def artifacts(bundle):
 value={a['kind']:a['payload'] for a in bundle['artifacts']};need(len(value)==len(bundle['artifacts'])==4 and set(value)=={'SourceBundle','EvidenceBundle','QuestionGraph','CheckReport'},'FOUR_ACTIVE_ARTIFACTS');return value
def label_removed(text,n):
 need(type(text) is str,'LABEL_TEXT_TYPE');m=re.match(r'^(?:（'+str(n)+r'）|\('+str(n)+r'\))\s*',text);need(m is not None,'Q16_SUBQUESTION_LABEL_'+str(n)+'_MISSING_OR_WRONG');return text[m.end():]
def check(old_bundle,old_side,new_bundle,new_side):
 old,new=artifacts(old_bundle),artifacts(new_bundle);oldg,newg=old['QuestionGraph'],new['QuestionGraph'];olde,newe=old['EvidenceBundle'],new['EvidenceBundle'];s0,s1=old['SourceBundle'],new['SourceBundle'];same(s0['assets'],s1['assets'],'ORIGINAL_SOURCE_ASSETS_CHANGED');same(s0['scope_manifest'],s1['scope_manifest'],'FOUR_SCOPE_MANIFEST_CHANGED')
 oldregions={v['region_id']:v for v in olde['regions']};newregions={v['region_id']:v for v in newe['regions']};need(len(oldregions)==len(newregions)==37 and set(oldregions)==set(newregions),'REGION_SCOPE_CHANGED')
 for rid,oldregion in oldregions.items():
  value=copy.deepcopy(newregions[rid]);need(value['certainty']=='CONFIRMED','SOURCE_REGION_NOT_CONFIRMED');value['certainty']=oldregion['certainty']
  if rid in {'region-q16-task'+str(n) for n in (1,2,3)}:value['text']=label_removed(value['text'],int(rid[-1]))
  same(oldregion,value,'REGION_CONTENT_OR_SOURCE_DELTA:'+rid)
 same(oldg['fragments'],newg['fragments'],'GRAPH_FRAGMENTS_CHANGED_OR_DIAGNOSTIC_PROMOTED');need(len(newg['fragments'])==26,'FRAGMENT_COUNT')
 need(len(newg['questions'])==len(oldg['questions'])==4,'QUESTION_COUNT')
 for q0,q1 in zip(oldg['questions'],newg['questions']):
  value=copy.deepcopy(q1);value['directory_id']=q0['directory_id'];same(q0,value,'QUESTION_IDENTITY_OR_SHARED_MATERIAL_CHANGED')
 shared=newg['questions'][1]['shared_fragment_ids'];need(len(shared)==8 and all(q['shared_fragment_ids']==shared for q in newg['questions'][1:]),'SHARED_EIGHT_MATERIALS_CHANGED')
 dirs={v['directory_id']:v for v in s1['directories']};q16dir=newg['questions'][0]['directory_id'];readingdir=newg['questions'][1]['directory_id'];need(q16dir!=readingdir and all(q['directory_id']==readingdir for q in newg['questions'][1:]),'FOUR_TASK_DIRECTORY_SCOPE');need('一定是直角三角形吗' in dirs[q16dir]['label'] and '漫话勾股世界' in dirs[readingdir]['label'],'SOURCE_DIRECTORY_LABELS')
 need(len(newg['answer_relations'])==4,'ANSWER_RELATION_COUNT')
 for before,after in zip(oldg['answer_relations'],newg['answer_relations']):
  need(after['status']=='SELECTED' and after['selected_fragment_ids']==before['candidate_fragment_ids'],'SOURCE_CONFIRMED_ANSWER_SELECTION_OR_OWNER');value=copy.deepcopy(after);value['status']=before['status'];value['selected_fragment_ids']=before['selected_fragment_ids'];need(type(after['evidence_refs']) is list and bool(after['evidence_refs']) and all(type(v) is str for v in after['evidence_refs']),'ANSWER_SOURCE_EVIDENCE');value['evidence_refs']=before['evidence_refs'];same(before,value,'ANSWER_MAPPING_CHANGED')
 same(old_side['source_proofs'],new_side['source_proofs'],'CROP_SOURCE_PROOFS_CHANGED');same(old_side['q16_formula_slots'],new_side['q16_formula_slots'],'ELEVEN_FORMULA_DIAGNOSTICS_CHANGED');same(old_side['reading_task_answers'],new_side['reading_task_answers'],'READING_ANSWER_MAP_CHANGED');same(old_side['q16_task_map'],new_side['q16_task_map'],'Q16_SUBTASK_ANSWER_SPANS_CHANGED')
 need(len(old_side['bindings'])==len(new_side['bindings']),'BINDING_COUNT')
 for before,after in zip(old_side['bindings'],new_side['bindings']):
  value=copy.deepcopy(after)
  if before['block_id'] in {'q16-task'+str(n) for n in (1,2,3)}:
   need(value['runs'] and value['runs'][0]['format']=='plain','LABEL_RICH_RUN');value['runs'][0]['text']=label_removed(value['runs'][0]['text'],int(before['block_id'][-1]))
  same(before,value,'RICH_RUN_OR_BINDING_DELTA:'+before['block_id'])
 blanks=[run for b in new_side['bindings'] for run in b['runs'] if run['format']=='blank'];need(len(blanks)==6 and all(run['value'] is None for run in blanks),'SIX_UNFILLED_BLANKS')
 need(new_side['human_verified'] is False and new_side['business_acceptance'] is False and not new_side['platform_actions'],'NO_FALSE_HUMAN_OR_PLATFORM_CLAIM');need(new_side.get('a_owner_acceptance',False) is False,'NO_FALSE_A_OWNER_CLAIM')
 return {'status':'FOUR_TASK_CONTENT_DELTA_MATCH','questions':4,'shared_fragments':8,'unfilled_blanks':6,'formula_diagnostics':11,'source_regions_and_crops':37,'graph_fragments':26,'q16_printed_labels_restored':3,'selected_answer_relations':4,'platform_requests':0,'human_acceptance':False,'a_owner_acceptance':False}
