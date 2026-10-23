"""Consume a local C01 bundle through independently pinned unmodified A24 code."""
import argparse,hashlib,importlib.abc,json,socket,sys
from pathlib import Path
A_COMMIT='c5aefbc8e995c410b3babf74a251f05a7724a1c2'
PINS_SHA='e52b3d88f344d7873859f609c78d41e6c5421ac6bb363c83e81061dcf772a006'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def strict(raw):
 def obj(pairs):
  value={}
  for key,item in pairs:
   if key in value:raise ValueError('DUPLICATE_JSON_KEY')
   value[key]=item
  return value
 return json.loads(raw,object_pairs_hook=obj,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def guard(event,args):
 if event in {'socket.connect','socket.connect_ex','socket.getaddrinfo','socket.gethostbyname','socket.sendto','socket.sendmsg','subprocess.Popen','os.system','os.posix_spawn','os.spawn','os.exec','os.fork','os.startfile','os.startfile/2'}:raise RuntimeError('LOCAL_C01_FORBIDDEN_IO:'+event)
class Imports(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('annotation.runtime','annotation.delivery','annotation.recognition','playwright','onnxruntime','torch','paddle','transformers')):raise ImportError('LOCAL_C01_BLOCKED_IMPORT:'+fullname)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('a-source','pins','bundle','out'):p.add_argument('--'+name,required=True)
 a=p.parse_args();raw=Path(a.pins).read_bytes();assert sha(raw)==PINS_SHA,'PINS_CHANGED';pins=strict(raw);assert pins['a_commit']==A_COMMIT and len(pins['members'])==50
 source=Path(a.a_source).resolve()
 for m in pins['members']:
  path=(source/m['path']).resolve();assert path.is_relative_to(source),'SOURCE_PATH_ESCAPE'
  raw=path.read_bytes();assert len(raw)==m['bytes'] and sha(raw)==m['sha256'],'A_SOURCE_CHANGED'
 sys.dont_write_bytecode=True;sys.addaudithook(guard);sys.meta_path.insert(0,Imports());sys.path.insert(0,str(source/'src'))
 from annotation.contracts import load_bundle
 import inspect
 assert Path(inspect.getfile(load_bundle)).resolve().is_relative_to(source/'src'),'WRONG_A_CONSUMER'
 path=Path(a.bundle).resolve();raw=path.read_bytes();original=strict(raw);value=load_bundle(path,verify_assets=True).model_dump(mode='json');assert canon(original)==canon(value),'COMPLETE_OBJECT_CHANGED'
 result={'status':'FIXED_A24_COMPLETE_C01_OBJECT_MATCH','a_commit':A_COMMIT,'source_files_verified':50,'bundle_sha256':sha(raw),'complete_object_sha256':sha(canon(value)),'platform_requests':0,'a_owner_acceptance':False,'human_acceptance':False,'full_object':value}
 with Path(a.out).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps({k:v for k,v in result.items() if k!='full_object'}));return 0
if __name__=='__main__':raise SystemExit(main())
