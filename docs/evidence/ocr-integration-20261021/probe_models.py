from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.metadata,io,json,socket,sys,time,zipfile
import numpy as np
from PIL import Image,ImageOps

HERE=Path(__file__).parent
REPO=HERE.parent/'textbook-annotation-assistant'
sys.path.insert(0,str(REPO/'src'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def blocked(*a,**k):raise RuntimeError('NETWORK_DISABLED_MODEL_AUDIT')
socket.create_connection=blocked;socket.getaddrinfo=blocked
socket.socket.connect=blocked;socket.socket.connect_ex=blocked
def default(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
p=argparse.ArgumentParser();p.add_argument('mode',choices=['text','formula']);args=p.parse_args()
package=REPO/'handoffs/b/46007447/B-46007447-observed-eight-sources-v2-PARTIAL-2026-10-17.zip'
assert sha(package.read_bytes())=='ec77d52ebcf25b3fec64579f63400c010cc08a623d71e20506e6ed46125ea695'
member='assets/46007447_page_14.jpg' if args.mode=='text' else 'assets/46007447_viewer_173.jpg'
with zipfile.ZipFile(package) as z:raw=z.read(member)
image=Image.open(io.BytesIO(raw)).convert('RGB')
box=[627,120,1142,348] if args.mode=='text' else [727,337,764,364]
crop=image.crop(box);input_rgb_sha=sha(crop.tobytes())
receipt=dict(recorded_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),mode=args.mode,python=sys.version,
 source_member=member,source_sha256=sha(raw),source_size=list(image.size),bbox=box,crop_rgb_sha256=input_rgb_sha,
 network_disabled=True,paid_api_calls=0,downloads=0,inference_calls=0,independent_human_accepted=False,decision='HOLD')
started=time.perf_counter()
if args.mode=='text':
 from annotation.recognition.inline_ocr import _cpu_backend
 engine,backend=_cpu_backend()
 receipt['adapter']='annotation.recognition.inline_ocr._cpu_backend'
 receipt['initialization_seconds']=time.perf_counter()-started
 started=time.perf_counter();result,elapsed=engine(np.array(crop)[:,:,::-1].copy(),use_det=True,use_cls=False,use_rec=True)
 assert result and len(result)>0
 receipt.update(backend=backend,raw_result=result,backend_elapsed=elapsed,inference_calls=1,recognized_regions=len(result))
else:
 from annotation.recognition.formula_backend import _local_cpu_backend
 engine,backend=_local_cpu_backend(HERE.parent/'latex-range-models')
 receipt['adapter']='annotation.recognition.formula_backend._local_cpu_backend'
 receipt['initialization_seconds']=time.perf_counter()-started
 crop=ImageOps.expand(crop,border=2,fill='white');crop=crop.resize((crop.width*3,crop.height*3),Image.Resampling.LANCZOS)
 receipt['input_transform']=dict(padding=2,scale=3,resampling='PIL_LANCZOS',rgb_sha256=sha(crop.tobytes()))
 started=time.perf_counter();result,elapsed=engine(np.array(crop))
 assert isinstance(result,str) and result.strip()
 receipt.update(backend=backend,raw_result=result,backend_elapsed=elapsed,inference_calls=1)
receipt.update(call_wall_seconds=time.perf_counter()-started,status='EXISTING_LOCAL_ADAPTER_CPU_CALL_OK',
 scope='Backend availability only; raw output is unverified, not formula accuracy or chapter acceptance.')
(HERE/(args.mode+'-probe.json')).write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2,default=default)+'\n').encode('utf-8'))
print(json.dumps({k:receipt[k] for k in ('mode','status','inference_calls','call_wall_seconds','decision')}))
