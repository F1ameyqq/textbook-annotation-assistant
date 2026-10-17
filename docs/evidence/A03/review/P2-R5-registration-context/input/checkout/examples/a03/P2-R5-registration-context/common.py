"""R5 file helpers only; no checker or product imports."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];EX=Path(__file__).resolve().parent
OUT=ROOT/'docs/evidence/A03/execution/P2-R5-registration-context'
BASE='e608b54b973b14ff55dd2c4530153f5fe7c931f4'
WORKFLOW='5fcb2e0084c92c20092cac19e33619128ad86d54'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
def h(v):return sha(canon(v))
def load(p):return json.loads(p.read_bytes())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
def raw_write(p,raw):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb')as f:f.write(raw)
def git(*a):return subprocess.check_output(['git','-c','core.longpaths=true',*a],cwd=ROOT)
def ref(a):return{k:a[k]for k in('artifact_id','revision','kind','content_hash')}
def isres(v):return isinstance(v,dict)and{'path','sha256','media_type'}<=set(v)
