"""Book-parameterized A26/A28 native export collector; one GET, no retry."""
import asyncio
import base64
from datetime import datetime, timezone
from .core import load_binding, owned_readonly_context, ORIGIN, TARGET, write_new, sha, require, parse, record_exception
from .capture import FETCH


def records(raw):
    parsed = []
    for number,line in enumerate(raw.decode('utf-8-sig').splitlines(),1):
        if not line.strip(): continue
        row=parse(line)
        require(type(row) is dict and isinstance(row.get('question'),str),'NATIVE_PAPER_RECORD_REQUIRED')
        parsed.append((number,row))
    require(bool(parsed),'EMPTY_NATIVE_EXPORT')
    return parsed


async def capture(config, expected_sha):
    binding=load_binding(config,expected_sha);book=binding.data['book_id']
    endpoint='/qieti/api/annotate_ocr/export-paper-questions/'+book
    require(binding.data['allowed_get']==[{'url':TARGET,'resource_types':['document'],'max_requests':1},
        {'url':ORIGIN+endpoint,'resource_types':['fetch','xhr'],'max_requests':1}],'EXACT_NATIVE_EXPORT_SCOPE')
    owner=owned_readonly_context(binding)
    result={'schema':'CustomerNativeExportCapture/v1','book_id':book,'run_id':binding.data['run_id'],
        'status':'STARTED','save_attempts':0,'login_attempts':0,'retries':0,'body_encoding':'FETCH_ARRAYBUFFER_HTTP_ENTITY_BYTES'}
    try:
        async with owner:
            await owner.page.route(TARGET,lambda route:route.fulfill(status=200,content_type='text/html',
                body='<!doctype html><title>Native export</title><link rel="icon" href="data:,">'))
            await owner.navigate();binding.check()
            write_new(binding.output/'export-request-intent.json',{'method':'GET','url':ORIGIN+endpoint,'attempts':1})
            response=await asyncio.wait_for(owner.page.evaluate(FETCH,endpoint),30)
            require(response['status']!='LOGIN_REQUIRED','LOGIN_REQUIRED_NO_LOGIN_ATTEMPT')
            raw=base64.b64decode(response.pop('body_base64'),validate=True)
            with (binding.output/'paper-questions.jsonl').open('xb') as stream:stream.write(raw)
            response.update(bytes=len(raw),sha256=sha(raw),counts={layer:owner.policy.counts.get((layer,ORIGIN+endpoint),0)
                                                                 for layer in ('context','native')})
            result['platform_export']=response
            require(response['status']==200 and not owner.policy.blocked and response['counts']=={'context':1,'native':1},'NATIVE_EXPORT_GET_FAILED')
            result['record_count']=len(records(raw));result['status']='NATIVE_EXPORT_CAPTURED_PENDING_MAPPING'
    except BaseException as exc:
        result['status']='FAILED_NO_RETRY'
        if binding.output.exists():result['error']=record_exception(binding.output,'export-error',exc,'NATIVE_EXPORT')
    finally:
        result['release']=owner.release;result['finished_at']=datetime.now(timezone.utc).isoformat()
        if binding.output.exists():write_new(binding.output/'capture-summary.json',result)
    return result
