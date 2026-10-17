"""Explicit, resumable CPU reads of unselected inline mathematical source ROIs.

All proposed regions and skipped weak tokens remain in the layout. Inference
uses two fixed source contexts and two existing full-canvas preparations. No
transcription reference enters planning, selection, preprocessing or decoding.
"""
from __future__ import annotations
import copy
from contextlib import closing
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

import numpy as np
from PIL import Image

from .baseline import code_digest,digest,file_digest
from . import batch
from .inline_math import build_inline_math_layout
from .formula_backend import _local_cpu_backend,pixel_digest
from .formula_canvas import CONFIG as CANVAS_CONFIG,preprocess_canvas

SCHEMA='b-inline-formula-observation-trial/0.1'
CALL_SCHEMA='b-inline-formula-call-trial/0.1'
REPORT_SCHEMA='b-inline-formula-run-trial/0.1'
CONFIG={'eligibility':'MATHLIKE_RUN_WITH_OPERAND_AND_ARITHMETIC_MARKER_OR_AMBIGUOUS_TEN_BRIDGE/0.1',
        'arithmetic_markers':'=+-−×÷*/<>≤≥≠≈±∓√∛∜^_:²³⁴⁵⁶⁷⁸⁹⁰∑∏∫∂∇∈∉∪∩∠⊥∥',
        'regions':['CORE_CONTEXT_PAD2','HALO'], 'core_padding_pixels':2,
        'vertical_policy':'FULL_SOURCE_ROW_CROP_HEIGHT',
        'deduplication':'EXACT_SOURCE_BBOX_AND_CANVAS_VARIANT_ONLY',
        'elapsed_policy':'CALL_WALL_INCLUDING_PREPROCESSING_OR_SYNTHETIC_DECLARATION',
        'canvas':copy.deepcopy(CANVAS_CONFIG),'selection':'NONE'}
SQL='''
CREATE TABLE IF NOT EXISTS attempts(attempt_id TEXT PRIMARY KEY,run_id TEXT,call_id TEXT,cache_key TEXT,state TEXT,started_at TEXT,finished_at TEXT,error TEXT,output_json TEXT);
CREATE TABLE IF NOT EXISTS cache(cache_key TEXT PRIMARY KEY,call_id TEXT,attempt_id TEXT,output_json TEXT);
CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY,run_id TEXT,call_id TEXT,attempt_id TEXT,kind TEXT,details_json TEXT,created_at TEXT);
'''

def ref(v):return {k:v[k]for k in ('artifact_id','revision','content_hash')}
def now():return datetime.now(timezone.utc).isoformat()
def flags():return dict(decision='HOLD',complete=False,transcription_verified=False,business_acceptance=False,
                        platform_actions=[],graph_modified=False,expected_text_consumed=False)
def envelope(schema,kind,prefix,layout,producer,payload,inputs=None):
    inputs=inputs if inputs is not None else[ref(layout)]
    body=dict(schema_version=schema,kind=kind,revision=1,book_id=layout['book_id'],scope_id=layout['scope_id'],
              input_refs=inputs,producer=copy.deepcopy(producer),payload=payload)
    return {**body,'artifact_id':prefix+'-'+digest(body)[:24],'content_hash':digest(payload)}

def plan_inline_formula_calls(evidence,layout,original_path,*,line_ids):
    p=layout.get('payload',{})
    archived=p.get('observations_archive')
    expected=build_inline_math_layout(evidence,archived,original_path,line_ids=line_ids)
    if layout!=expected:raise ValueError('inline mathematical layout is stale or changed')
    with Image.open(original_path)as opened:image=opened.convert('RGB')
    rows={r['line_id']:r for r in p['rows']}
    calls,skipped,index=[],[],{}
    for unit in p['units']:
        text=unit.get('raw_text')or''
        operand=any(c.isdigit()or'A'<=c<='Z'or'a'<=c<='z'or'\u0370'<=c<='\u03ff'for c in text)
        eligible=(unit['kind']=='MATHLIKE_RUN'and operand
                  and(any(c in CONFIG['arithmetic_markers']for c in text)
                      or'CHINESE_TEN_OPERATOR_LOOKALIKE_UNRESOLVED'in unit['risks']))
        if not eligible:
            skipped.append(dict(unit_id=unit['unit_id'],reason='FULL_ROW_CONTEXT_ONLY'if unit['kind']=='FULL_LINE_FALLBACK'else'NO_OPERAND_AND_ARITHMETIC_OR_AMBIGUOUS_BRIDGE',
                                raw_text=unit.get('raw_text'),inference_performed=False))
            continue
        row=rows[unit['line_id']];core=unit['core_source_bbox']
        if core is None:
            core_box=list(row['crop_bbox'])
        else:
            core_box=[max(0,math.floor(core[0])-2),row['crop_bbox'][1],
                      min(image.width,math.ceil(core[2])+2),row['crop_bbox'][3]]
            if core_box[2]<=core_box[0]:core_box=list(row['crop_bbox'])
        for region,box in [('CORE_CONTEXT_PAD2',core_box),('HALO',unit['source_bbox'])]:
            tile=image.crop(box)
            for definition in CONFIG['canvas']['variants']:
                key=digest([ref(layout),box,definition])
                binding=dict(unit_id=unit['unit_id'],line_id=unit['line_id'],region_variant=region)
                if key in index:
                    calls[index[key]]['unit_bindings'].append(binding)
                    continue
                index[key]=len(calls)
                calls.append(dict(call_id='inline-formula-call-'+key[:24],source_bbox=list(box),crop_local_bbox=list(box),
                    crop_size=list(tile.size),crop_rgb_sha256=pixel_digest(tile),canvas_variant=copy.deepcopy(definition),
                    unit_bindings=[binding],localization_kind='CTC_TIMESTEP_ESTIMATE',source_glyph_complete=False))
    return image,dict(source=copy.deepcopy(p['source']),requested_line_ids=list(line_ids),
                      layout_ref=ref(layout),calls=calls,not_inference_units=skipped)

