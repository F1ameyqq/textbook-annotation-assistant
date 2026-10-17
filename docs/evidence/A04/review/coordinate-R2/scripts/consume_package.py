"""Independent public loader + actual full decode from a different cwd."""
import hashlib,json,sys
from pathlib import Path
from PIL import Image
from annotation.contracts import load_bundle
package=Path(sys.argv[1]);bundle=load_bundle(package/'bundle.json')
source=next(a for a in bundle.artifacts if a.kind=='SourceBundle');rows=[]
for asset in source.payload.assets:
    path=package/asset.path;blob=path.read_bytes()
    assert not Path(asset.path).is_absolute() and hashlib.sha256(blob).hexdigest()==asset.sha256
    with Image.open(path) as image:
        fmt=image.format
        for frame in range(getattr(image,'n_frames',1)):image.seek(frame);image.load()
        assert image.size==(asset.width,asset.height)
    rows.append({'path':asset.path,'sha256':asset.sha256,'size':[asset.width,asset.height],
      'media_type':asset.media_type,'decoded_format':fmt,'full_decode':'PASS'})
assert len(source.payload.pages_acquired)==3
print(json.dumps({'public_loader':'PASS','asset_count':len(rows),'assets':rows}))
