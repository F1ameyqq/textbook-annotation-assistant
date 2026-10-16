"""A05 reviewer: one UI book selection, GET-only business readback, then close.

Run only after the executor report and release certificate are present.
Never executes the writer's command queue or any save/OCR action.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl, urlencode

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
OUT = ROOT / 'docs/evidence/A05/review'
sys.path.insert(0, str(ROOT / 'tools'))
from usense_login import load_credentials, VIEWER_URL, VIEWER_MARKER, verify_viewer
from playwright.sync_api import sync_playwright

BOOK = '46007447'
for name in ('DEBUG', 'PWDEBUG'):
    os.environ.pop(name, None)

def now():
    return datetime.now(timezone.utc).isoformat()

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def clean(data):
    if isinstance(data, dict):
        return {k: clean(v) for k, v in data.items()
                if k.lower() not in {'created_by','updated_by','claimer','team_name','accessid','signature','policy'}
                and not any(x in k.lower() for x in ('token', 'password', 'authorization', 'cookie', 'username', 'user_name', 'user_id', 'phone', 'email'))}
    if isinstance(data, list):
        return [clean(v) for v in data]
    return data

def safe_url(url):
    p = urlsplit(url)
    keys = {'file_id', 'fileId', 'pageNum', 'annotationType', 'question_order', 'zone', 'page', 'pageSize'}
    q = urlencode([(k, v) for k, v in parse_qsl(p.query) if k in keys])
    return p.scheme + '://' + p.netloc + p.path + ('?' + q if q else '')

def book_subset(data):
    rows = []
    def walk(x):
        if isinstance(x, dict):
            if str(x.get('id')) == BOOK:
                keep = {'id','title','ISBN','status','page_count','question_count','processing_status','duplicateCheckStatus','reviewed_at','delivered_at','delivery_submitted_at'}
                rows.append({k: v for k, v in x.items() if k in keep})
            else:
                for v in x.values():
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return {'code': data.get('code'), 'target_books': rows}

def main():
    release_path = ROOT / 'docs/evidence/A05/execution/session-release.json'
    report_path = ROOT / 'docs/tasks/A05-execution-report.md'
    if not report_path.is_file() or not release_path.is_file():
        raise RuntimeError('executor report or release certificate missing')
    release = json.loads(release_path.read_text(encoding='utf-8-sig'))
    if release.get('released') is not True:
        raise RuntimeError('executor release is not confirmed')
    if release.get('pending_write') or release.get('unknown_save') or release.get('matching_active_process_count') != 0:
        raise RuntimeError('executor still has pending or active state')
    credentials = load_credentials()
    profile = ROOT / '.local/browser-profiles' / hashlib.sha256(credentials.username.encode()).hexdigest()[:20]
    del credentials
    process_query = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(msedge|python|pythonw)\\.exe$' } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    probe = subprocess.run(['powershell.exe','-NoProfile','-Command',process_query],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if probe.returncode != 0:
        raise RuntimeError('process exclusivity could not be checked')
    processes = json.loads(probe.stdout) if probe.stdout.strip() else []
    if isinstance(processes, dict):
        processes = [processes]
    matched = []
    for proc in processes:
        command = (proc.get('CommandLine') or '').replace('\\','/').lower()
        if str(profile).replace('\\','/').lower() in command or '/stages/a05/session.py' in command or '/stages/a05/reopen_session.py' in command:
            matched.append(proc['ProcessId'])
    save('independent-preflight.json', {'at':now(), 'executor_release_confirmed':True,'report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'matching_active_process_count':len(matched),'matching_active_process_ids':matched,'read_only_get_guard':True})
    if matched:
        raise RuntimeError('profile or writer is still active')
    events = []
    blocked = []
    started = now()
    closed = False
    def guard(route):
        req = route.request
        if req.method not in ('GET', 'HEAD', 'OPTIONS'):
            blocked.append({'at': now(), 'method': req.method, 'url': safe_url(req.url)})
            save('blocked-requests.json', blocked)
            route.abort('blockedbyclient')
        else:
            route.continue_()
    def capture(response):
        p = urlsplit(response.url)
        if not p.path.startswith('/qieti/api/') or any(x in p.path.lower() for x in ('login', 'token', 'refresh', 'user')):
            return
        record = {'index': len(events) + 1, 'at': now(), 'url': safe_url(response.url), 'method': response.request.method, 'http_status': response.status}
        events.append(record)
        try:
            data = response.json()
            if p.path.endswith('/claim_book/books'):
                data = book_subset(data)
            else:
                data = clean(data)
            name = 'independent-response-%04d.json' % record['index']
            save(name, data)
            record['body_file'] = name
        except Exception:
            record['body_available'] = False
        save('independent-network.json', events)
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(str(profile), channel='msedge', headless=True,
                viewport={'width':1600, 'height':1100}, accept_downloads=False, ignore_https_errors=True, service_workers='block', timeout=30000)
            try:
                context.route('**/*', guard)
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(20000)
                page.on('response', capture)
                page.on('dialog', lambda d: d.dismiss())
                page.goto(VIEWER_URL, wait_until='domcontentloaded', timeout=45000)
                page.locator(VIEWER_MARKER + ', input[placeholder="请输入密码"]:visible').first.wait_for(state='visible', timeout=30000)
                if not verify_viewer(page):
                    raise RuntimeError('authenticated viewer not confirmed')
                page.get_by_role('button', name='选择书籍', exact=True).click()
                target_row = page.locator('.el-table__row').filter(has_text=BOOK)
                target_row.wait_for(state='visible', timeout=20000)
                target_row.get_by_role('button', name='选择', exact=True).click()
                page.wait_for_timeout(3500)
                visible = page.locator('body').inner_text()
                if BOOK not in visible:
                    raise RuntimeError('target book not visibly confirmed')
                old_ids = {r['rect_id'] for r in json.loads((ROOT / 'docs/evidence/A05/baseline/annotations.json').read_text(encoding='utf-8-sig'))['data']}
                annotation_events = [e for e in events if '/get_manual_annotations_unified/' in e['url'] and e.get('body_file')]
                if not annotation_events:
                    raise RuntimeError('page did not read all annotations')
                latest = json.loads((OUT / annotation_events[-1]['body_file']).read_text(encoding='utf-8-sig'))
                if latest.get('code') != 0:
                    raise RuntimeError('annotation business read failed')
                persisted_crops = []
                for row in latest['data']:
                    if row['rect_id'] in old_ids:
                        continue
                    url = row['image_path']
                    parsed = urlsplit(url)
                    if parsed.scheme != 'https' or '/annotate_images/' + BOOK + '/' not in parsed.path:
                        raise RuntimeError('unexpected crop source')
                    response = context.request.get(url)
                    if response.status != 200:
                        raise RuntimeError('persisted crop unavailable')
                    content = response.body()
                    name = 'independent-persisted-' + row['type'] + '.jpg'
                    (OUT / name).write_bytes(content)
                    persisted_crops.append({'rect_id':row['rect_id'], 'role':row['type'], 'file':name,
                        'sha256':hashlib.sha256(content).hexdigest(), 'http_status':response.status, 'source_url':safe_url(url)})
                save('independent-persisted-crops.json', persisted_crops)
                receipt = json.loads((ROOT / 'docs/evidence/A05/execution/commit-receipt.json').read_text(encoding='utf-8-sig'))
                node = receipt['data']['inserted_question_node']
                if node.get('order_in_level') != '22' or not node.get('isQuestion'):
                    raise RuntimeError('unexpected review question node')
                page.locator('[data-node-id="' + node['id'] + '"]').click()
                page.wait_for_timeout(3000)
                visible = page.locator('body').inner_text()
                endpoints = {
                    'independent-question-info22.json':'/qieti/api/annotate_pic/get_question_info/46007447/22',
                    'independent-question22.json':'/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/22',
                    'independent-ocr-question22.json':'/qieti/api/verify_annotation/get-ocr-annotation?file_id=46007447&question_order=22&zone=question',
                    'independent-ocr-answer22.json':'/qieti/api/verify_annotation/get-ocr-annotation?file_id=46007447&question_order=22&zone=answer',
                    'independent-source-page14.json':'/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=mr_pre',
                    'independent-source-page173.json':'/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=173&annotationType=mr_pre',
                }
                # Authentication stays inside the page; only fixed GET response bodies leave it.
                for name, endpoint in endpoints.items():
                    result = page.evaluate('''async url => {
                        const auth = JSON.parse(localStorage.getItem('user') || '{}');
                        const response = await fetch(url, {method:'GET', headers:{Authorization:'Bearer '+auth.access_token}});
                        return {http_status:response.status, body:await response.json()};
                    }''', endpoint)
                    save(name, clean(result['body']))
                    if result['http_status'] != 200 or result['body'].get('code') != 0:
                        raise RuntimeError('fixed business GET failed')
                plan = json.loads((ROOT / 'docs/evidence/A05/execution/write-plan.json').read_text(encoding='utf-8-sig'))
                originals = []
                for frame in plan['frames']:
                    source = json.loads((OUT / ('independent-source-page' + str(frame['viewer_page']) + '.json')).read_text(encoding='utf-8-sig'))
                    source_page = source['data']['pages'][0]
                    url = source_page['image']
                    if urlsplit(url).scheme != 'https' or '/upload_images/' + BOOK + '/' not in urlsplit(url).path:
                        raise RuntimeError('unexpected original source')
                    response = context.request.get(url)
                    if response.status != 200:
                        raise RuntimeError('original source unavailable')
                    content = response.body()
                    name = 'independent-original-' + frame['role'] + '.jpg'
                    (OUT / name).write_bytes(content)
                    originals.append({'file':name,'role':frame['role'],'viewer_page':frame['viewer_page'],
                        'source_index':source_page.get('page_index'),'planned_source_index':frame['source_index'],
                        'sha256':hashlib.sha256(content).hexdigest(),'matches_plan_sha256':hashlib.sha256(content).hexdigest()==frame['sha256'],
                        'source_url':safe_url(url),'http_status':response.status})
                save('independent-originals.json', originals)
                save('independent-ui-summary.json', {'at':now(), 'target_book':BOOK, 'authenticated_viewer':verify_viewer(page),
                    'target_visibly_confirmed':True, 'rect_box_count_in_view':page.locator('.rect-box').count(),
                    'selected_question_node_id':node['id'], 'selected_question_order':'22', 'fill_question_type_text_visible':'填空' in visible,
                    'screenshot_viewport':[1600,1100], 'screenshot_clip':[0,50,1600,1050],
                    'canvases':page.locator('canvas').evaluate_all('els => els.map(e=>({width:e.width,height:e.height}))'),
                    'non_get_business_requests_allowed':False})
                page.screenshot(path=str(OUT / 'independent-reopen.png'), clip={'x':0,'y':50,'width':1600,'height':1000})
                save('independent-run-result.json', {'status':'READBACK_CAPTURED','started_at':started,'finished_at':now(), 'network_events':len(events),'blocked_requests':len(blocked)})
            finally:
                context.close()
                closed = True
    finally:
        save('session-release.json', {'released':closed, 'closed_at':now(), 'read_only':True, 'pid':os.getpid(), 'pending_write_actions':False,
            'blocked_request_count':len(blocked), 'executor_release_sha256':hashlib.sha256(release_path.read_bytes()).hexdigest()})

if __name__ == '__main__':
    try:
        main()
        print('A05_INDEPENDENT_READBACK_CLOSED')
    except Exception as exc:
        save('independent-error.json', {'at':now(), 'error_type':type(exc).__name__})
        print('A05_INDEPENDENT_READBACK_BLOCKED: ' + type(exc).__name__)
        sys.exit(2)
