"""Read-only shortest replay of frozen original or an exported R3 case."""
import argparse
import json
from pathlib import Path
import closure as c

p=argparse.ArgumentParser();p.add_argument('--case',default='original');p.add_argument('--expect',default='UNDECLARED_REFERENCE');args=p.parse_args()
if args.case=='original':
    directory=c.OUT/'inputs/counterexample';path=directory/'bundle.json';raw=path.read_bytes()
    assert c.sha(raw)=='b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653'
    description=json.loads((directory/'result.json').read_bytes());overrides={}
    for item in description['resource_overrides']:
        value=(directory/Path(item['file']).name).read_bytes();assert c.sha(value)==item['sha256'];overrides[item['logical']]=value
else:
    description=json.loads(Path(args.case).read_bytes());path=c.ROOT/description['bundle'];raw=path.read_bytes()
    assert c.sha(raw)==description['bundle_sha256'];overrides={}
    for item in description['resources']:
        value=(c.ROOT/item['file']).read_bytes();assert c.sha(value)==item['sha256'];overrides[item['logical']]=value
bundle=json.loads(raw);pkg=c.Package(bundle,overrides)
try:pkg.validate();actual='STATIC_ACCEPTED';error=None
except c.Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
receipt=[row for row in pkg.evidence_refs if row['kind']=='ExecutionReceipt'and row['schema_version']=='1.3.0-a03-static-proposal'and row['formal_path'].endswith('/results/0/before_evidence_refs')]
print(json.dumps({'entry':'closure.Package.validate','actual':actual,'expected':args.expect,'error':error,'bundle_sha256':c.sha(raw),
 'new_1_3_receipt_before_evidence_refs_observed':bool(receipt),'consumers_with_closure_faults':len(pkg.consumer_failures()),'native_qualification':False}))
raise SystemExit(0 if actual==args.expect else 1)
