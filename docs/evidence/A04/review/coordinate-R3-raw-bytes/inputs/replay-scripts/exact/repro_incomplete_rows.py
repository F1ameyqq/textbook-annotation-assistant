"""Minimal R2 offline reproduction. NEW output required; exit1=defect present."""
import argparse,contextlib,hashlib,io,json,os,shutil,struct,sys,zlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False);sys.dont_write_bytecode=True
os.environ['A04_R2_GUARD_LOG_DIR']=str(a.output/'guard-records')
import offline_guard
sys.path.insert(0,str(a.root/'src'))
from PIL import Image
from annotation.source.usense.cli import main
from annotation.contracts import load_bundle
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
width,height=37,29;row=b'\0'+bytes((i*13)%256 for i in range(width*3))
blob=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(row))+chunk(b'IEND',b'')
source=a.output/'input';shutil.copytree(a.root/'tests/fixtures/a04/source',source)
capture=json.loads((source/'capture.json').read_text(encoding='utf-8'))
(source/capture['pages'][0]['asset_path']).write_bytes(blob)
with Image.open(io.BytesIO(blob)) as im:im.verify()
with Image.open(io.BytesIO(blob)) as im:im.load()
buf=io.StringIO();target=a.output/'output'
with contextlib.redirect_stdout(buf):rc=main(['offline','--input',str(source),'--output',str(target),'--as-of',capture['observed_at']])
accepted=False
if (target/'bundle.json').exists():load_bundle(target/'bundle.json');accepted=True
r={'sha256':hashlib.sha256(blob).hexdigest(),'input_bytes':len(blob),'CRC_valid':True,'zlib_stream_complete':True,
 'declared_size':[width,height],'actual_scanline_bytes':len(row),'expected_scanline_bytes':height*(1+width*3),
 'actual_rows':1,'declared_rows':height,'Pillow_verify_and_load':'ACCEPTED',
 'public_cli_returncode':rc,'public_cli_stdout':buf.getvalue(),'final_bundle_created':(target/'bundle.json').exists(),
 'public_loader_accepted':accepted,'expected':'Reject incomplete original pixels before publishing a final bundle',
 'defect_reproduced':rc==0 and accepted}
(a.output/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r));raise SystemExit(1 if r['defect_reproduced'] else 0)
