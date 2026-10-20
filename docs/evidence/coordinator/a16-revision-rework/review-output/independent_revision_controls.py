"""Independent revision-only controls. New harness data; no old suite/candidate replay."""
import asyncio
import copy
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import AsyncMock, patch

ROOT=Path('D:/1800-worktrees/a16-r1-review')
OUT=ROOT/'docs/evidence/A16/independent-r1-review'
START=time.monotonic()
ATTEMPTS=[]


def forbidden(name):
    def denied(*a,**k):
        ATTEMPTS.append(name);raise AssertionError('REAL_RESOURCE_DENIED_'+name)
    return denied


def audit(event,args):
    if event in ('socket.connect','socket.bind','subprocess.Popen','os.kill'):
        forbidden(event)()
    if event=='open' and isinstance(args[0],(str,bytes)):
        text=os.fsdecode(args[0]).replace('\\','/').lower()
        if '/.local/' in text or 'browser-profiles' in text:forbidden('PRIVATE_PROFILE_PATH')()


sys.addaudithook(audit)
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'tests/a16_current_readonly')]
with patch.object(ctypes,'WinDLL',forbidden('NATIVE_IMPORT')):
    import a16_current_state_probe as probe
    from annotation.source.usense.current_readonly import gate,policy,decode
    from test_frame_binding_revision import CollectHarness
from PIL import Image,ImageFile


class NoIOLoop(asyncio.SelectorEventLoop):
    def _make_self_pipe(self):pass
    def _close_self_pipe(self):pass
    def _write_to_self(self):pass
    def __init__(self):
        super().__init__();self._selector.select=lambda timeout=None:[]
class NoIOPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):return NoIOLoop()
asyncio.set_event_loop_policy(NoIOPolicy())

VALID=(OUT/'native-fetch-valid.js').read_bytes()
INVALID=(OUT/'reserved-getter-invalid.js').read_bytes()


def harness(script=VALID):
    h=CollectHarness();h.guard.scripts=[{'bytes':script,'ref':'INDEPENDENT_NATIVE_FETCH.js','loaded_origin':{}}]
    return h


def summary(h):
    r=h.result
    return {'outcome':r.get('outcome'),'error':r.get('error'),'calls':h.calls,
        'steps':r.get('steps'),'sample_status':r.get('sample',{}).get('status'),
        'sample_content':r.get('sample',{}).get('content'),
        'sample_registered':h.guard.policy.sample_order,
        'wire':h.files.get('wire-observation.json'),'saved_names':list(h.files),
        'real_resources':False}


async def r1_current_binding():
    h=harness();h.sample=h.sample[2:]+h.sample[:2]
    seen=[];actual=probe.bound_content
    def observe(body,zone,order,frames,confirmed):
        seen.append({'zone':zone,'same_current_binding':frames is h.result['sample']['frame_binding']['frames'],
            'same_old_inventory':frames is h.result['target']['questions'][0]['frames']})
        return actual(body,zone,order,frames,confirmed)
    with patch.object(probe,'bound_content',observe):await h.collect()
    assert len(seen)==3 and all(x['same_current_binding'] and not x['same_old_inventory'] for x in seen)
    assert h.result['sample']['content']['choice']['rect_ids']==['3-1','3-2','3-3','3-4']
    assert h.result['sample']['status']=='PROVISIONAL_PENDING_FINAL_GUARD'
    assert 'sample-readback.json' not in h.files
    return {'actual':summary(h),'data_flow_observation':seen}


async def r1_optional_zone_presence():
    h=harness()
    for row in h.frames['data']:
        if row['rect_id']=='3-1':row['zone']='choice'
    # Current sample lacks an explicit zone present in the full inventory.
    try:await h.collect()
    except gate.Stop:pass
    else:raise AssertionError('MISSING_EXPLICIT_ZONE_ACCEPTED')
    assert not any('get_question_info' in c or 'get-ocr-annotation' in c for c in h.calls)
    assert h.result['sample']['status']=='REJECTED_RUN_FAILED'
    return summary(h)


