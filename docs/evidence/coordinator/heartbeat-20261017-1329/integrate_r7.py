"""Scoped raw-byte R7 integration; never merges the unaccepted A03 ancestry."""
import hashlib
import io
import json
from pathlib import Path
import subprocess

root=Path('D:/1800'); out=Path(__file__).resolve().parent
base='81d3ec7e42e0a1a76ad744bf59536fc5f68adee4'; target='8ad45dd07214ae406a3fab28d76a4b5abd6eef03'
def git(*args): return subprocess.check_output(['git',*args],cwd=root)
def sha(b): return hashlib.sha256(b).hexdigest()
rows=[r.split('\t') for r in git('diff','--name-status',base,target).decode().splitlines()]
allowed=('src/annotation/contracts/a03_bridge/','tests/fixtures/a03/P2-R7-readonly-codec/','examples/a03/P2-R7-readonly-codec/','docs/evidence/A03/execution/P2-R7-readonly-codec/')
singles={'tests/test_a03_r7_readonly_codec.py','docs/tasks/A03-P2-R7-readonly-codec-delivery.md'}
added=[]
for status,path in rows:
    if status=='M': assert path=='pyproject.toml'
    else:
        assert status=='A' and (path.startswith(allowed) or path in singles),path
        assert not (root/path).exists(),path
        added.append(path)
assert len(added)==339 and len(rows)==340
old_project=(root/'pyproject.toml').read_bytes()
before=git('show',base+':pyproject.toml'); after=git('show',target+':pyproject.toml')
assert after.startswith(before)
append=after[len(before):]
assert append.decode().strip()=='[tool.setuptools.package-data]\n"annotation.contracts.a03_bridge" = ["data/*.json", "data/schemas/*.json"]'
assert b'Pillow==11.3.0' in old_project and b'[tool.setuptools.package-data]' not in old_project
requests='\n'.join(target+':'+p for p in added)+'\n'
r=subprocess.run(['git','cat-file','--batch'],input=requests.encode(),cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,check=True)
stream=io.BytesIO(r.stdout); files=[]; content=[]
for path in added:
    head=stream.readline().decode().split(); assert head[1]=='blob'
    b=stream.read(int(head[2])); assert stream.read(1)==b'\n'
    files.append(dict(path=path,bytes=len(b),sha256=sha(b),source_blob=head[0]));content.append((path,b))
assert not stream.read()
for path,b in content:
    dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(b)
newline=b'\r\n' if b'\r\n' in old_project else b'\n'
final_project=old_project+append.replace(b'\n',newline)
(root/'pyproject.toml').write_bytes(final_project)
for row in files: assert sha((root/row['path']).read_bytes())==row['sha256']
result=dict(status='COPIED_PENDING_INTEGRATION_TESTS',source_base=base,source_target=target,root_parent=git('rev-parse','HEAD').decode().strip(),files=files,pyproject=dict(before_sha256=sha(old_project),after_sha256=sha(final_project),append_utf8=append.decode(),preserved_dependency='Pillow==11.3.0'),unaccepted_runtime_ancestry_imported=False,remote_push=False)
(out/'integration-files.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],new_files=len(files),old_files_modified=['pyproject.toml'])))
