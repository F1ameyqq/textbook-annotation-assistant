"""Final static pre-seal child. Parent records its exit, then seals all files."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
verification=json.loads((OUT/'delivery-verification.json').read_bytes())
assert verification['changed_old_files']==0 and verification['static_records']==36
assert not (OUT/'sha256-manifest.json').exists()
for run in (OUT/'runs').iterdir():
    if (run/'exit.json').exists():
        value=json.loads((run/'exit.json').read_bytes());assert not value['owned_child_alive']
print(json.dumps({'status':'PREPARED_STATIC_SEAL','product_runs':0,'native_sessions':0,'manifest_written_by_parent_only_after_child_exit':True}))
