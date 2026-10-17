"""R2 independent public-entry and publication tests, local Python only."""
import argparse,contextlib,copy,hashlib,io,json,os,shutil,struct,subprocess,sys,traceback,zlib
from pathlib import Path
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
ROOT=a.root.resolve();OUT=a.output.resolve();OUT.mkdir(parents=True,exist_ok=False)
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'src'))
from PIL import Image,ImageFile
from annotation.source.usense import parse_capture,build_source,SourceParseError
from annotation.source.usense import cli
from annotation.contracts import load_bundle,seal_artifact,artifact_ref,write_bundle
BASE=json.loads((ROOT/'tests/fixtures/a04/source/capture.json').read_text(encoding='utf-8'))
RESULTS=[];CHILDREN=[];DIM=(37,29);DEPENDENCY='c6bebdf43eb93f7a6ae21e96ec07ed155686777d'
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
CONSUMER=Path(__file__).with_name('consume_package.py')
elsewhere=Path(os.environ['TEMP'])/'independent consumer cwd with spaces';elsewhere.mkdir(exist_ok=True)
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(blob):return hashlib.sha256(blob).hexdigest()
def execute(name,fn):
    try:r={'case':name,'status':'PASS','observation':fn()}
    except Exception as e:r={'case':name,'status':'FAIL','type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
    RESULTS.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
def image(fmt,seed=1):
    im=Image.new('RGB',DIM);pix=im.load()
    for y in range(DIM[1]):
        for x in range(DIM[0]):pix[x,y]=((x*19+y*13+seed)%256,(x*7+y*31+seed*3)%256,(x*x+y*17+seed*11)%256)
    if fmt=='P2':
        gray=im.convert('L');return ('P2\n# independent R2 synthetic\n37 29\n255\n'+' '.join(str(v) for v in gray.getdata())+'\n').encode()
    if fmt=='P5':
        gray=im.convert('L');return b'P5\n37 29\n255\n'+gray.tobytes()
    b=io.BytesIO();im.save(b,format=fmt,**({'quality':89,'progressive':True} if fmt=='JPEG' else {}));return b.getvalue()
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def short_pixels_png():
    # All CRCs valid and valid zlib stream, but only ONE of 29 required RGB rows.
    ihdr=struct.pack('>IIBBBBB',*DIM,8,2,0,0,0)
    row=b'\0'+bytes((i*13)%256 for i in range(DIM[0]*3))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(row))+chunk(b'IEND',b'')