async def r1_source_digest_conflict():
    h=harness();h.sample[2]['image_path_sha256']='0'*64
    try:await h.collect()
    except gate.Stop:pass
    else:raise AssertionError('CONFLICTING_SOURCE_DIGEST_ACCEPTED')
    assert h.result['steps']['sample_frames']=='FAILED'
    assert h.result['steps']['content_question']=='NOT_RUN'
    return summary(h)


async def r1_late_answer_guard():
    h=harness()
    def late(zone,body):
        if zone=='answer':h.guard.record_failure(gate.Stop('INDEPENDENT_LATE_ANSWER_GUARD'))
    h.body_mutate=late
    await h.observe()
    assert h.exit_code==2 and h.result['outcome']=='ERROR'
    assert h.result['sample']['content_acceptable'] is False
    assert all(x['status']=='UNKNOWN' and x['text'] is None for x in h.result['sample']['content'].values())
    assert 'sample-readback.json' not in h.files and 'sample-rejected.json' in h.files
    return summary(h)


async def r2_supported_relation():
    h=harness();await h.collect();w=h.files['wire-observation.json']
    assert w['status']=='CURRENT_CODE_CONFIRMED' and len(h.calls)==11
    raw=VALID.decode()
    for binding in w['binding_proof']['bindings'].values():
        assert binding['asset_sha256']==hashlib.sha256(VALID).hexdigest()
        for ref in binding['field_refs'].values():
            fragment=raw[ref['start']:ref['end']]
            assert hashlib.sha256(fragment.encode()).hexdigest()==ref['code_sha256']
    assert h.result['sample']['content']['choice']['status']=='AVAILABLE'
    return summary(h)


async def unknown_case(script=None,assets=None):
    h=harness(script if script is not None else VALID)
    if assets is not None:h.guard.scripts=assets
    await h.collect()
    assert h.files['wire-observation.json']['status']=='UNKNOWN','UNSUPPORTED_SOURCE_MARKED_CURRENT_CODE_CONFIRMED'
    assert h.guard.policy.sample_order is None and len(h.guard.policy.business)==6
    assert len(h.calls)==6 and 'sample' not in h.result
    assert 'AVAILABLE' not in json.dumps(h.result) and 'KNOWN_EMPTY' not in json.dumps(h.result)
    return summary(h)


async def r2_computed_field():
    return await unknown_case(VALID.replace(b'ocr_result:payload.data.ocr_result',b'ocr_result:payload.data.success'))
async def r2_caller_shadow():
    return await unknown_case(VALID.replace(b'async function readSet(b,n)',b'async function readSet(frameRead,n)')
        .replace(b'frameRead(b,n)',b'frameRead(frameRead,n)').replace(b'infoRead(b,n)',b'infoRead(frameRead,n)')
        .replace(b'bodyRead(b,n,',b'bodyRead(frameRead,n,'))
async def r2_cross_asset():
    pos=VALID.index(b'async function readSet')
    return await unknown_case(assets=[{'bytes':VALID[:pos],'ref':'GETTERS_ONLY.js','loaded_origin':{}},
        {'bytes':VALID[pos:],'ref':'CALLER_ONLY.js','loaded_origin':{}}])
async def r2_top_alias():
    return await unknown_case(b'const alias=fetch;\n'+VALID)
