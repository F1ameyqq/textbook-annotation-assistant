"""Finite retained source-region consumption; ordinary OCR is never TeX cache."""
from __future__ import annotations
import json
from pathlib import Path
from .store import Hold,byte_hash,digest

APP=Path(__file__).resolve().parents[3]


def bootstrap(store,book):
    directory=APP/'runtime/customer-formula-history'/book
    index=directory/'registry.json'
    if not index.is_file():return
    raw=index.read_bytes();value=json.loads(raw)
    if value.get('schema')!='CustomerConsumedSourceRegions/v1' or value.get('book_id')!=book:
        raise Hold('历史区域索引身份不一致。')
    files={}
    for row in value['evidence_files']:
        path=(directory/row['filename']).resolve()
        if (not path.is_relative_to(directory.resolve()) or not path.is_file()
            or byte_hash(path.read_bytes())!=row['sha256'] or path.stat().st_size!=row['bytes']):
            raise Hold('历史区域原记录已改变，不启动公式识别。')
        files[row['sha256']]=row
    for row in value['regions']:
        if (len(row.get('source_sha256',''))!=64 or type(row.get('bbox')) is not list or len(row['bbox'])!=4
            or not all(type(n) is int for n in row['bbox']) or not 0<=row['bbox'][0]<row['bbox'][2]
            or not 0<=row['bbox'][1]<row['bbox'][3] or not row.get('evidence_sha256')
            or any(reference not in files for reference in row['evidence_sha256'])
            or row.get('consumed') is not True or row.get('tex_cache') is not False):
            raise Hold('历史区域记录缺少来源或消耗身份。')
        key=digest([book,row['source_sha256'],row['bbox']]);kind='consumed-source-region:'+book
        old=store.operation(kind,key)
        if old:
            if old['state']!='COMPLETE' or store.get(old['output'])!=row:
                raise Hold('历史区域保护已有不同记录，不能覆盖或重跑。')
        else:store.record_read(kind,key,row)


def guard(store,book,source_sha256,bbox):
    bootstrap(store,book)
    with store.connect() as db:
        rows=db.execute('SELECT state,output FROM operations WHERE kind=?',('consumed-source-region:'+book,)).fetchall()
    for state,reference in rows:
        if state!='COMPLETE' or reference is None:raise Hold('历史区域保护状态未知，先保留记录。')
        row=store.get(reference)
        if row['source_sha256']!=source_sha256:continue
        old=row['bbox']
        if max(old[0],bbox[0])<min(old[2],bbox[2]) and max(old[1],bbox[1])<min(old[3],bbox[3]):
            raise Hold('此范围与已执行的历史识别区域重叠，保留原观察或失败，不换模型重跑。')