def truncated_jpeg():
    im=Image.open(io.BytesIO(image('PNG')));stream=io.BytesIO();im.save(stream,format='JPEG',quality=89)
    blob=stream.getvalue();sos=blob.index(b'\xff\xda');entropy=sos+2+struct.unpack('>H',blob[sos+2:sos+4])[0]
    return blob[:entropy+max(2,(len(blob)-entropy)//5)]
def bad_crc_png():
    data=bytearray(image('PNG'));index=data.index(b'IDAT');length=struct.unpack('>I',data[index-4:index])[0]
    data[index+4+length]^=64;return bytes(data)
def decode(blob):
    facts={'bytes':len(blob),'sha256':sha(blob)}
    try:
        with Image.open(io.BytesIO(blob)) as im:
            facts.update(format=im.format,size=list(im.size));im.verify()
        facts['structure']='PASS'
    except Exception as e:facts.update(structure='REJECTED',structure_error=type(e).__name__)
    try:
        with Image.open(io.BytesIO(blob)) as im:
            for frame in range(getattr(im,'n_frames',1)):im.seek(frame);im.load()
        facts['full_decode']='PASS'
    except Exception as e:facts.update(full_decode='REJECTED',decode_error=type(e).__name__)
    return facts
def input_package(name,fmt='PNG',first=None):
    case=OUT/name;source=case/'input';(source/'assets').mkdir(parents=True)
    capture=copy.deepcopy(BASE);capture['book']['title']='SYNTHETIC reviewer R2 '+name
    rows=[]
    for i,pg in enumerate(capture['pages']):
        extension={'PNG':'png','JPEG':'jpg','P2':'pgm','P5':'pgm'}[fmt]
        rel='assets/reviewer-'+str(pg['viewer_page'])+'.'+extension;data=first if i==0 and first is not None else image(fmt,i+1)
        (source/rel).write_bytes(data);pg['asset_path']=rel
        rows.append({'path':rel,'sha256':sha(data),'bytes':len(data)})
    save(source/'capture.json',capture);save(case/'input-inventory.json',{'mode':'SYNTHETIC_INDEPENDENT','assets':rows})
    return case,source,capture
def run(command,cwd,prefix):
    process=subprocess.Popen(command,cwd=str(cwd),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    timed_out=False
    try:out,err=process.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        timed_out=True;process.kill();out,err=process.communicate(timeout=10)
    prefix.with_suffix('.stdout.txt').write_bytes(out);prefix.with_suffix('.stderr.txt').write_bytes(err)
    record={'args':command,'cwd':str(cwd),'pid':process.pid,'returncode':process.returncode,
       'reaped':process.poll() is not None,'timed_out':timed_out}
    CHILDREN.append(record);save(prefix.with_suffix('.command.json'),record)
    assert not timed_out,record
    return process.returncode,out.decode('utf-8','replace'),err.decode('utf-8','replace')
def public_case(name,fmt='PNG',first=None,valid=True,structural=None,complete=None):
    case,source,cap=input_package(name,fmt,first);blob=(source/cap['pages'][0]['asset_path']).read_bytes();fact=decode(blob)
    if structural:assert fact['structure']==structural,fact
    if complete:assert fact['full_decode']==complete,fact
    target=case/'output';command=[sys.executable,'-B','-m','annotation.source.usense','offline',
      '--input',str(source),'--output',str(target),'--as-of',cap['observed_at']]
    rc,stdout,stderr=run(command,elsewhere,case/'public-cli')
    fact.update(cli_returncode=rc,output_exists=target.exists(),final_bundle=(target/'bundle.json').exists(),stdout=stdout)
    if not valid:
        assert rc==2 and not target.exists(),fact
        assert stdout.strip()=='A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path',fact
        assert not stderr and str(source) not in stdout,fact
    else:
        assert rc==0 and not stderr,fact
        moved=case/'relocated full package with spaces';shutil.copytree(target,moved)
        code,output,errors=run([sys.executable,'-B',str(CONSUMER),str(moved)],elsewhere,case/'relocated-consumer')
        assert code==0 and not errors,(code,output,errors)
        facts=json.loads(output);bindings=facts['assets'];expected=json.loads((case/'input-inventory.json').read_text(encoding='utf-8'))['assets']
        assert {v['path']:v['sha256'] for v in bindings}=={v['path']:v['sha256'] for v in expected}
        assert all(v['size']==list(DIM) for v in bindings)
        expected_media={'PNG':'image/png','JPEG':'image/jpeg','P2':'image/x-portable-graymap','P5':'image/x-portable-graymap'}[fmt]
        assert all(v['media_type']==expected_media for v in bindings),bindings
        entry=json.loads((target/'evidence/entry-result.json').read_text(encoding='utf-8'))
        assert entry['geometry_dependency_status']=='ACCEPTED' and entry['geometry_dependency_commit']==DEPENDENCY
        assert entry['geometry_status']=='NOT_PERFORMED_BY_SOURCE' and entry['acceptance']=='NOT_ASSERTED' and not entry['network_used']
        assert 'WAITING_ACCEPTED_COMMIT' not in stdout and 'GEOMETRY_NOT_PERFORMED' in stdout
        fact.update(relocation=facts,entry=entry)
    save(case/'result.json',fact);return fact

TRUNCATED=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x04\x00\x00\x00\x03'
assert len(TRUNCATED)==24 and sha(TRUNCATED)=='501c8a30dc5edc616c56ac49f6c38180b2ea7335fe42c57350484ae5356def29'
execute('N01-original-24-byte-PNG',lambda:public_case('N01-original-24-byte-PNG',first=TRUNCATED,valid=False,complete='REJECTED'))
execute('N02-valid-CRC-zlib-short-pixels',lambda:public_case('N02-valid-CRC-zlib-short-pixels',first=short_pixels_png(),valid=False,structural='PASS',complete='REJECTED'))
execute('N03-JPEG-valid-header-short-entropy',lambda:public_case('N03-JPEG-valid-header-short-entropy',fmt='JPEG',first=truncated_jpeg(),valid=False,structural='PASS',complete='REJECTED'))
execute('N04-PGM-P5-missing-pixels',lambda:public_case('N04-PGM-P5-missing-pixels',fmt='P5',first=b'P5\n37 29\n255\n'+bytes(range(23)),valid=False,structural='PASS',complete='REJECTED'))
execute('N05-PNG-valid-pixels-bad-CRC',lambda:public_case('N05-PNG-valid-pixels-bad-CRC',first=bad_crc_png(),valid=False,structural='REJECTED',complete='PASS'))
for fmt in ['PNG','JPEG','P2','P5']:
    execute('P-'+fmt+'-portable',lambda fmt=fmt:public_case('P-'+fmt+'-portable',fmt=fmt,structural='PASS',complete='PASS'))

def publication(name,mode):
    case,source,cap=input_package(name);parsed=parse_capture(cap,source,now=cap['observed_at'])
    file=source/cap['pages'][0]['asset_path'];before=sha(file.read_bytes())
    file.write_bytes(short_pixels_png() if mode=='corrupt' else image('PNG',97))
    after=sha(file.read_bytes());assert before!=after
    try:build_source(parsed,source)
    except SourceParseError as e:error={'code':e.code,'path':e.path}
    else:raise AssertionError('Changed original published')
    expected='RESOURCE_INVALID' if mode=='corrupt' else 'RESOURCE_MISMATCH'
    assert error=={'code':expected,'path':'$.pages[0].path' if mode=='corrupt' else '$.pages[0]'},error
    assert not (source/'evidence').exists() and not (source/'bundle.json').exists()
    r={'before_sha256':before,'after_sha256':after,'after_decode':decode(file.read_bytes()),'error':error,
       'source_history_created':False,'final_bundle_created':False}
    save(case/'result.json',r);return r
execute('U01-damaged-after-parse-before-source',lambda:publication('U01-damaged-after-parse-before-source','corrupt'))
execute('U02-valid-bytes-changed-after-parse',lambda:publication('U02-valid-bytes-changed-after-parse','valid'))
def public_copy_race():
    case,source,cap=input_package('U03-public-parse-copy-race');original=cli.parse_capture;mutated=False
    def between(*args,**kwargs):
        nonlocal mutated
        parsed=original(*args,**kwargs)
        if not mutated:
            (source/cap['pages'][0]['asset_path']).write_bytes(short_pixels_png());mutated=True
        return parsed
    target=case/'output';buf=io.StringIO()
    with patch.object(cli,'parse_capture',side_effect=between),patch.object(cli,'collect_live',side_effect=AssertionError('offline scope')),contextlib.redirect_stdout(buf):
        rc=cli.main(['offline','--input',str(source),'--output',str(target),'--as-of',cap['observed_at']])
    assert rc==2 and mutated and not (target/'bundle.json').exists() and not (target/'evidence/source-capture.json').exists()
    assert buf.getvalue().strip()=='A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path'
    (case/'stdout.txt').write_text(buf.getvalue(),encoding='utf-8')
    r={'returncode':rc,'output_directory_exists':target.exists(),'source_history_created':False,'final_bundle_created':False,
       'meaning':'Partial failure files retained; neither source history nor final bundle published'};save(case/'result.json',r);return r
execute('U03-public-parse-copy-race',public_copy_race)
def truncation_flag():
    case,source,cap=input_package('G01-ambient-permissive-flag');assert ImageFile.LOAD_TRUNCATED_IMAGES is False
    old=ImageFile.LOAD_TRUNCATED_IMAGES
    try:
        ImageFile.LOAD_TRUNCATED_IMAGES=True
        try:parse_capture(cap,source,now=cap['observed_at'])
        except SourceParseError as e:code=e.code
        else:raise AssertionError('Permissive ambient decoder accepted')
        assert code=='RESOURCE_INVALID' and ImageFile.LOAD_TRUNCATED_IMAGES is True
    finally:ImageFile.LOAD_TRUNCATED_IMAGES=old
    assert ImageFile.LOAD_TRUNCATED_IMAGES is False
    r={'gate':'RESOURCE_INVALID','product_changed_global_flag':False,'harness_restored_initial_false':True};save(case/'result.json',r);return r
execute('G01-ambient-permissive-flag',truncation_flag)
def redaction():
    case,source,cap=input_package('G02-decoder-error-redaction');buf=io.StringIO();target=case/'output'
    with patch.object(ImageFile.ImageFile,'load',side_effect=OSError('R2_SYNTHETIC_PRIVATE_MARKER '+str(source))),contextlib.redirect_stdout(buf):
        rc=cli.main(['offline','--input',str(source),'--output',str(target),'--as-of',cap['observed_at']])
    text=buf.getvalue();assert rc==2 and text.strip()=='A04_FAILED:RESOURCE_INVALID; LOCATION=$.pages[0].asset_path'
    assert 'R2_SYNTHETIC_PRIVATE_MARKER' not in text and str(source) not in text and not target.exists()
    (case/'stdout.txt').write_text(text,encoding='utf-8');r={'returncode':rc,'stdout':text,'output_created':False};save(case/'result.json',r);return r
execute('G02-decoder-error-redaction',redaction)
def layer_boundary():
    case=OUT/'L01-artificial-hash-only-forgery';source=case/'SYNTHETIC_FORGERY_NOT_A04_OUTPUT'
    shutil.copytree(OUT/'P-PNG-portable/output',source)
    data=load_bundle(source/'bundle.json').model_dump(mode='json');artifact=next(x for x in data['artifacts'] if x['kind']=='SourceBundle')
    asset=artifact['payload']['assets'][0];blob=short_pixels_png();(source/asset['path']).write_bytes(blob);key=asset['asset_id'];newsha=sha(blob)
    def rebind(value):
        if isinstance(value,dict):
            if value.get('asset_id')==key and 'sha256' in value:value['sha256']=newsha
            for child in value.values():rebind(child)
        elif isinstance(value,list):
            for child in value:rebind(child)
    rebind(data);new_source=seal_artifact(artifact);artifacts=[new_source]
    for other in data['artifacts']:
        if other['kind']=='SourceBundle':continue
        other['input_refs']=[artifact_ref(new_source) if ref['artifact_id']==new_source['artifact_id'] else ref for ref in other['input_refs']]
        artifacts.append(seal_artifact(other))
    data['artifacts']=artifacts;write_bundle(data,source/'artificial-exchange.json');load_bundle(source/'artificial-exchange.json')
    cap=json.loads((source/'capture.json').read_text(encoding='utf-8'))
    try:parse_capture(cap,source,now=cap['observed_at'])
    except SourceParseError as e:source_code=e.code
    else:raise AssertionError('Source full decoder accepted artificial hash-only bundle')
    assert source_code=='RESOURCE_INVALID'
    r={'label':'SYNTHETIC_TEST_FORGERY','a04_legal_output':False,'public_hash_header_loader':'ACCEPTED',
       'full_decode':decode(blob),'a04_source_gate':source_code,'public_contract_changed':False}
    save(case/'LAYER-BOUNDARY.json',r);return r
execute('L01-artificial-hash-only-forgery',layer_boundary)
assert ImageFile.LOAD_TRUNCATED_IMAGES is False
summary={'target_commit':'76898657e76ac2db071327e90c6ca5031d17571f','mode':'LOCAL_PYTHON_INDEPENDENT_SYNTHETIC',
 'results':RESULTS,'passed':sum(r['status']=='PASS' for r in RESULTS),'failed':sum(r['status']=='FAIL' for r in RESULTS),
 'children':CHILDREN,'all_recorded_children_reaped':all(p['reaped'] for p in CHILDREN),
 'initial_and_final_truncation_flag':False,'real_R01_R06':'BLOCKED_NOT_RUN',
 'browser_profile_login_network_model_or_book_actions':0}
save(OUT/'results.json',summary)
print('SUMMARY '+json.dumps({'passed':summary['passed'],'failed':summary['failed'],'child_count':len(CHILDREN)}),flush=True)
raise SystemExit(0 if summary['failed']==0 else 1)
