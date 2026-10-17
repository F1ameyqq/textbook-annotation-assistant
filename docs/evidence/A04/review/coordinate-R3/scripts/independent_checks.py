"""Bounded representative R3 checks; synthetic PNG oracle uses physical tiles."""
import argparse,contextlib,copy,hashlib,io,json,os,shutil,struct,subprocess,sys,time,traceback,tracemalloc,zlib
from pathlib import Path
from unittest.mock import patch
from process_identity import child
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--consume',type=Path);a=p.parse_args()
ROOT=a.root.resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'src'))
from PIL import Image,ImageFile
from annotation.source.usense import parse_capture,build_source,SourceParseError
from annotation.source.usense import cli,parser,png_pixels as gate
from annotation.contracts import load_bundle
def sha(b):return hashlib.sha256(b).hexdigest()
if a.consume:
    bundle=load_bundle(a.consume/'bundle.json');source=next(x for x in bundle.artifacts if x.kind=='SourceBundle');rows=[]
    for asset in source.payload.assets:
        b=(a.consume/asset.path).read_bytes()
        assert sha(b)==asset.sha256 and not Path(asset.path).is_absolute()
        with Image.open(io.BytesIO(b)) as im:
            im.load();assert im.size==(asset.width,asset.height);fmt=im.format
        rows.append({'path':asset.path,'sha256':asset.sha256,'size':[asset.width,asset.height],'media_type':asset.media_type,'decoded_format':fmt})
    print(json.dumps({'public_loader':'PASS','complete_decode':'PASS','assets':rows}));raise SystemExit(0)
OUT=a.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
BASE=json.loads((ROOT/'tests/fixtures/a04/source/capture.json').read_text(encoding='utf-8'))
RESULTS=[];CHILDREN=[]
ENV=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
OTHER=Path(os.environ['TEMP'])/'independent consumer cwd with spaces';OTHER.mkdir(exist_ok=True)
TILE=((0,5,3,5,1,5,3,5),(6,)*8,(4,5,4,5,4,5,4,5),(6,)*8,
      (2,5,3,5,2,5,3,5),(6,)*8,(4,5,4,5,4,5,4,5),(6,)*8)
