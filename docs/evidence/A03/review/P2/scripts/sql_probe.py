# -*- coding: utf-8 -*-
"""Independent stdlib-only read-only SQLite inspection of this review's case."""
from pathlib import Path
import argparse,hashlib,json,sqlite3,sys,os
parser=argparse.ArgumentParser();parser.add_argument('case',type=Path);args=parser.parse_args()
case=args.case.resolve();allowed=Path('D:/1800/docs/evidence/A03/review/P2/cases').resolve()
assert case.is_relative_to(allowed)
result={'pid':os.getpid(),'python':sys.executable,'sqlite':sqlite3.sqlite_version,'inspection':'mode=ro; no annotation imports'}
for label,filename in [('runtime','runtime/runtime.sqlite3'),('target','target/target.sqlite3')]:
 p=case/filename;assert p.is_file()
 db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=1);db.row_factory=sqlite3.Row
 try:
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  rows={t:[dict(x) for x in db.execute('SELECT * FROM "'+t+'"')] for t in tables}
  result[label]={'path':str(p),'device':p.stat().st_dev,'inode':p.stat().st_ino,'application_id':db.execute('PRAGMA application_id').fetchone()[0],
   'user_version':db.execute('PRAGMA user_version').fetchone()[0],'tables':rows}
 finally:db.close()
state=json.loads(next(x['value'] for x in result['target']['tables']['meta'] if x['key']=='state'))
effects=[json.loads(x['body']) for x in result['target']['tables']['effects']]
business={k:state[k] for k in ('target','internal_bindings','frame_projections')}
result['independent']={'target_effect_count':sum(bool(x['mutated']) for x in effects),'target_dispatch_count':len(effects),
 'business_sha256':hashlib.sha256(json.dumps(business,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
 'business_projection':business,'target_read_sequence':state['read_sequence'],'target_effects':effects,
 'all_runtime_events':[json.loads(x['body']) for x in sorted(result['runtime']['tables']['events'],key=lambda x:(x['book'],x['sequence']))]}
print(json.dumps(result,ensure_ascii=False,sort_keys=True))
