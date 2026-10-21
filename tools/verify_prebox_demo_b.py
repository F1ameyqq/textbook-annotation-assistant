"""Verify an extracted portable prebox demo and replay its draft lifecycle offline."""
from pathlib import Path, PurePosixPath
import argparse
import base64
import hashlib
import importlib.abc
import json
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();root=args.package.resolve()
    if args.out.exists():raise ValueError('请使用尚不存在的输出目录')
    digest=lambda raw:hashlib.sha256(raw).hexdigest()
    manifest=json.loads((root/'manifest.json').read_bytes())
    seen=set()
    for row in manifest['members']:
        name=row['path'];relative=PurePosixPath(name);target=(root/name).resolve()
        if relative.is_absolute()or'..'in relative.parts or'\\'in name or':'in name or name in seen or not target.is_relative_to(root):raise ValueError('清单路径无效')
        seen.add(name);raw=target.read_bytes()
        if len(raw)!=row['bytes']or digest(raw)!=row['sha256']:raise ValueError('成员摘要不一致：'+name)
    class NoModels(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0]in{'rapidocr_onnxruntime','rapid_latex_ocr','onnxruntime','paddle','torch','openai'}:raise RuntimeError('模型导入禁用')
    sys.meta_path.insert(0,NoModels())
    def guard(event,values):
        if event=='socket.connect':raise RuntimeError('出站网络禁用')
    sys.addaudithook(guard)
    sys.path.insert(0,str(root/'src'))
    from annotation.prebox.store import Workspace,encode
    import numpy,cv2,PIL
    workspace=Workspace(args.out/'original')
    files=[dict(name=p.name,data_base64=base64.b64encode(p.read_bytes()).decode('ascii'))for p in sorted((root/'examples').glob('*.jpg'))]
    if len(files)!=2:raise ValueError('需要两张固定示例')
    workspace.import_images(files,0);original=workspace.state()
    if encode(original['pages'])!=(root/'reference/initial-pages.json').read_bytes():raise ValueError('原图候选重建不同')
    import copy
    pages=[{k:copy.deepcopy(p[k])for k in('page_id','sha256','width','height','boxes')}for p in original['pages']]
    pages[0]['boxes'][0]['bbox'][0]+=1;pages[0]['boxes'][0]['kind']='stem'
    workspace.save(pages,1)
    document=workspace.export_document();(args.out/'adjusted-draft.json').write_bytes(encode(document))
    imported=Workspace(args.out/'imported');imported.import_document(document,0)
    restored=imported.export_document()
    for before,after in zip(document['pages'],restored['pages']):
        for key in('page_id','name','sha256','width','height','image_base64'):
            if before[key]!=after[key]:raise ValueError('JSON来源恢复不同')
        for a,b in zip(before['boxes'],after['boxes']):
            if any(a[key]!=b[key]for key in('box_id','kind','bbox','status'))or b['origin']!='IMPORTED_DRAFT':raise ValueError('JSON草稿恢复不同')
        if len(before['boxes'])!=len(after['boxes']):raise ValueError('JSON恢复漏框')
    workspace.restore(1,2)
    reopened=Workspace(args.out/'original').state()
    if reopened['pages']!=original['pages']or reopened['revision']!=3:raise ValueError('历史恢复/重开不同')
    receipt=dict(schema_version='b-prebox-demo-replay/0.1',manifest_members=len(seen),
        initial_counts=[len(p['boxes'])for p in original['pages']],source_shas=[p['sha256']for p in original['pages']],
        initial_candidate_bytes_match=True,saved=True,json_roundtrip=True,restore_reopen=True,
        models_disabled=True,outbound_network_disabled=True,new_ocr_calls=0,paid_calls=0,website_actions=0,
        dependencies=dict(numpy=numpy.__version__,opencv=cv2.__version__,Pillow=PIL.__version__),
        clean_dependency_installation=False,browser_test_in_replay=False,decision='HOLD',human_verified=False)
    (args.out/'receipt.json').write_bytes(encode(receipt));print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
