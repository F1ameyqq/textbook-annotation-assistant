"""Five independent A21 boundary controls; fake memory resources only."""
import copy
import json
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase,IsolatedAsyncioTestCase
from unittest.mock import AsyncMock,Mock
ROOT=Path('D:/1800-worktrees/a21-independent-fixed')
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import a16_current_state_probe as p
from annotation.source.usense.current_readonly import gate,policy,auth
RECORDS=[]
IMAGE=gate.ORIGIN+'/assets/auth-dock.42.webp'
CANDIDATE='f0710e872776c452728e68710052c8580ae45fc4ea55cbff7fddb11a11d18657'
def enc(v):return json.dumps(v).encode('utf-8')
async def guard():
 session=NS(send=AsyncMock(return_value={'frameTree':{'frame':{'id':'INDEPENDENT_MAIN'}}}),on=Mock())
 page=NS(url=gate.LOGIN,main_frame=object(),on=Mock())
 context=NS(route=AsyncMock(),route_web_socket=AsyncMock(),new_cdp_session=AsyncMock(return_value=session))
 g=p.CurrentGuard(context,page,policy.ReadPolicy());await g.install();return g
def route(g,url=IMAGE,method='GET',kind='image',frame=None,body=None):
 req=NS(url=url,method=method,resource_type=kind,frame=g.auth_frame if frame is None else frame,redirected_from=None,post_data=body,headers={'content-type':'application/json'})
 return NS(request=req,continue_=AsyncMock(),abort=AsyncMock(),fulfill=AsyncMock())
def event(url=IMAGE,method='GET',kind='Image',body=None):
 return {'requestId':'INDEPENDENT_FETCH','networkId':'INDEPENDENT_NETWORK','frameId':'INDEPENDENT_MAIN','resourceType':kind,'request':{'url':url,'method':method,'postData':body,'headers':{'Content-Type':'application/json'}}}
class StaticControls(TestCase):
 def test_literal_URL_boundaries_and_protected_paths(self):
  good=[gate.ORIGIN+'/assets/oauth-mark.v2.svg',gate.ORIGIN+'/qieti/assets/api-2.Icon.PNG']
  bad=[IMAGE+'?',IMAGE+'#',IMAGE+';x',IMAGE.replace('/assets/','/assets/api/'),IMAGE.replace('auth-dock','%61uth-dock'),IMAGE.replace('auth-dock','auth%2fdock'),IMAGE.replace('auth-dock','auth..dock'),IMAGE.replace('www.usense.com','www.usense.com.evil.invalid'),IMAGE.replace('www.usense.com','x@www.usense.com'),IMAGE.replace('https://','https://www.usense.com@'),IMAGE.replace('/assets/','//assets/'),IMAGE.replace('/assets/','/assets/./')]
  for u in good:self.assertEqual(policy.ReadPolicy().decide('GET',u,'Image'),(True,'STATIC'))
  for u in bad:
   self.assertFalse(policy.static_image('GET',u,'Image'),u)
   self.assertFalse(policy.ReadPolicy().decide('GET',u,'Image')[0],u)
  RECORDS.append({'case':'independent_literal_boundaries','positive':len(good),'negative':len(bad)})
 def test_complete_47_scope_candidate_and_three_inert_templates(self):
  e=ROOT/'docs/evidence/A21/static-image';binding=gate.scope_binding(CANDIDATE);self.assertEqual(len(binding),47)
  candidate=json.loads((e/'candidate-manifest.json').read_bytes())
  for k,v in binding.items():
   if k!='candidate_manifest_sha256':self.assertTrue(gate.same_typed(candidate[k],v),k)
  docs={name:json.loads((e/name).read_bytes()) for name in ['activation-template-NONEXECUTABLE.json','decision-template-NONEXECUTABLE.json','independent-report-template-NONEXECUTABLE.json']}
  for name,doc in docs.items():
   for k,v in binding.items():self.assertTrue(gate.same_typed(doc[k],v),name+':'+k)
  decision=docs['decision-template-NONEXECUTABLE.json'];report=docs['independent-report-template-NONEXECUTABLE.json'];activation=docs['activation-template-NONEXECUTABLE.json']
  self.assertFalse(decision['live_authorized']);self.assertFalse(decision['direct_user_decision']);self.assertEqual(report['result'],'NOT_REVIEWED');self.assertIsNone(activation['not_before'])
  now=datetime(2026,10,21,2,tzinfo=timezone.utc)
  def validate(d,r):
   a=copy.deepcopy(activation);a.update(not_before=now.isoformat(),expires_at=(now+timedelta(seconds=900)).isoformat(),user_decision_sha256=gate.sha(enc(d)),independent_report_sha256=gate.sha(enc(r)))
   return gate.validate_activation(enc(a),gate.sha(enc(a)),CANDIDATE,gate.PROFILE_FINGERPRINT,enc(d),enc(r),explicit_live=True,exception=True,now=now)
  with self.assertRaises(gate.Stop):validate(decision,report)
  d=copy.deepcopy(decision);d.update(live_authorized=True,certificate_exception_authorized=True,direct_user_decision=True,login_submission_authorized=True,credential_transmission_authorized=True,credential_tls_exception_authorized=True,authorization_basis='DIRECT_A21_USER_DECISION')
  r=copy.deepcopy(report);r['result']='ACCEPTED_OFFLINE_ONLY'
  self.assertTrue(validate(d,r).ignore_https_errors)
  for key,value in [('authorization_basis','DIRECT_A20_USER_DECISION'),('run_id','A20-spent'),('decision_path','D:/1800/docs/approvals/A20-authenticated-source-user-decision.json')]:
   bad=copy.deepcopy(d);bad[key]=value
   with self.assertRaises(gate.Stop):validate(bad,r)
  RECORDS.append({'case':'complete_scope_and_templates','scope_fields':47,'template_field_comparisons':141,'candidate_fields':46,'inert_templates_rejected':True,'old_identity_authority_mutations_rejected':3})
