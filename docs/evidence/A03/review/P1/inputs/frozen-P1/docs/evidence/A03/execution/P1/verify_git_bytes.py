"""Verify exact Git-delivered P1 bytes; offline packaging only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
WORKFLOW='a354f95f1d0b40a8f0847b57fa3978cac999e7a2'

def run(*args):return subprocess.check_output(['git',*args],cwd=str(ROOT))

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'HEAD'
    rows=[]
    if mode=='index':
        for raw in run('ls-files','-s','-z').split(b'\0'):
            if not raw:continue
            meta,name=raw.split(b'\t',1)
            path=name.decode('utf-8')
            if path.startswith('examples/a03/P1/') or path=='docs/a03-recovery-contract-v1-proposal.md':
                rows.append((path,meta.split()[1].decode('ascii')))
    else:
        for path in run('diff','--name-only',WORKFLOW,mode).decode('utf-8').splitlines():
            rows.append((path,run('rev-parse',mode+':'+path).decode('ascii').strip()))
    process=subprocess.run(['git','cat-file','--batch'],cwd=str(ROOT),
                           input=('\n'.join(oid for _,oid in rows)+'\n').encode('ascii'),
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    stream=process.stdout
    offset=0
    errors=[]
    for path,oid in rows:
        end=stream.index(b'\n',offset)
        actual_oid,kind,size=stream[offset:end].split()
        size=int(size)
        data=stream[end+1:end+1+size]
        offset=end+1+size+1
        local=ROOT/path
        if actual_oid.decode('ascii')!=oid or kind!=b'blob' or not local.is_file() or local.read_bytes()!=data:
            errors.append(path)
    print(json.dumps({'check_kind':'GIT_EXACT_BYTE_PACKAGING','revision':mode,
                      'files_checked':len(rows),'byte_mismatches':errors,'passed':not errors,
                      'recovery_function_executed':False},indent=2))
    return 0 if not errors else 1

if __name__=='__main__':sys.exit(main())