def _producer(backend):
    names=('inline_math','formula_backend','formula_canvas','batch','baseline')
    return dict(module=__name__,version='0.1.0',code_sha256=code_digest(Path(__file__)),
        dependency_code_sha256={n:code_digest(Path(__file__).with_name(n+'.py'))for n in names},
        configuration=copy.deepcopy(CONFIG),configuration_sha256=digest(CONFIG),**backend)

def _validate_call(value,plan,layout,producer,image):
    p=value.get('payload',{})
    if (value.get('schema_version')!=CALL_SCHEMA or value.get('kind')!='InlineFormulaCallTrial'
            or value.get('input_refs')!=[ref(layout)]or value.get('producer')!=producer
            or value.get('content_hash')!=digest(p)or p.get('plan')!=plan
            or any(value.get(k)!=layout[k]for k in ('book_id','scope_id'))):
        raise ValueError('cached inline formula call binding changed')
    body={k:v for k,v in value.items()if k not in ('artifact_id','content_hash')}
    if value.get('artifact_id')!='inline-formula-observed-call-'+digest(body)[:24]:
        raise ValueError('cached inline call identity changed')
    for k,v in flags().items():
        if p.get(k)!=v:raise ValueError('cached inline call verification changed')
    metadata,_=preprocess_canvas(image,plan,plan['canvas_variant'],recorded_trace=p['preprocessing']['preprocessing_trace'])
    if metadata!=p.get('preprocessing'):raise ValueError('cached inline formula pixels or trace changed')
    if (p.get('recognition_error')is not None or not isinstance(p.get('raw_latex'),str)
            or p.get('encoder_decoder_called')is not True
            or not isinstance(p.get('decoded_text'),str)):
        raise ValueError('failed or malformed call cannot be reused as successful cache')
    for field in ('engine_elapsed_seconds','wall_elapsed_seconds'):
        value=p.get(field)
        if type(value)not in (int,float)or not math.isfinite(value)or value<0:
            raise ValueError('cached inline elapsed time invalid')

def _event(db,run_id,kind,call_id=None,attempt_id=None,**detail):
    cur=db.execute('INSERT INTO events(run_id,call_id,attempt_id,kind,details_json,created_at)VALUES(?,?,?,?,?,?)',
        (run_id,call_id,attempt_id,kind,batch._json(detail),now()))
    return cur.lastrowid

