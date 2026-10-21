"""Retain exact local library source evidence only; no browser or network."""
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/evidence/A24/route-callback-minimum"
LOCAL=Path("D:/1800/.local/stages/a24-route-callback-library-evidence")
LIB=Path(sys.executable).parent/"Lib/site-packages/playwright"
OUT.mkdir(parents=True,exist_ok=False)
LOCAL.mkdir(parents=True,exist_ok=False)
records=[]
for name in ("_impl/_helper.py","_impl/_impl_to_api_mapping.py","_impl/_browser_context.py","async_api/_generated.py"):
    source=LIB/name;raw=source.read_bytes();dest=LOCAL/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as handle:handle.write(raw)
    records.append({"path":str(source),"private_fixed_copy":str(dest),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
value={"schema":"A24RouteCallbackLocalLibraryEvidence/v1","python":sys.version.split()[0],"python_executable":sys.executable,
    "playwright_version":version("playwright"),"sources":records,"source_copies_private_only":True,"browser_or_network_created":False,
    "dispatch_contract":"RouteHandler invokes handler(route,route.request); ImplToApiMapping.wrap_handler truncates using len(inspect.signature(handler).parameters)",
    "observed_old_signature":"bound tracked(*args,**kwargs) has two parameters","corrected_signature":"functools.wraps restores bound route(route) signature",
    "whole_environment_or_browser_binary_rebuilt_or_fully_hashed":False}
with (OUT/"library-provenance.json").open("xb") as handle:handle.write((json.dumps(value,indent=2)+"\n").encode())
task=Path("D:/1800/docs/tasks/A24-route-callback-minimum-correction-continuation.md")
with (OUT/"task.md").open("xb") as handle:handle.write(task.read_bytes())
print(json.dumps({"playwright_version":value["playwright_version"],"source_files":len(records),"python":value["python"],"actual_resources":0}))
