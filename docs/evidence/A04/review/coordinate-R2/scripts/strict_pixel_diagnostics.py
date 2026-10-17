"""Targeted LOCAL recheck of decoder discrepancy; preserve initial failures."""
import argparse,contextlib,copy,hashlib,io,json,os,shutil,struct,subprocess,sys,traceback,zlib
from pathlib import Path
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
ROOT=a.root.resolve();OUT=a.output.resolve();OUT.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(ROOT/'src'))
from PIL import Image,ImageFile
import cv2,numpy as np
from annotation.source.usense import parse_capture,build_source,SourceParseError
from annotation.source.usense import cli
from annotation.contracts import load_bundle
BASE=json.loads((ROOT/'tests/fixtures/a04/source/capture.json').read_text(encoding='utf-8'))
R2=Path(__file__).resolve().parents[1];SHORT=R2/'independent-cases/N02-valid-CRC-zlib-short-pixels/input'
RESULTS=[];CHILDREN=[]
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def validate_png_rows(blob):
    pos=8;raw=b'';crc=True;chunks=[]
    while pos<len(blob):
        length=struct.unpack('>I',blob[pos:pos+4])[0];kind=blob[pos+4:pos+8];data=blob[pos+8:pos+8+length]
        expected_crc=struct.unpack('>I',blob[pos+8+length:pos+12+length])[0]
        crc=crc and (zlib.crc32(kind+data)&0xffffffff)==expected_crc;chunks.append(kind.decode())
        if kind==b'IHDR':w,h,depth,color,compression,filtermethod,interlace=struct.unpack('>IIBBBBB',data)
        if kind==b'IDAT':raw+=data
        pos+=12+length
    assert (depth,color,compression,filtermethod,interlace)==(8,2,0,0,0)
    pixels=zlib.decompress(raw);expected_bytes=h*(1+w*3)
    return {'ihdr_size':[w,h],'color':'8bit RGB noninterlaced','chunk_CRCs_valid':crc,'chunks':chunks,
      'zlib_decompression_completed':True,'actual_scanline_bytes':len(pixels),'expected_scanline_bytes':expected_bytes,
      'complete_rows':len(pixels)//(1+w*3),'expected_rows':h,'pixel_rows_complete':len(pixels)==expected_bytes}
def decoders(blob):
    r={}
    for name,op in [('pillow_structure',lambda im:im.verify()),('pillow_full_load',lambda im:im.load())]:
        try:
            with Image.open(io.BytesIO(blob)) as im:op(im)
            r[name]='PASS'
        except Exception as e:r[name]='REJECTED';r[name+'_error']=type(e).__name__
    decoded=cv2.imdecode(np.frombuffer(blob,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
    r['opencv_full_decode']='REJECTED' if decoded is None else 'PASS'
    if decoded is not None:r['opencv_shape']=list(decoded.shape)
    return r
def run_cli(source,output,label):
    cap=json.loads((source/'capture.json').read_text(encoding='utf-8'))
    command=[sys.executable,'-B','-m','annotation.source.usense','offline','--input',str(source),'--output',str(output),'--as-of',cap['observed_at']]
    process=subprocess.Popen(command,cwd=str(OUT),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=process.communicate(timeout=40)
    (OUT/(label+'-stdout.txt')).write_bytes(out);(OUT/(label+'-stderr.txt')).write_bytes(err)
    record={'args':command,'cwd':str(OUT),'pid':process.pid,'returncode':process.returncode,'reaped':process.poll() is not None}
    CHILDREN.append(record);save(OUT/(label+'-command.json'),record)
    return process.returncode,out.decode('utf-8','replace')
def case(name,fn):
    try:r={'case':name,'status':'PASS','observation':fn()}
    except Exception as e:r={'case':name,'status':'FAIL','error':str(e),'traceback':traceback.format_exc()}
    RESULTS.append(r);print(json.dumps(r),flush=True)

def short_png():
    cap=json.loads((SHORT/'capture.json').read_text(encoding='utf-8'));blob=(SHORT/cap['pages'][0]['asset_path']).read_bytes()
    rows=validate_png_rows(blob);d=decoders(blob)
    assert rows['chunk_CRCs_valid'] and not rows['pixel_rows_complete'] and d['opencv_full_decode']=='REJECTED'
    assert rows['actual_scanline_bytes']==112 and rows['expected_scanline_bytes']==3248
    output=OUT/'short-row-public-output';rc,stdout=run_cli(SHORT,output,'short-row-public')
    accepted=False
    if (output/'bundle.json').exists():load_bundle(output/'bundle.json');accepted=True
    r={'sha256':hashlib.sha256(blob).hexdigest(),'independent_row_check':rows,'decoders':d,
       'public_cli_returncode':rc,'public_loader_accepted':accepted,'stdout':stdout,
       'final_bundle_created':(output/'bundle.json').exists(),'expected':'Reject incomplete original before publication'}
    save(OUT/'short-row-observation.json',r)
    assert rc==2 and not accepted,r
    return r
case('D01-short-row-CRC-valid-PNG-public-gate',short_png)

# Independent second corrupt pixel input with full decompressed length but an
# illegal PNG filter byte; valid zlib and CRCs, structural verify still passes.
def filter_png():
    raw=(b'\xff'+bytes([20,40,60])*37)+(b'\0'+bytes([70,80,90])*37)*28
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',37,29,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
def prepare(name,bad=False):
    folder=OUT/name;shutil.copytree(SHORT,folder/'input');source=folder/'input';cap=json.loads((source/'capture.json').read_text(encoding='utf-8'))
    good=io.BytesIO();Image.new('RGB',(37,29),(10,20,30)).save(good,format='PNG')
    (source/cap['pages'][0]['asset_path']).write_bytes(filter_png() if bad else good.getvalue())
    return folder,source,cap
def bad_filter():
    folder,source,cap=prepare('invalid-filter',True);blob=(source/cap['pages'][0]['asset_path']).read_bytes();d=decoders(blob)
    assert d['pillow_structure']=='PASS' and d['pillow_full_load']=='REJECTED' and d['opencv_full_decode']=='REJECTED',d
    rc,stdout=run_cli(source,folder/'output','invalid-filter')
    r={'decoder':d,'public_cli_returncode':rc,'stdout':stdout,'output_exists':(folder/'output').exists()}
    save(folder/'result.json',r);assert rc==2 and not r['output_exists'] and 'RESOURCE_INVALID; LOCATION=$.pages[0].asset_path' in stdout,r
    return r
case('D02-full-length-invalid-filter-PNG-rejected',bad_filter)
def before_publish():
    folder,source,cap=prepare('invalid-filter-after-parse');parsed=parse_capture(cap,source,now=cap['observed_at'])
    (source/cap['pages'][0]['asset_path']).write_bytes(filter_png())
    try:build_source(parsed,source)
    except SourceParseError as e:error={'code':e.code,'path':e.path}
    else:raise AssertionError('Damaged pixels published')
    r={'error':error,'history_exists':(source/'evidence').exists(),'bundle_exists':(source/'bundle.json').exists()}
    save(folder/'result.json',r);assert error=={'code':'RESOURCE_INVALID','path':'$.pages[0].path'} and not r['history_exists'] and not r['bundle_exists']
    return r
case('D03-invalid-filter-before-publication-recheck',before_publish)
def public_copy():
    folder,source,cap=prepare('invalid-filter-public-copy');real=cli.parse_capture;done=False;buf=io.StringIO();target=folder/'output'
    def mutate(*args,**kwargs):
        nonlocal done
        parsed=real(*args,**kwargs)
        if not done:(source/cap['pages'][0]['asset_path']).write_bytes(filter_png());done=True
        return parsed
    with patch.object(cli,'parse_capture',side_effect=mutate),contextlib.redirect_stdout(buf):
        rc=cli.main(['offline','--input',str(source),'--output',str(target),'--as-of',cap['observed_at']])
    r={'returncode':rc,'stdout':buf.getvalue(),'history_exists':(target/'evidence/source-capture.json').exists(),'bundle_exists':(target/'bundle.json').exists()}
    save(folder/'result.json',r);assert rc==2 and not r['history_exists'] and not r['bundle_exists']
    return r
case('D04-invalid-filter-public-copy-recheck',public_copy)
save(OUT/'results.json',{'results':RESULTS,'passed':sum(r['status']=='PASS' for r in RESULTS),
 'failed':sum(r['status']=='FAIL' for r in RESULTS),'children':CHILDREN,
 'opencv_version':cv2.__version__,'numpy_version':np.__version__,
 'all_recorded_children_reaped':all(p['reaped'] for p in CHILDREN),'network_browser_profile_or_model_used':False})
print('SUMMARY '+json.dumps({'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS)}),flush=True)
raise SystemExit(1 if any(r['status']=='FAIL' for r in RESULTS) else 0)
