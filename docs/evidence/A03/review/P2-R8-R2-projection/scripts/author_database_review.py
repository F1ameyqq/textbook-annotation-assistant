# -*- coding: utf-8 -*-
import json
from evidence import EV,author_read
from verify_case import verify_case
prefix=EV+'validation/native-r2-01/cases/N1/'
result=verify_case('author',author_read,prefix+'runtime/runtime.sqlite3',prefix+'target/target.sqlite3',True)
assert result['POST_HOLD_run_rows']==0
print(json.dumps({'status':result['status'],'author_artifacts':result['counts']['runtime']['artifacts'],'effects':result['effect_count'],
 'material_progress':len(result['material_progress']),'POST_HOLD_runs':result['POST_HOLD_run_rows'],'hold':result['book']['hold']}))
