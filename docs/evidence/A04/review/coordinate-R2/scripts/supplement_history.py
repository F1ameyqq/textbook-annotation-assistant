"""Add only exact frozen A05 files referenced by a historical offline test."""
import hashlib,io,json,subprocess,tarfile
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];F=Path('D:/1800/.local/stages/A04-review/coordinate-R2/frozen source with spaces')
repo='C:/Users/ASUS/.codex/worktrees/a04-headless-readonly/1800';target='76898657e76ac2db071327e90c6ca5031d17571f'
names=['reopen-book.json','source-metadata.json','reopen-directory.json','reopen-annotations.json','source-viewer14.jpg','source-viewer173.jpg']
paths=['docs/evidence/A05/execution/'+n for n in names]
b=subprocess.check_output(['git','-C',repo,'archive','--format=tar.gz',target,*paths])
(OUT/'inputs/historical-test-supplement.tar.gz').write_bytes(b);rows=[]
with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as t:
    for m in t.getmembers():
        p=F/m.name
        if m.isdir():p.mkdir(parents=True,exist_ok=True);continue
        assert m.isfile() and not p.exists();data=t.extractfile(m).read();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        rows.append({'path':m.name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(OUT/'inputs/history-supplement-manifest.json').write_text(json.dumps({'target_commit':target,'files':rows,'archive_sha256':hashlib.sha256(b).hexdigest(),'purpose':'Historical A05 replay test only; no current book observation'},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'files':len(rows),'bytes':len(b)}))
