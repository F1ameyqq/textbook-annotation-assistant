"""Compare new P1-R1 package bytes with Git raw blobs, without archive filters."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
BASE='2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9'
EXACT={'docs/a03-recovery-contract-v1-r1-proposal.md','docs/tasks/A03-P1-R1-execution-report.md'}
PREFIX=('examples/a03/P1-R1/','docs/evidence/A03/execution/P1-R1/')

def git(*args):
    return subprocess.check_output(['git',*args],cwd=str(ROOT))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('revision',default='HEAD',nargs='?')
    args=parser.parse_args()
    rows=[]
    if args.revision=='index':
        for entry in git('ls-files','-s','-z').split(b'\0'):
            if entry:
                meta,name=entry.split(b'\t',1)
                name=name.decode('utf-8')
                if name in EXACT or name.startswith(PREFIX):
                    rows.append((name,meta.split()[1].decode('ascii')))
    else:
        for name in git('diff','--name-only',BASE,args.revision).decode('utf-8').splitlines():
            rows.append((name,git('rev-parse',args.revision+':'+name).decode('ascii').strip()))
    result=subprocess.run(['git','cat-file','--batch'],cwd=str(ROOT),check=True,
                          input=('\n'.join(oid for _,oid in rows)+'\n').encode('ascii'),
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    data=result.stdout
    pos=0
    errors=[]
    for name,oid in rows:
        end=data.index(b'\n',pos)
        actual,kind,size=data[pos:end].split()
        size=int(size)
        content=data[end+1:end+1+size]
        pos=end+1+size+1
        local=ROOT/name
        if (actual.decode('ascii')!=oid or kind!=b'blob' or not local.is_file()
                or local.read_bytes()!=content):
            errors.append(name)
    print(json.dumps({'check_kind':'P1_R1_GIT_RAW_BYTE_AUDIT','revision':args.revision,
                      'files_checked':len(rows),'byte_mismatches':errors,'passed':not errors,
                      'runtime_or_recovery_executed':False},indent=2))
    return 0 if not errors else 1

if __name__=='__main__':sys.exit(main())
