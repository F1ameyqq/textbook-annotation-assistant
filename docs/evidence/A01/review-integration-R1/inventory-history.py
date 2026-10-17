import hashlib,json
from pathlib import Path
root=Path('D:/1800');out=root/'docs/evidence/A01/review-integration-R1'
paths=set((root/'docs/evidence/A01').rglob('*'))|set((root/'docs/tasks').glob('A01*.md'))
rows=[]
for path in sorted(paths):
 if path.is_file() and out not in path.parents:
  data=path.read_bytes();rows.append(dict(path=path.relative_to(root).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
with (out/'historical-before.json').open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(dict(note='Supplemental inventory including ignored logs; captured during read-only setup. No old material has been written by this review.',files=rows),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(files=len(rows))))
