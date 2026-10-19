"""Read-only raw Git publication integrity; standard library, no product execution."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ref',default='HEAD')
parser.add_argument('--repository',default=None)
args=parser.parse_args()
root=Path(args.repository) if args.repository else Path(__file__).resolve().parents[3]
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
def git(*a,data=None):
    return subprocess.run(['git','-c','core.longpaths=true',*a],cwd=root,env=env,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
ref=git('rev-parse','--verify',args.ref+'^{tree}').decode().strip()
cache={}
def blob(p):
    if p not in cache:cache[p]=git('cat-file','blob',ref+':'+p)
    return cache[p]
manifest=json.loads(blob('docs/handoff/a08-a09-q4/manifest.json'))
members=manifest['source_members']+manifest['generated_members']
paths=[m['path'] for m in members]
assert len(set(paths))==len(paths)
raw=git('cat-file','--batch',data=''.join(ref+':'+p+'\n' for p in paths).encode());i=0
for p in paths:
    end=raw.index(b'\n',i);h=raw[i:end].split();assert h[1]==b'blob';n=int(h[2]);cache[p]=raw[end+1:end+1+n];i=end+n+2
assert i==len(raw)
for m in members:
    raw=blob(m['path']);assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256'],m['path']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==m['blob_oid'],m['path']
count=0
for f in manifest['frozen_delivery_manifests']:
    frozen=json.loads(blob(f));entries=frozen.get('members',frozen.get('entries'))
    assert entries is not None
    for m in entries:
        raw=blob(m['path']);assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256'],(f,m['path']);count+=1
print(json.dumps({'result':'PASS_PUBLICATION_INTEGRITY_ONLY','tree':ref,'publication_members':len(members),'frozen_manifest_members':count,'new_business_runs':0,'platform_actions':0}))
