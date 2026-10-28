"""New finite source-only checks; no browser, HTTP, model or old save replay."""
from pathlib import Path
import copy,io,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from annotation.customer.store import Store,Hold,byte_hash,digest
from annotation.customer.platform_source import catalog,scope_plan,page_url,acquire,validate_plan
from annotation.customer.transport import UsenseTransport,NoRedirect
from annotation.runtime.usense_live.config import endpoints

BOOK='825730'
def response(v):return {'code':0,'data':v}
def fixture():
 return {'directory':response({'directory_data':[{'id':'chapter','label':'Chapter','children':[
  {'id':'lesson','label':'Selected ordinary lesson','children':[{'id':'old','label':'1','isQuestion':True,'order_in_level':'1'}]},
  {'id':'other','label':'Other lesson','children':[]}]}]}),
  'source':response({'file_id':BOOK,'total_pages':100}),
  'frames':response([{'file_id':BOOK,'order_in_level':'1','type':z,'page_index':p} for z,p in [('question',5),('answer',80)]])}

class SourceR1(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.store=Store(self.root/'store');self.flat=fixture()
  self.plan=scope_plan(catalog(self.flat,BOOK),'lesson')
 def test_program_scope_and_seven_exact_gets(self):
  self.assertEqual(self.plan['question_pages'],[5,6]);self.assertEqual(self.plan['answer_pages'],[80,81])
  self.assertEqual(self.plan['existing_node_ids'],['old']);self.assertEqual(self.plan['maximum_api_gets'],7)
  urls=endpoints(pages=[5,6,80,81],source=True,book_id=BOOK)
  self.assertEqual(len(urls),7);self.assertTrue(all(BOOK in u for u in urls.values()))
  self.assertFalse(any('get_question_info' in u or 'export' in u for u in urls.values()))
 def test_bad_plan_stops_before_resource(self):
  broken=copy.deepcopy(self.plan);broken['save_attempts']=1
  with patch('annotation.customer.platform_source.UsenseTransport') as resource:
   with self.assertRaises(Hold):acquire(self.store,{},broken)
   resource.assert_not_called()
  self.assertIsNone(self.store.operation('platform-source',digest(broken)))
 def test_directory_and_range_constraints(self):
  cat=catalog(self.flat,BOOK)
  for d,kwargs in [('chapter',{}),('other',{}),('lesson',{'question_pages':[5,5]}),('lesson',{'answer_pages':[5]})]:
   with self.subTest(d=d,kwargs=kwargs),self.assertRaises(Hold):scope_plan(cat,d,**kwargs)
 def test_page_binding_rejects_alias_wrong_book_and_query(self):
  good=response({'file_id':BOOK,'pages':[{'page_index':4,'image':'https://bucket.oss-cn.aliyuncs.com/books/'+BOOK+'/page.jpg'}]})
  self.assertTrue(page_url({'page_5':good},BOOK,5).endswith('page.jpg'))
  for mutate in ('wrongbook','wrongindex','query','otherhost'):
   bad=copy.deepcopy(good)
   if mutate=='wrongbook':bad['data']['file_id']='9'
   if mutate=='wrongindex':bad['data']['pages'][0]['page_index']=5
   if mutate=='query':bad['data']['pages'][0]['image']+='?redirect=1'
   if mutate=='otherhost':bad['data']['pages'][0]['image']='https://example.com/'+BOOK+'/p.jpg'
   with self.subTest(mutate=mutate),self.assertRaises(Hold):page_url({'page_5':bad},BOOK,5)
 def fake(self,*,failure=False,changed=False):
  outer=self;calls=[]
  class Transport:
   def __init__(self,*a):self.processes=[];self.out=outer.root
   def _capture(self,*,pages):
    calls.append(('capture',pages));flat=copy.deepcopy(outer.flat)
    if changed:flat['directory']['data']['directory_data'][0]['children'][0]['id']='changed'
    for n in pages:flat['page_'+str(n)]=response({'file_id':BOOK,'pages':[{'page_index':n-1,'image':f'https://b.aliyuncs.com/{BOOK}/{n}.png'}]})
    return flat
   def download_original(self,url):
    calls.append(('original',url))
    if failure:raise Hold('synthetic failure')
    raw=url.encode();path=outer.root/(url.rsplit('/',1)[-1]);path.write_bytes(raw)
    return {'raw_path':str(path),'raw_sha256':byte_hash(raw),'width':1,'height':1,'image_url':url}
  return Transport,calls
 def test_acquire_and_byte_verified_reuse(self):
  cls,calls=self.fake();one=acquire(self.store,{},self.plan,transport_factory=cls)
  two=acquire(self.store,{},self.plan,transport_factory=cls)
  self.assertEqual(one,two);self.assertEqual(len(calls),5);self.assertEqual(one['new_ocr_calls'],0)
  self.assertEqual([p['viewer_page'] for p in one['pages']],[5,6,80,81])
  Path(one['pages'][0]['raw_path']).write_bytes(b'changed')
  from annotation.recognition.content_review import SourceChanged
  with self.assertRaises(SourceChanged):acquire(self.store,{},self.plan,transport_factory=cls)
  self.assertEqual(len(calls),5)
 def test_first_original_failure_stops_no_retry(self):
  cls,calls=self.fake(failure=True)
  with self.assertRaises(Hold):acquire(self.store,{},self.plan,transport_factory=cls)
  self.assertEqual(len(calls),2)
  with self.assertRaises(Hold):acquire(self.store,{},self.plan,transport_factory=cls)
  self.assertEqual(len(calls),2)
  result=self.store.get(self.store.operation('platform-source',digest(self.plan))['output'])
  self.assertEqual(result['successors'],'NOT_RUN')
 def test_changed_directory_stops_before_original(self):
  cls,calls=self.fake(changed=True)
  with self.assertRaises(Hold):acquire(self.store,{},self.plan,transport_factory=cls)
  self.assertEqual(len(calls),1)
 def test_original_transport_single_read_cache_and_redirect_rejection(self):
  from PIL import Image
  buf=io.BytesIO();Image.new('RGB',(7,11),'white').save(buf,format='PNG');raw=buf.getvalue()
  t=object.__new__(UsenseTransport);t.store=self.store;t.book=BOOK;t.out=self.root;t.settings={}
  class Response(io.BytesIO):status=200
  class Opener:
   def open(self,*args,**kwargs):return Response(raw)
  with patch('urllib.request.build_opener',return_value=Opener()) as get:
   first=t.download_original('https://b.aliyuncs.com/'+BOOK+'/p.png')
   second=t.download_original('https://b.aliyuncs.com/'+BOOK+'/p.png')
   self.assertEqual(first,second);self.assertEqual(get.call_count,1)
   self.assertEqual([first['width'],first['height']],[7,11]);self.assertEqual(first['raw_sha256'],byte_hash(raw))
  with self.assertRaises(Hold):NoRedirect().redirect_request(None,None,None,None,None,None)

class SourceAuthorityR1(unittest.TestCase):
 def test_activation_binding_and_exactly_one_launch(self):
  import importlib.util,json
  from datetime import datetime,timezone,timedelta
  spec=importlib.util.spec_from_file_location('source_entry',ROOT/'tools/customer_source_once.py')
  entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);app=root/'app';(app/'tools').mkdir(parents=True);(app/'src').mkdir()
   script=app/'tools/customer_source_once.py';script.write_text('synthetic declared member',encoding='utf-8')
   def put(name,value):
    path=root/name;path.write_text(json.dumps(value),encoding='utf-8');return str(path)
   plan=scope_plan(catalog(fixture(),BOOK),'lesson')
   plan_path=put('plan.json',plan)
   settings=put('settings.json',{'profile':str(root/'profile'),'platform_enabled':True,'tls_reference':'synthetic','proxy_server':None})
   manifest=put('manifest.json',{'scope':'A30_SOURCE_ONLY','source_files':[{'path':'tools/customer_source_once.py','sha256':entry.sha(script)}]})
   now=datetime.now(timezone.utc)
   a={'schema':'A30SourceAuthority/v1','activated':False,'executor':'01a16bf6-ed2d-7950-b2c9-9df30e7e6bd6',
    'not_before':(now-timedelta(seconds=1)).isoformat(),'expires_at':(now+timedelta(seconds=300)).isoformat(),
    'manifest_path':manifest,'manifest_sha256':entry.sha(manifest),'plan_path':plan_path,'plan_sha256':entry.sha(plan_path),
    'settings_path':settings,'settings_sha256':entry.sha(settings),'book_id':BOOK,'directory_id':'lesson','profile_fingerprint':'synthetic',
    'limits':{'api_gets':7,'original_gets':4,'contexts':1,'navigations':1,'ocr':0,'saves':0,'login':0,'retries':0},'workspace':str(root/'workspace')}
   path=put('authority.json',a)
   with patch.object(entry,'ROOT',app),patch('annotation.customer.platform_source.acquire',return_value={'synthetic':True}) as resource,patch('annotation.runtime.usense_live.core.profile_identity',return_value=('synthetic','synthetic')):
    with self.assertRaisesRegex(ValueError,'EXPLICIT_ACTIVATION_REQUIRED'):entry.main(['--authority',path,'--sha256',entry.sha(path)])
    resource.assert_not_called()
    a['activated']=True;path=put('authority.json',a)
    script.write_text('changed',encoding='utf-8')
    with self.assertRaisesRegex(ValueError,'FIXED_SOURCE_CHANGED'):entry.main(['--authority',path,'--sha256',entry.sha(path)])
    resource.assert_not_called();script.write_text('synthetic declared member',encoding='utf-8')
    self.assertEqual(entry.main(['--authority',path,'--sha256',entry.sha(path)]),0)
    with self.assertRaises(FileExistsError):entry.main(['--authority',path,'--sha256',entry.sha(path)])
    self.assertEqual(resource.call_count,1)
    self.assertTrue((root/'workspace/source-round-result.json').is_file())

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
