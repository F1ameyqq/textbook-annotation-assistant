"""Minimal offline acceptance-boundary reproduction. Exit 1 = defect present.

Usage requires a NEW output directory and raw frozen source/fixtures under --root.
No browser, login tool, platform request or product mutation is performed.
"""
import argparse,contextlib,hashlib,io,json,os,shutil,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);sys.dont_write_bytecode=True
sys.path.insert(0,str(a.root/'src'))
from PIL import Image
from annotation.source.usense.cli import main
from annotation.contracts import load_bundle
input_dir=a.output/'input';shutil.copytree(a.root/'tests/fixtures/a04/source',input_dir)
cap=json.loads((input_dir/'capture.json').read_text(encoding='utf-8'))
bad=b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+b'\x00\x00\x00\x04\x00\x00\x00\x03'
path=input_dir/cap['pages'][0]['asset_path'];path.write_bytes(bad)
decoder='NOT_REJECTED'
try:
    with Image.open(path) as image:image.load()
except Exception as error:decoder=type(error).__name__
output_dir=a.output/'output';buf=io.StringIO()
with contextlib.redirect_stdout(buf):rc=main(['offline','--input',str(input_dir),'--output',str(output_dir),'--as-of',cap['observed_at']])
public_loader_accepted=False;pages_acquired=None
if (output_dir/'bundle.json').exists():
    bundle=load_bundle(output_dir/'bundle.json');public_loader_accepted=True
    pages_acquired=len(bundle.artifacts[0].payload.pages_acquired)
r={'input_bytes':len(bad),'sha256':hashlib.sha256(bad).hexdigest(),'independent_decoder_error':decoder,
 'public_cli_returncode':rc,'public_cli_stdout':buf.getvalue(),
 'public_loader_accepted':public_loader_accepted,'pages_acquired':pages_acquired,
 'expected':'Resource rejected before publishing SourceBundle/PlatformSnapshot',
 'defect_reproduced':decoder!='NOT_REJECTED' and rc==0 and public_loader_accepted}
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r));raise SystemExit(1 if r['defect_reproduced'] else 0)
