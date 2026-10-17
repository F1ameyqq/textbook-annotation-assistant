# -*- coding: utf-8 -*-
"""Record actual frozen import locations without opening any state/target."""
import importlib,json,os,platform,sqlite3,sys
from pathlib import Path
root=Path('D:/1800/docs/evidence/A03/review/P2/input/checkout').resolve()
names=('annotation.contracts','annotation.contracts.recovery','annotation.delivery.planner','annotation.delivery.mock.persistent',
 'annotation.delivery.reconciler','annotation.runtime.storage','annotation.runtime.storage.holds','annotation.runtime.recovery','annotation.runtime.recovery.quality')
modules={n:str(Path(importlib.import_module(n).__file__).resolve()) for n in names}
assert all(Path(p).is_relative_to(root) for p in modules.values())
import pydantic
print(json.dumps({'pid':os.getpid(),'python':sys.version,'executable':sys.executable,'sqlite':sqlite3.sqlite_version,'pydantic':pydantic.__version__,
 'platform':platform.platform(),'imports':modules,'database_or_target_opened':False,'field_reset':'NOT_EXECUTED'}))