class BarrierControls(IsolatedAsyncioTestCase):
 async def test_equal_but_not_identical_context_frame_cannot_send(self):
  class EqualFrame:
   def __eq__(self,other):return True
  g=await guard();r=route(g,frame=EqualFrame());await g.route(r)
  r.continue_.assert_not_awaited();r.abort.assert_awaited_once();self.assertTrue(g.stopped)
  g=await guard();g.page.main_frame=EqualFrame();await g.paused(event())
  self.assertEqual(g.session.send.await_args.args[0],'Fetch.failRequest');self.assertTrue(g.stopped)
  RECORDS.append({'case':'identity_not_equality','context_and_native_denied':2})
 async def test_one_guard_image_then_one_login_across_both_layers(self):
  g=await guard();r=route(g);await g.route(r);await g.paused(event());r.continue_.assert_awaited_once()
  self.assertEqual(g.auth.login_counts,{'context':0,'native':0})
  credentials=auth.Secrets('INDEPENDENT_FAKE_USER','INDEPENDENT_FAKE_PASSWORD');body=enc({'username':credentials.username,'password':credentials.password}).decode()
  g.auth.form_validated=True;g.auth.arm_submit(credentials)
  r=route(g,gate.LOGIN_POST,'POST','fetch',body=body);await g.route(r);r.continue_.assert_awaited_once()
  await g.paused(event(gate.LOGIN_POST,'POST','Fetch',body));self.assertEqual(g.session.send.await_args.args[0],'Fetch.continueRequest')
  self.assertEqual(g.auth.login_counts,{'context':1,'native':1});self.assertFalse(g.stopped)
  await g.paused(event(gate.LOGIN_POST,'POST','Fetch',body));self.assertEqual(g.session.send.await_args.args[0],'Fetch.failRequest');self.assertTrue(g.stopped)
  RECORDS.append({'case':'same_guard_login_two_barriers','counts':g.auth.login_counts,'duplicate_native_denied':True})
 async def test_image_does_not_reset_or_consume_shared_exclusion_bound(self):
  g=await guard();r=route(g);await g.route(r);await g.paused(event());self.assertEqual(g.excluded_static_events,0)
  for index in range(16):
   v=g.classify('GET','https://cdn.bootcdn.net/a.js','Script',False,True);self.assertEqual(v,(False,policy.EXCLUDED_STATIC,True))
  self.assertEqual(g.excluded_static_events,16)
  r=route(g);await g.route(r);r.continue_.assert_awaited_once();self.assertEqual(g.excluded_static_events,16)
  self.assertEqual(g.classify('GET','https://cdn.bootcdn.net/a.js','Script',False,True),(False,'EXCLUDED_STATIC_EVENT_LIMIT',False))
  g.denied('EXCLUDED_STATIC_EVENT_LIMIT');r=route(g);await g.route(r);r.continue_.assert_not_awaited();r.abort.assert_awaited_once()
  RECORDS.append({'case':'image_preserves_shared_exclusion_bound','accepted_excluded_denials':16,'seventeenth_fatal':True,'image_after_stop_denied':True})