def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def wrap(w,h,depth,colour,interlace,raw,palette=None,compressed=None,extra=b''):
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,depth,colour,0,0,interlace))+(chunk(b'PLTE',palette) if palette is not None else b'')+extra+chunk(b'IDAT',compressed if compressed is not None else zlib.compress(raw))+chunk(b'IEND',b'')
def layout(w,h,depth,colour,interlace,filter_method=0,padding=False,one_palette=False,bad_index=False):
    channels={0:1,2:3,3:1,4:2,6:4}[colour];mask=(1<<depth)-1
    entries=1 if one_palette else 2
    palette=bytes(v for i in range(entries) for v in (i*200,i*170,i*90)) if colour==3 else None
    output=bytearray();row_oracle=[];covered=[]
    # Tile partitions actual image coordinates; no production layout helper or
    # pass width/height formula is used to produce expected bytes.
    for pass_id in range(7 if interlace else 1):
        previous=None
        for y in range(h):
            xs=[x for x in range(w) if not interlace or TILE[y%8][x%8]==pass_id]
            if not xs:continue
            samples=[]
            for x in xs:
                covered.append((x,y))
                for c in range(channels):
                    v=((x+y)%entries) if colour==3 else ((x*257+y*71+c*19)&mask)
                    if bad_index and colour==3 and x==0 and y==0:v=2
                    samples.append(v)
            row=bytearray()
            if depth<8:
                for offset in range(0,len(samples),8//depth):
                    group=samples[offset:offset+8//depth];value=sum(v<<(8-depth*(j+1)) for j,v in enumerate(group))
                    if padding and len(group)*depth<8:value|=(1<<(8-len(group)*depth))-1
                    row.append(value)
            else:
                for value in samples:row.extend(value.to_bytes(depth//8,'big'))
            previous=previous if previous is not None else bytes(len(row));assert len(previous)==len(row)
            distance=max(1,(channels*depth+7)//8);encoded=bytearray()
            for i,value in enumerate(row):
                left=row[i-distance] if i>=distance else 0;up=previous[i];corner=previous[i-distance] if i>=distance else 0
                prediction=left+up-corner
                paeth=min(enumerate((left,up,corner)),key=lambda pair:(abs(prediction-pair[1]),pair[0]))[1]
                predictor=(0,left,up,(left+up)//2,paeth)[filter_method]
                encoded.append((value-predictor)&255)
            output.append(filter_method);output.extend(encoded)
            row_oracle.append({'pass':pass_id,'physical_y':y,'physical_pixels':len(xs),'scanline_bytes':1+len(row)})
            previous=row
    assert len(covered)==w*h and len(set(covered))==w*h
    raw=bytes(output);return wrap(w,h,depth,colour,interlace,raw,palette),raw,row_oracle,palette
def record(name,fn):
    try:result={'case':name,'status':'PASS','observation':fn()}
    except Exception as e:result={'case':name,'status':'FAIL','error':str(e),'traceback':traceback.format_exc()}
    RESULTS.append(result);print(json.dumps(result),flush=True)
def expect_reject(blob,reason=None):
    try:gate.verify_png_pixels(blob)
    except gate.PNGPixelError as e:
        if reason:assert str(e)==reason,(reason,str(e))
        return str(e)
    raise AssertionError('Invalid PNG accepted by pixel gate')
def call(command,cwd,prefix):
    process=subprocess.Popen(command,cwd=str(cwd),env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE);identity=child(process)
    try:out,err=process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill();out,err=process.communicate(timeout=5);raise AssertionError('Bounded child timed out')
    prefix.with_suffix('.stdout.txt').write_bytes(out);prefix.with_suffix('.stderr.txt').write_bytes(err)
    info={'args':command,'cwd':str(cwd),'identity':identity,'returncode':process.returncode,'reaped':process.poll() is not None}
    CHILDREN.append(info);save(prefix.with_suffix('.command.json'),info)
    return process.returncode,out.decode('utf-8','replace'),err.decode('utf-8','replace')
def package(name,blob,size):
    folder=OUT/name;source=folder/'input';shutil.copytree(ROOT/'tests/fixtures/a04/source',source)
    cap=copy.deepcopy(BASE);cap['book']['title']='SYNTHETIC R3 reviewer '+name
    first=cap['pages'][0]['asset_path'];(source/first).write_bytes(blob)
    # Explicit synthetic frame is adjusted to fit deliberately tiny edge images.
    cap['annotations']['data'][0]['rect_bbox']='0,0,{},{}'.format(min(size[0],3),min(size[1],2))
    save(source/'capture.json',cap);return folder,source,cap
def public(name,blob,size,valid):
    folder,source,cap=package(name,blob,size);target=folder/'output'
    args=[sys.executable,'-B','-m','annotation.source.usense','offline','--input',str(source),'--output',str(target),'--as-of',cap['observed_at']]
    rc,stdout,stderr=call(args,OTHER,folder/'public-cli');fact={'returncode':rc,'stdout':stdout,'input_sha256':sha(blob),'input_bytes':len(blob),
      'output_exists':target.exists(),'bundle_created':(target/'bundle.json').exists()}
    if not valid:
        assert rc==2 and not target.exists() and not stderr,fact
        assert stdout.strip()=='A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path'
    else:
        assert rc==0 and not stderr,fact
        moved=folder/'relocated full package with spaces';shutil.copytree(target,moved)
        code,output,errors=call([sys.executable,'-B',str(Path(__file__)),'--root',str(ROOT),'--consume',str(moved)],OTHER,folder/'consumer')
        assert code==0 and not errors,(code,output,errors)
        consumer=json.loads(output);assert consumer['assets'][0]['sha256']==sha(blob) and consumer['assets'][0]['size']==list(size)
        fact['consumer']=consumer
        entry=json.loads((moved/'evidence/entry-result.json').read_text(encoding='utf-8'))
        assert entry['geometry_dependency_status']=='ACCEPTED' and entry['geometry_dependency_commit']=='c6bebdf43eb93f7a6ae21e96ec07ed155686777d'
        assert entry['geometry_status']=='NOT_PERFORMED_BY_SOURCE' and entry['acceptance']=='NOT_ASSERTED' and not entry['network_used']
        fact['entry']=entry
    save(folder/'result.json',fact);return fact

LAYOUTS=[('gray1-packed',9,5,1,0,0,0,True,False),('palette2-Adam7-Paeth',7,6,2,3,1,4,True,False),
 ('rgb16-plain',11,3,16,2,0,0,False,False),('rgba16-Adam7',9,13,16,6,1,0,False,False),
 ('gray16-tiny-Adam7',1,9,16,0,1,0,False,False),('grayalpha8',2,5,8,4,0,0,False,False),
 ('palette1-1x1-padding',1,1,1,3,1,0,True,True)]
GENERATED={}
for name,w,h,depth,colour,interlace,method,padding,one_palette in LAYOUTS:
    generated=layout(w,h,depth,colour,interlace,method,padding,one_palette);GENERATED[name]=generated
    def inspect(name=name,w=w,h=h,depth=depth,colour=colour,interlace=interlace,generated=generated):
        blob,raw,oracle,palette=generated
        with Image.open(io.BytesIO(blob)) as im:im.load();assert im.size==(w,h)
        info=gate.verify_png_pixels(blob);assert info['actual_scanline_bytes']==len(raw)==sum(r['scanline_bytes'] for r in oracle)
        errors=[expect_reject(wrap(w,h,depth,colour,interlace,altered,palette),'SCANLINE_SIZE') for altered in (raw[:-1],raw+b'\0')]
        save(OUT/(name+'-oracle.json'),{'layout':[w,h,depth,colour,interlace],'physical_rows':oracle,'expected_bytes':len(raw),'gate':info,'negative_reasons':errors})
        return {'layout':[w,h,depth,colour,interlace],'expected_bytes':len(raw),'gate':info,'short_and_extra_rejected':True}
    record('L-'+name,inspect)
for name in ['gray1-packed','palette2-Adam7-Paeth','rgba16-Adam7','palette1-1x1-padding']:
    dims=next((x[1],x[2]) for x in LAYOUTS if x[0]==name)
    record('P-'+name,lambda name=name,dims=dims:public('P-'+name,GENERATED[name][0],dims,True))
def encoded(fmt,mode='RGB',size=(17,9),value='white'):
    b=io.BytesIO();Image.new(mode,size,value).save(b,format=fmt);return b.getvalue()
for name,blob in [('white-PNG',encoded('PNG')),('JPEG',encoded('JPEG')),
                  ('PGM-P5',b'P5\n17 9\n255\n'+b'\xff'*(17*9)),
                  ('PGM-P2',b'P2\n17 9\n255\n'+b'255 '*(17*9)+b'\n')]:
    record('P-'+name,lambda name=name,blob=blob:public('P-'+name,blob,(17,9),True))
for name in ['gray1-packed','rgba16-Adam7']:
    _,w,h,d,c,i,*_=next(x for x in LAYOUTS if x[0]==name);b,raw,rows,palette=GENERATED[name]
    record('N-'+name+'-short',lambda name=name,w=w,h=h,d=d,c=c,i=i,raw=raw,palette=palette:public('N-'+name+'-short',wrap(w,h,d,c,i,raw[:-1],palette),(w,h),False))
def publication_swap():
    good,_,_,_=layout(37,29,8,2,0);folder,source,cap=package('U-same-size-swap',good,(37,29))
    parsed=parse_capture(cap,source,now=cap['observed_at']);bad=wrap(37,29,8,2,0,b'\0'+bytes((j*13)%256 for j in range(37*3)))
    assert sha(bad)=='205543876fb32bb14f003bfeec32279e9fd4886bd1949eee9810999e468969bd'
    (source/cap['pages'][0]['asset_path']).write_bytes(bad)
    try:build_source(parsed,source)
    except SourceParseError as e:error={'code':e.code,'path':e.path}
    else:raise AssertionError('Bad original published')
    assert error=={'code':'RESOURCE_INVALID','path':'$.pages[0].path'} and not (source/'evidence').exists()
    fact={'error':error,'source_history_exists':False,'final_bundle_exists':False};save(folder/'result.json',fact);return fact
record('U-same-size-swap',publication_swap)
def public_copy_swap():
    good,_,_,_=layout(37,29,8,2,0);folder,source,cap=package('U-public-copy-swap',good,(37,29));original=cli.parse_capture;changed=False;buf=io.StringIO();target=folder/'output'
    def mutate(*args,**kwargs):
        nonlocal changed
        obj=original(*args,**kwargs)
        if not changed:
            (source/cap['pages'][0]['asset_path']).write_bytes(wrap(37,29,8,2,0,b'\0'+bytes((j*13)%256 for j in range(37*3))));changed=True
        return obj
    with patch.object(cli,'parse_capture',side_effect=mutate),contextlib.redirect_stdout(buf):
        rc=cli.main(['offline','--input',str(source),'--output',str(target),'--as-of',cap['observed_at']])
    assert rc==2 and not (target/'bundle.json').exists() and not (target/'evidence/source-capture.json').exists()
    fact={'returncode':rc,'stdout':buf.getvalue(),'partial_output_exists':target.exists(),'history_published':False,'final_bundle_published':False};save(folder/'result.json',fact);return fact
record('U-public-copy-swap',public_copy_swap)

def resource_scaling():
    b,raw,_,_=layout(9,5,1,0,0);limits={'MAX_PNG_BYTES':len(b),'MAX_PNG_PIXELS':45,'MAX_PNG_DIMENSION':9,'MAX_PNG_SCANLINE_BYTES':len(raw),'MAX_PNG_CHUNKS':3};rows=[]
    for name,value in limits.items():
        with patch.object(gate,name,value):gate.verify_png_pixels(b)
        with patch.object(gate,name,value-1):reason=expect_reject(b)
        rows.append({'limit':name,'inclusive_value':value,'one_below_rejected':reason})
    return rows
record('R-inclusive-scaled-limits',resource_scaling)
def header_limits():
    rows=[]
    for w,h,d,c in [(32769,1,8,0),(32768,32768,8,0),(16384,1024,16,6)]:
        with patch.object(gate.zlib,'decompressobj',side_effect=AssertionError('must reject before decompression')) as create:
            reason=expect_reject(wrap(w,h,d,c,0,b''));assert create.call_count==0
        rows.append({'layout':[w,h,d,c],'reason':reason,'decompressors_created':0})
    return rows
record('R-default-header-limits',header_limits)
def expansion_cap():
    compressed=zlib.compress(b'\0'*(2*1024*1024));blob=wrap(13,11,8,0,0,b'',compressed=compressed);create=zlib.decompressobj;requests=[]
    class Proxy:
        def __init__(self):self.stream=create()
        def decompress(self,data,max_length):requests.append(max_length);return self.stream.decompress(data,max_length)
        def flush(self,*_):raise AssertionError('unbounded flush forbidden')
        def __getattr__(self,name):return getattr(self.stream,name)
    tracemalloc.start();t=time.perf_counter()
    with patch.object(gate.zlib,'decompressobj',side_effect=Proxy):reason=expect_reject(blob,'SCANLINE_SIZE')
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert requests and max(requests)<=155 and peak<2*1024*1024
    return {'compressed_bytes':len(compressed),'represented_expansion_bytes':2*1024*1024,'declared_scanline_bytes':154,
      'requested_output_caps':requests,'python_tracemalloc_peak':peak,'elapsed_seconds':time.perf_counter()-t,'reason':reason}
record('R-bounded-expansion',expansion_cap)
def capped_read():
    b,_,_,_=layout(17,9,8,2,0);b=b[:33]+chunk(b'tEXt',b'key\0'+b'x'*2048)+b[33:]
    folder=OUT/'R-capped-read';folder.mkdir();path=folder/'oversized.png';path.write_bytes(b);real_open=Path.open;reads=[]
    class Reader:
        def __enter__(self):self.stream=real_open(path,'rb');return self
        def __exit__(self,*args):self.stream.close()
        def read(self,n=-1):reads.append(n);return self.stream.read(n)
    def intercept(p,*args,**kwargs):return Reader() if p==path else real_open(p,*args,**kwargs)
    with patch.object(Path,'open',intercept),patch.object(parser,'MAX_PNG_BYTES',1024),patch.object(gate,'MAX_PNG_BYTES',1024):
        try:parser._image_inventory(path,'$.pages[0].asset_path')
        except SourceParseError as e:error={'code':e.code,'path':e.path}
        else:raise AssertionError('Over-limit file accepted')
    assert reads==[8,1017] and error['code']=='RESOURCE_INVALID'
    fact={'actual_file_bytes':len(b),'scaled_cap':1024,'read_request_sizes':reads,'maximum_read_bytes':1025,'error':error};save(folder/'result.json',fact);return fact
record('R-bounded-input-read',capped_read)

def apng():
    b=io.BytesIO();Image.new('RGBA',(5,5),'white').save(b,format='PNG',save_all=True,append_images=[Image.new('RGBA',(5,5),'black')],duration=100,loop=0)
    data=b.getvalue()
    with Image.open(io.BytesIO(data)) as im:
        assert im.n_frames==2
        for i in range(2):im.seek(i);im.load()
    expect_reject(data,'ANIMATION_UNSUPPORTED');return public('C-APNG-explicit-rejection',data,(5,5),False)
record('C-APNG-explicit-rejection',apng)
record('C-PNG-trailing-bytes-rejection',lambda:public('C-PNG-trailing-bytes-rejection',encoded('PNG')+b'R3-tail',(17,9),False))
def indexed_samples():
    good,_,_,_=layout(7,6,2,3,1,4,True,False);gate.verify_png_pixels(good)
    bad,_,_,_=layout(7,6,2,3,1,4,True,False,True)
    return {'normal_Paeth_padding':'PASS','invalid_index_reason':expect_reject(bad,'PALETTE_INDEX')}
record('C-indexed-Paeth-palette-sample',indexed_samples)
assert ImageFile.LOAD_TRUNCATED_IMAGES is False
summary={'mode':'BOUNDED_INDEPENDENT_LOCAL_PYTHON','results':RESULTS,'passed':sum(r['status']=='PASS' for r in RESULTS),
 'failed':sum(r['status']=='FAIL' for r in RESULTS),'children':CHILDREN,'all_children_reaped':all(r['reaped'] for r in CHILDREN),
 'oracle':'Physical 8x8 Adam7 tile partition and row byte packing, no production layout formula reused',
 'layout_count':len(LAYOUTS),'normal_public_formats':['PNG','JPEG','PGM-P2','PGM-P5'],
 'full_default_maximum_resource_stress':'NOT_RUN; scaled inclusive bounds and small expansion/input probes only',
 'real_platform_browser_profile_network_models':0}
save(OUT/'results.json',summary);print('SUMMARY '+json.dumps({'passed':summary['passed'],'failed':summary['failed'],'children':len(CHILDREN)}),flush=True)
raise SystemExit(0 if not summary['failed'] else 1)
