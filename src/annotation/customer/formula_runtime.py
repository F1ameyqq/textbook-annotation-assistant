"""One local source-bound formula crop through the retained owned runtime.

Building a request only reads local bytes. The durable ROI gate checks cache and
prior failures before the worker can be launched or a model can be imported.
"""
from __future__ import annotations

import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path

from .formula_roi_cache import build_request, obtain_candidate, MODEL_FILES, KIND
from .store import Hold, byte_hash, encoded

APP = Path(__file__).resolve().parents[3]
DEPENDENCIES = ('rapid-latex-ocr','onnxruntime','numpy','Pillow','tokenizers','opencv-python','PyYAML','chardet')
CONFIGURATION = {'source_mode':'ORIGINAL_RGB_SINGLE_ROI', 'backend_entry':'LaTeXOCR.__call__',
                 'maximum_decode_tokens':128, 'temperature':0.00001, 'alternate_variants':0}


def _need(condition, message):
    if not condition:
        raise Hold(message)


def _path(value):
    return Path(value['path'] if isinstance(value,dict) else value).resolve()


def local_identity(settings):
    runtime=settings.get('runtime',{})
    python=_path(runtime['formula_python'])
    site=python.parent.parent/'Lib/site-packages'
    model_spec=runtime.get('formula_models',str(site/'rapid_latex_ocr/models'))
    model_dir=Path(model_spec['directory']).resolve() if isinstance(model_spec,dict) else _path(model_spec)
    package=site/'rapid_latex_ocr'
    versions={d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions(path=[str(site)])}
    dependencies={name:versions[name.lower().replace('_','-')] for name in DEPENDENCIES}
    _need(dependencies['rapid-latex-ocr']=='0.0.9','本地公式识别器版本不符。')
    code={str(path.relative_to(APP)).replace('\\','/'):byte_hash(path.read_bytes()) for path in
          [APP/'src/annotation/customer/formula_runtime.py', APP/'tools/customer_formula_worker.py',
           APP/'src/annotation/recognition/formula_backend.py']}
    code.update({'rapid_latex_ocr/'+name:byte_hash((package/name).read_bytes()) for name in
                 ('main.py','models.py','utils.py','utils_load.py','config.yaml')})
    files=[{'name':name,'bytes':(model_dir/name).stat().st_size,'sha256':byte_hash((model_dir/name).read_bytes())} for name in sorted(MODEL_FILES)]
    if isinstance(model_spec,dict):
        declared={row['name']:row['sha256'] for row in model_spec.get('assets',[])}
        _need(declared=={row['name']:row['sha256'] for row in files},'随包公式模型与原文件身份不一致。')
    identity={'backend':'rapid-latex-ocr','version':'0.0.9','files':files,'code_sha256':code,
              'runtime':{'python_sha256':byte_hash(python.read_bytes()),'dependencies':dependencies},
              'configuration':CONFIGURATION.copy()}
    return identity,python,model_dir


def request_for_region(page, book, bbox, settings):
    from PIL import Image
    raw=Path(page['raw_path']).read_bytes()
    _need(page['kind']=='image' and byte_hash(raw)==page['raw_sha256'],'公式来源原图已改变。')
    with Image.open(io.BytesIO(raw)) as original:
        _need(original.size==(page['width'],page['height']),'公式来源尺寸已改变。')
        _need(type(bbox) is list and len(bbox)==4 and all(type(x) is int for x in bbox)
              and 0<=bbox[0]<bbox[2]<=original.width and 0<=bbox[1]<bbox[3]<=original.height,
              '请在原图内选择一个公式区域。')
        crop=original.convert('RGB').crop(tuple(bbox))
        buffer=io.BytesIO();crop.save(buffer,format='PNG',compress_level=9,optimize=False)
        crop_bytes=buffer.getvalue();rgb=crop.tobytes()
    model,python,model_dir=local_identity(settings)
    source={'book_id':book,'asset_id':page['asset_id'],'sha256':page['raw_sha256'],'width':page['width'],'height':page['height']}
    return build_request(source,bbox,crop_bytes,rgb,model),crop_bytes,python,model_dir


def obtain_region(store, page, book, bbox, settings, *, allow_first_local_call=False):
    from .formula_history import guard
    guard(store,book,page['raw_sha256'],bbox)
    request,roi_bytes,python,model_dir=request_for_region(page,book,bbox,settings)
    # A shifted/expanded crop must not bypass a consumed logical region. This
    # also holds new regions while an interrupted ROI has no retained binding.
    with store.connect() as db:
        prior=db.execute('SELECT key,state,output FROM operations WHERE kind=?',(KIND,)).fetchall()
    for key,state,output in prior:
        if key==request['roi_key']:
            continue  # The exact cache gate below handles COMPLETE/FAIL/INTENT.
        _need(output is not None,'已有公式识别中断，先核对原记录；不能换区域重跑。')
        saved=store.get(output)['request']['roi_identity']
        if saved['book_id']==book and saved['source_sha256']==page['raw_sha256']:
            old=saved['source_bbox']
            _need(max(old[0],bbox[0])>=min(old[2],bbox[2]) or max(old[1],bbox[1])>=min(old[3],bbox[3]),
                  '这个区域与已识别或失败区域重叠；使用原记录，不会换裁剪重跑。')

    def run_once(bound_request):
        directory=store.root/'formula-roi'/bound_request['roi_key']
        directory.mkdir(parents=True,exist_ok=False)
        roi_path=directory/'original-roi.png'
        with roi_path.open('xb') as stream:stream.write(roi_bytes)
        envelope={'schema':'CustomerFormulaWorkerInput/v1','request':bound_request,
                  'source_path':str(Path(page['raw_path']).resolve()),'roi_path':str(roi_path),
                  'model_directory':str(model_dir),'python_executable':str(python)}
        input_path=directory/'request.json'
        with input_path.open('xb') as stream:stream.write(encoded(envelope))
        worker=APP/'tools/customer_formula_worker.py'
        command=[str(python),'-I','-B',str(worker),'--input',str(input_path),'--sha256',byte_hash(input_path.read_bytes())]
        spec=importlib.util.spec_from_file_location('customer_formula_owned_process',APP/'tools/owned_process.py')
        holder=importlib.util.module_from_spec(spec);spec.loader.exec_module(holder)
        result=holder.run(command,APP,directory/'worker',180)
        _need(result.get('owned_os_release_confirmed') is True and result.get('exit_code')==0,
              '本次公式识别失败或释放未证；保留记录，不会再次识别此区域。')
        process=directory/'worker.process.json';stdout=directory/'worker.stdout'
        process_value=json.loads(process.read_bytes())
        _need(byte_hash(stdout.read_bytes())==process_value['stdout']['sha256'],'公式进程原输出已改变。')
        observation=json.loads(stdout.read_text(encoding='utf-8').strip().splitlines()[-1])
        observation.update(owned_os_release_confirmed=True,
            raw_record={'path':str(stdout),'sha256':byte_hash(stdout.read_bytes()),
                        'process_path':str(process),'process_sha256':byte_hash(process.read_bytes())})
        return observation

    enabled=allow_first_local_call is True and settings.get('runtime',{}).get('formula_inference_activated') is True
    if not enabled and store.operation(KIND,request['roi_key']) is None:
        raise Hold('本地公式识别尚未启用，保留当前材料；不会开始模型调用。')
    return obtain_candidate(store,request,allow_first_local_call=enabled,run_once=run_once)