async def r2_reserved_getter():
    h=harness(INVALID);await h.collect()
    actual=summary(h)
    with (OUT/'reserved-getter-counterexample.actual.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(actual,stream,ensure_ascii=False,indent=2);stream.write('\n')
    assert h.files['wire-observation.json']['status']=='UNKNOWN','INVALID_JS_RESERVED_GETTER_AUTHORIZES_SAMPLE_READS'
    assert h.guard.policy.sample_order is None and len(h.calls)==6
    return actual


def image_bytes(fmt):
    raw=bytes((i*i+37*i+29)%256 for i in range(31*43*3))
    with Image.frombytes('RGB',(31,43),raw) as image:
        out=io.BytesIO();image.save(out,format=fmt);return out.getvalue()


async def r3_complete_decode_and_save():
    raw=image_bytes('JPEG');h=harness();url=policy.OSS+'/upload_images/46007447/independent-original.jpg'
    h.guard.policy.register_original(url,gate.BOOK,14,57,'CURRENT_SYNTHETIC_SOURCE')
    h.guard.cache[url]={'bytes':raw};saved=[]
    class MemoryFile:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def write(self,b):saved.append(b)
    with patch.object(probe.Path,'open',return_value=MemoryFile()):
        result=await probe.original_once(h.page,h.guard,{'url':url,'viewer':14,'resource_index':57})
    assert result['full_pixel_decode'] and (result['width'],result['height'])==(31,43)
    assert saved==[raw] and result['sha256']==hashlib.sha256(raw).hexdigest()
    assert ImageFile.LOAD_TRUNCATED_IMAGES is False
    png=decode.original_info(image_bytes('PNG'));assert png['full_pixel_decode']
    return {'jpeg':result,'png':png,'same_immutable_bytes_saved':True,'global_truncation_tolerance':False}


async def r3_truncated_before_save():
    raw=image_bytes('JPEG')[:-31]
    with Image.open(io.BytesIO(raw)) as image:assert image.size==(31,43)
    h=harness();url=policy.OSS+'/upload_images/46007447/independent-truncated.jpg'
    h.guard.policy.register_original(url,gate.BOOK,14,57,'CURRENT_SYNTHETIC_SOURCE');h.guard.cache[url]={'bytes':raw}
    with patch.object(probe.Path,'open',side_effect=AssertionError('NO_INVALID_IMAGE_SAVE')) as writer:
        try:await probe.original_once(h.page,h.guard,{'url':url,'viewer':14,'resource_index':57})
        except gate.Stop as error:assert str(error)=='ORIGINAL_IMAGE_REJECTED'
        else:raise AssertionError('TRUNCATED_JPEG_ACCEPTED')
        writer.assert_not_called()
    return {'header_readable':True,'bytes_sha256':hashlib.sha256(raw).hexdigest(),'saved':False,'retried':False}


def release_case(before,after,output=b''):
    it=iter([before,after]);saved={}
    class API:
        def held_identity(self,h):
            v=next(it)
            if isinstance(v,Exception):raise v
            return copy.deepcopy(v)
    class Handle:
        closed=False
        def __int__(self):return 99
        def Close(self):self.closed=True
    class Child:
        def __init__(self):self._handle=Handle();self.stdin=io.BytesIO();self.stdout=io.BytesIO();self.stderr=io.BytesIO()
        def poll(self):return 0
        def communicate(self,**kw):return output,b''
    class Job:
        closed=False
        def assign(self,c):pass
        def active(self):return 0
        def close(self):self.closed=True
    class Clock:
        value=70000
        def monotonic(self):self.value+=.01;return self.value
    child=Child();job=Job()
    with patch.object(probe,'load_native',return_value=(API,None)),patch.object(probe,'OwnedJob',return_value=job), \
        patch.object(probe.subprocess,'Popen',return_value=child),patch.object(probe,'time',Clock()), \
        patch.object(probe,'save_new',lambda p,v:saved.update(copy.deepcopy(v))):
        result=probe.supervise(['INDEPENDENT_MEMORY_ONLY'],Path('MEMORY_OUTPUT'),limit=20)
    assert child._handle.closed and job.closed and all(s.closed for s in [child.stdin,child.stdout,child.stderr])
    return result


def r4_identity_and_parent():
    good={'pid':19,'created_filetime':321};after={**good,'exit_observed':True,'exit_code':0}
    records=[]
    valid=release_case(good,after);assert valid['state']=='RELEASED' and probe.worker_succeeded(valid);records.append(valid)
    for invalid in [{**after,'pid':True},{**after,'created_filetime':0},{**after,'created_filetime':322},
        {k:v for k,v in after.items() if k!='created_filetime'},OSError('INDEPENDENT_AFTER_IDENTITY_FAILURE')]:
        value=release_case(good,invalid)
        assert value['state']=='UNKNOWN' and value['errors'] and not probe.worker_succeeded(value);records.append(value)
    bad_before=release_case(OSError('INDEPENDENT_BEFORE_IDENTITY_FAILURE'),after)
    assert bad_before['state']=='UNKNOWN' and not probe.worker_succeeded(bad_before);records.append(bad_before)
    worker_error=release_case(good,after,b'INDEPENDENT_WORKER_ERROR')
    assert worker_error['state']=='RELEASED' and worker_error['errors'] and not probe.worker_succeeded(worker_error)
    records.append(worker_error)
    return {'fake_native_records':records,'real_native_or_processes':False}


CASES=[('R1_CURRENT_FRAME_DATAFLOW',r1_current_binding),('R1_OPTIONAL_ZONE_MISSING',r1_optional_zone_presence),
    ('R1_IMAGE_DIGEST_CONFLICT',r1_source_digest_conflict),('R1_LATE_ANSWER_INVALIDATION',r1_late_answer_guard),
    ('R2_SUPPORTED_RELATION',r2_supported_relation),('R2_WRONG_RESPONSE_FIELD',r2_computed_field),
    ('R2_SHADOWED_CALLER',r2_caller_shadow),('R2_CROSS_ASSET',r2_cross_asset),('R2_TOP_ALIAS',r2_top_alias),
    ('R3_FULL_DECODE_SAME_SAVE',r3_complete_decode_and_save),('R3_TRUNCATED_BEFORE_SAVE',r3_truncated_before_save),
    ('R4_HELD_IDENTITY_AND_PARENT',r4_identity_and_parent),('R2_RESERVED_GETTER_SYNTAX',r2_reserved_getter)]
results=[];first=None
with patch.object(ctypes,'WinDLL',forbidden('NATIVE')),patch.object(subprocess,'Popen',forbidden('POPEN')), \
    patch.object(socket.socket,'connect',forbidden('SOCKET_CONNECT')),patch.object(socket.socket,'bind',forbidden('SOCKET_BIND')), \
    patch.object(probe.native,'profile_binding',forbidden('PROFILE')):
    for name,operation in CASES:
        if first:
            results.append({'case':name,'status':'NOT_RUN','reason':'FIRST_UNEXPECTED_FAILURE_STOP'});continue
        try:
            actual=asyncio.run(operation()) if asyncio.iscoroutinefunction(operation) else operation()
            results.append({'case':name,'status':'PASS','actual':actual})
        except BaseException as error:
            first={'case':name,'type':type(error).__name__,'detail':str(error)}
            results.append({'case':name,'status':'FAIL','failure':first})

record={'task':'A16','revision':'R01-R04','candidate_manifest_sha256':'071340237c76a7159bd90485e17a774c2f870114baef0199172a2fc5f9547efc',
    'result':'REWORK' if first else 'ALL_INDEPENDENT_CONTROLS_PASS','cases':results,'first_failure':first,
    'resource_attempts':ATTEMPTS,'duration_ms':round((time.monotonic()-START)*1000),
    'limits':'Only new frozen revision code; new revision harness transport/UI/file fakes; actual collect/binding/parser/decoder/supervisor paths.',
    'old_suite_or_old_candidate_executed':False,'real_browser_network_profile_native_or_occupancy':False}
with (OUT/'independent-controls-result.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(record,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({'result':record['result'],'statuses':{c['case']:c['status'] for c in results},
    'first_failure':first,'resource_attempts':ATTEMPTS,'duration_ms':record['duration_ms']}))
raise SystemExit(1 if first else 0)
