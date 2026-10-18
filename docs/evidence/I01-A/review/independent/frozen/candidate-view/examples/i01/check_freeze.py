"""Check fixed package bytes without importing products or opening any DB."""
import argparse
from support import ROOT, EVIDENCE, git, load, sha, write

parser=argparse.ArgumentParser();parser.add_argument('--candidate',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
items=load(EVIDENCE/'preparation/identity.json')['inputs']
rows=[]
for item in items:
    actual=sha(git(['show',args.candidate+':'+item['path']]))
    rows.append(dict(path=item['path'],expected_sha256=item['sha256'],git_sha256=actual,match=actual==item['sha256']))
write(args.output,dict(candidate=args.candidate,files=rows,mismatches=[r for r in rows if not r['match']],
    target_creations=0,dispatches=0,public_consumptions=0,product_imports=0,SQL=0))
print('mismatches='+str(sum(not r['match'] for r in rows)))