def collect_inline_formula(evidence,layout,original_path,workdir,*,line_ids,model_dir=None,recognizer=None,max_items=None):
    """Return (observations, execution_report); max_items never shrinks scope.

    Only explicit collection initializes local models. An injected test callback
    receives a tensor and returns (raw_text, seconds), always SYNTHETIC_TEST.
    Immutable calls are written before SQL success; process death leaves an
    INTERRUPTED attempt, never a reusable orphan. Failed calls are not cached.
    """
    if max_items is not None and(type(max_items)is not int or max_items<1):raise ValueError('positive max_items required')
    if recognizer is not None and model_dir is not None:raise ValueError('test callback and local models are exclusive')
    image,plan=plan_inline_formula_calls(evidence,layout,original_path,line_ids=line_ids)
    original_path,workdir=Path(original_path),Path(workdir)
    before=file_digest(original_path);layout_before=digest(layout)
    frozen_layout=copy.deepcopy(layout)
    decode_state={}
    if recognizer is None and not plan['calls']:
        backend=dict(execution_kind='NO_ELIGIBLE_INLINE_FORMULA_CALLS',backend='source-geometry-only')
        resizer=None
        def recognize(tensor):raise AssertionError('no eligible formula calls were declared')
    elif recognizer is None:
        engine,backend=_local_cpu_backend(model_dir)
        backend={**backend,'execution_kind':'CPU_RAPID_LATEX_OCR_INLINE','backend_adapter':'PRESERVE_CANVAS_LEARNED_RESIZER'}
        resizer=engine.image_resizer
        def recognize(tensor):
            tokens=engine.encoder_decoder(tensor,temperature=CONFIG['canvas']['temperature'])
            decode_state['raw_token_ids']=np.asarray(tokens).tolist()
            decoded=engine.tokenizer.token2str(tokens)
            if not isinstance(decoded,list)or len(decoded)!=1 or not isinstance(decoded[0],str):raise ValueError('invalid raw formula decode')
            decode_state['decoded_text']=decoded[0]
            return engine.post_process(decoded[0]),decoded[0],np.asarray(tokens).tolist(),None
    else:
        resizer=None
        backend=dict(execution_kind='SYNTHETIC_TEST',backend='injected-tensor-test-only',worker_identity=batch._worker_identity(recognizer))
        def recognize(tensor):
            raw,elapsed=recognizer(tensor)
            return raw,raw,None,elapsed
    producer=_producer(backend);run_id='inline-formula-run-'+uuid4().hex
    workdir.mkdir(parents=True,exist_ok=True)
    completed=[];receipts=[];new=hits=invalidated=encoder_calls=0
    with batch._exclusive(workdir),closing(sqlite3.connect(workdir/'inline-formula.sqlite3'))as db:
        db.row_factory=sqlite3.Row;db.executescript(SQL)
        with db:
            for old in db.execute("SELECT * FROM attempts WHERE state='RUNNING'").fetchall():
                db.execute("UPDATE attempts SET state='INTERRUPTED',finished_at=?,error=? WHERE attempt_id=?",(now(),'Previous exclusive process interrupted',old['attempt_id']))
                _event(db,run_id,'INTERRUPTED',old['call_id'],old['attempt_id'],previous_run_id=old['run_id'])
            _event(db,run_id,'RUN_STARTED',declared_calls=len(plan['calls']),layout_ref=ref(frozen_layout),producer=producer)
        for call in plan['calls']:
            key=digest([call,producer]);cached=db.execute('SELECT * FROM cache WHERE cache_key=?',(key,)).fetchone()
            value=descriptor=attempt_id=None
            if cached:
                try:
                    descriptor=json.loads(cached['output_json']);value=batch._read_object(workdir,descriptor)
                    _validate_call(value,call,frozen_layout,producer,image)
                    origin=db.execute('SELECT * FROM attempts WHERE attempt_id=?',(cached['attempt_id'],)).fetchone()
                    if(origin is None or origin['state']!='SUCCEEDED'or origin['output_json']!=cached['output_json']
                            or origin['cache_key']!=key or origin['call_id']!=call['call_id']):raise ValueError('cached inline origin is not successful')
                    starts=db.execute("SELECT * FROM events WHERE attempt_id=? AND kind='STARTED'",(cached['attempt_id'],)).fetchall()
                    ends=db.execute("SELECT * FROM events WHERE attempt_id=? AND kind='SUCCEEDED'",(cached['attempt_id'],)).fetchall()
                    if(len(starts)!=1 or len(ends)!=1 or starts[0]['run_id']!=origin['run_id']or ends[0]['run_id']!=origin['run_id']
                            or starts[0]['call_id']!=call['call_id']or ends[0]['call_id']!=call['call_id']
                            or json.loads(starts[0]['details_json'])!={'cache_key':key}
                            or json.loads(ends[0]['details_json'])!={'cache_key':key,'output':descriptor}):
                        raise ValueError('cached inline origin events changed or missing')
                    attempt_id=cached['attempt_id']
                except (OSError,ValueError,KeyError,TypeError)as exc:
                    invalidated+=1;value=descriptor=None
                    with db:
                        db.execute('DELETE FROM cache WHERE cache_key=?',(key,))
                        _event(db,run_id,'INVALIDATED',call['call_id'],reason=str(exc),previous_output=cached['output_json'])
                else:
                    hits+=1
                    with db:event=_event(db,run_id,'CACHE_HIT',call['call_id'],attempt_id,cache_key=key,output=descriptor)
                    receipts.append(dict(call_id=call['call_id'],state='DONE',cached=True,cache_key=key,origin_attempt_id=attempt_id,output=descriptor,event_id=event))
            if value is None and(max_items is None or new<max_items):
                new+=1;attempt_id='inline-formula-attempt-'+uuid4().hex
                with db:
                    db.execute("INSERT INTO attempts VALUES(?,?,?,?,'RUNNING',?,NULL,NULL,NULL)",(attempt_id,run_id,call['call_id'],key,now()))
                    _event(db,run_id,'STARTED',call['call_id'],attempt_id,cache_key=key)
                started=time.perf_counter();state=np.random.get_state();np.random.seed(CONFIG['canvas']['seed'])
                metadata=raw=decoded=tokens=error=elapsed=None;called=False;backend_elapsed=None
                decode_state.clear()
                try:
                    metadata,tensor=preprocess_canvas(image,call,call['canvas_variant'],resizer=resizer)
                    if metadata['preprocessing_trace']['stop_reason']=='RESIZER_FAILED':raise ValueError('recorded formula resizer failure')
                    called=True;encoder_calls+=1;raw,decoded,tokens,elapsed=recognize(tensor)
                    backend_elapsed=elapsed
                    if elapsed is None:elapsed=time.perf_counter()-started
                    if(not isinstance(raw,str)or not isinstance(decoded,str)or type(elapsed)not in(int,float)or not math.isfinite(elapsed)or elapsed<0):raise ValueError('invalid formula backend result')
                except Exception as exc:
                    raw=raw if isinstance(raw,str)else None
                    decoded=decoded if isinstance(decoded,str)else decode_state.get('decoded_text')
                    tokens=tokens if tokens is not None else decode_state.get('raw_token_ids')
                    elapsed=None;error=dict(type=type(exc).__name__,status='RECOGNITION_FAILED')
                finally:np.random.set_state(state)
                payload=dict(plan=copy.deepcopy(call),preprocessing=metadata,raw_latex=raw,decoded_text=decoded,
                    raw_token_ids=tokens,recognition_error=error,encoder_decoder_called=called,
                    raw_backend_elapsed_seconds=backend_elapsed if type(backend_elapsed)in(int,float)and math.isfinite(backend_elapsed)else None,
                    engine_elapsed_seconds=elapsed,wall_elapsed_seconds=time.perf_counter()-started,**flags())
                value=envelope(CALL_SCHEMA,'InlineFormulaCallTrial','inline-formula-observed-call',frozen_layout,producer,payload)
                descriptor=batch._put_object(workdir,value)
                with db:
                    successful=error is None
                    db.execute('UPDATE attempts SET state=?,finished_at=?,error=?,output_json=? WHERE attempt_id=?',
                        ('SUCCEEDED'if successful else'FAILED',now(),batch._json(error)if error else None,batch._json(descriptor),attempt_id))
                    event=_event(db,run_id,'SUCCEEDED'if successful else'FAILED',call['call_id'],attempt_id,cache_key=key,output=descriptor)
                    if successful:db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?)',(key,call['call_id'],attempt_id,batch._json(descriptor)))
                receipts.append(dict(call_id=call['call_id'],state='DONE'if error is None else'FAILED',cached=False,cache_key=key,origin_attempt_id=attempt_id,output=descriptor,event_id=event))
            if value is None:
                completed.append(dict(plan=copy.deepcopy(call),state='PENDING',observation=None))
                receipts.append(dict(call_id=call['call_id'],state='PENDING',cached=False,cache_key=key,origin_attempt_id=None,output=None,event_id=None))
            else:completed.append(dict(plan=copy.deepcopy(call),state='DONE'if value['payload']['recognition_error']is None else'FAILED',observation=value))
        try:after=file_digest(original_path)
        except OSError:after=None
        changed=before!=after or layout_before!=digest(layout)
        counts=dict(declared_calls=len(plan['calls']),done=sum(c['state']=='DONE'for c in completed),
            pending=sum(c['state']=='PENDING'for c in completed),failed=sum(c['state']=='FAILED'for c in completed),
            cache_hits=hits,invalidated=invalidated,new_attempts=new,new_encoder_decoder_calls=encoder_calls)
        state='FAILED'if changed or counts['failed']else'PARTIAL'if counts['pending']else'READY'
        payload={**plan,'calls':completed,'layout_archive':frozen_layout,'run_complete':state=='READY',
            'input_changed_during_execution':changed,**flags()}
        observations=envelope(SCHEMA,'InlineFormulaObservationTrial','inline-formula-observations',frozen_layout,producer,payload)
        observation_output=batch._put_object(workdir,observations)
        with db:event=_event(db,run_id,'RUN_FINISHED',state=state,counts=counts,observation_output=observation_output)
        report_payload=dict(run_id=run_id,state=state,counts=counts,calls=receipts,observation_output=observation_output,
            result_ref=ref(observations),layout_ref=ref(frozen_layout),original_sha256_before=before,original_sha256_after=after,
            terminal_event_id=event,model_initializations=1 if backend['execution_kind']=='CPU_RAPID_LATEX_OCR_INLINE'else 0,**flags())
        report=envelope(REPORT_SCHEMA,'InlineFormulaRunTrial','inline-formula-run',frozen_layout,producer,report_payload,[ref(frozen_layout),ref(observations)])
        batch._put_object(workdir,report)
    return observations,report
