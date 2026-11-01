"""Import existing raw B observations; never rerun models to migrate a cache."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import zipfile
from .store import Hold, byte_hash, digest


def import_evidence(store, path, *, member=None):
    from annotation.recognition.baseline import digest as b_digest
    from .source import validate_lines
    path = Path(path).resolve(); outer = path.read_bytes()
    if member is not None:
        with zipfile.ZipFile(path) as archive: raw = archive.read(member)
    else: raw = outer
    value = json.loads(raw)
    if value.get('schema_version')=='b-continuation-fixture-trial/0.1':
        require_payload=value.get('payload',{})
        if value.get('content_hash')!=b_digest(require_payload) or value.get('producer',{}).get('module')!='rapidocr_onnxruntime.RapidOCR':
            raise Hold('历史局部 OCR 原件摘要或来源不一致。')
        source=require_payload['source'];crop=require_payload['crop'];lines=require_payload['ocr_lines']
        validate_lines(lines,source['width'],source['height'])
        key=digest([value['book_id'],source['sha256']])
        record={'book_id':value['book_id'],'source':copy.deepcopy(source),'crop':copy.deepcopy(crop),'lines':copy.deepcopy(lines),
            'coverage':'CROP_ONLY','provenance':{'path':str(path),'archive_sha256':byte_hash(outer),'raw_sha256':byte_hash(raw),'member':member},
            'new_model_calls':0,'content_approved':False}
        old=store.operation('historic-partial-recognition',key)
        if old:
            retained=store.get(old['output']) if old['state']=='COMPLETE' else None
            equivalent=retained is not None and {k:v for k,v in retained.items() if k!='provenance'}=={k:v for k,v in record.items() if k!='provenance'} and retained['provenance']['raw_sha256']==record['provenance']['raw_sha256']
            if not equivalent:raise Hold('历史局部 OCR 已有不同原记录。')
        else:
            store.begin('historic-partial-recognition',key);store.finish('historic-partial-recognition',key,'COMPLETE',record)
        return {'book_id':value['book_id'],'coverage':'CROP_ONLY','source_sha256':source['sha256'],'lines':len(lines),'new_model_calls':0}
    if value.get('schema_version') not in ('b-evidence-trial/0.1','b-evidence-trial/0.2') or value.get('content_hash') != b_digest(value.get('payload')):
        raise Hold('旧识别原件类型或内容摘要不一致。')
    producer = value.get('producer', {}); baseline = producer.get('baseline_producer', producer)
    if baseline.get('ocr_enabled') is not True: raise Hold('该旧证据没有实际 OCR 标记，不能冒充识别缓存。')
    book = value['book_id']; imported = []
    provenance = {'path': str(path), 'archive_sha256': byte_hash(outer), 'member': member,
                  'raw_sha256': byte_hash(raw), 'producer': producer, 'artifact_id': value['artifact_id'],
                  'content_hash': value['content_hash'], 'new_model_calls': 0}
    for page in value['payload']['pages']:
        source = page['source']; lines = page['ocr_lines']; details = page.get('answer_detail_lines', [])
        validate_lines(lines, source['width'], source['height'])
        if details: validate_lines(details, source['width'], source['height'])
        key = digest([book, source['sha256']]); old = store.operation('historic-recognition', key)
        record = {'book_id': book, 'raw_sha256': source['sha256'], 'width': source['width'], 'height': source['height'],
                  'lines': copy.deepcopy(lines), 'detail_lines': copy.deepcopy(details), 'provenance': provenance,
                  'verification_status': 'UNVERIFIED_OBSERVATION', 'content_approved': False}
        if old:
            retained=store.get(old['output']) if old['state']=='COMPLETE' else None
            equivalent=retained is not None and {k:v for k,v in retained.items() if k!='provenance'}=={k:v for k,v in record.items() if k!='provenance'} and retained['provenance']['raw_sha256']==record['provenance']['raw_sha256']
            if not equivalent:
                raise Hold('同源旧缓存有不同原记录，保留两者并先核对；不覆盖或重识别。')
        else:
            store.begin('historic-recognition', key); store.finish('historic-recognition', key, 'COMPLETE', record)
        imported.append({'source_sha256': source['sha256'], 'lines': len(lines), 'detail_lines': len(details)})
    return {'book_id': book, 'imported': imported, 'provenance': provenance, 'new_model_calls': 0}


def bootstrap(store,book):
    """One-time packaged migration; no per-lesson cache-file selection."""
    directory=Path(__file__).resolve().parents[3]/'runtime/customer-recognition'/book
    index=directory/'registry.json'
    if not index.is_file():return
    raw=index.read_bytes();value=json.loads(raw);key=digest([book,byte_hash(raw)])
    old=store.operation('recognition-migration',key)
    if old:
        if old['state']!='COMPLETE':raise Hold('旧识别迁移有失败记录；保留原件，不重新识别。')
        return
    if value.get('book_id')!=book:raise Hold('识别缓存索引书籍不一致。')
    paths=[]
    for row in value['files']:
        path=(directory/row['filename']).resolve()
        if not path.is_relative_to(directory.resolve()) or byte_hash(path.read_bytes())!=row['sha256']:raise Hold('随包旧识别原件已改变。')
        paths.append((path,row.get('member')))
    store.begin('recognition-migration',key)
    try:
        result=[import_evidence(store,path,member=member) for path,member in paths]
        store.finish('recognition-migration',key,'COMPLETE',{'results':result,'new_model_calls':0})
    except BaseException as exc:
        store.finish('recognition-migration',key,'FAILED_NO_RETRY',{'type':type(exc).__name__,'message':str(exc)})
        raise


def cached_page(store, page, book):
    old = store.operation('historic-recognition', digest([book, page['raw_sha256']]))
    if old is None: return None
    if old['state'] != 'COMPLETE': raise Hold('旧识别状态未知，不能再跑同源输入。')
    record = store.get(old['output'])
    if record['raw_sha256'] != page['raw_sha256'] or [record['width'],record['height']] != [page['width'],page['height']]:
        raise Hold('旧识别来源身份不一致。')
    provenance = record['provenance']; original = Path(provenance['path'])
    if byte_hash(original.read_bytes()) != provenance['archive_sha256']: raise Hold('旧缓存原件已改变。')
    return copy.deepcopy(record)
