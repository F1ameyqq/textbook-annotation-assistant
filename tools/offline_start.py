"""Relocatable, cached-source-only desktop entry; no platform configuration."""
from __future__ import annotations

import hashlib
from contextlib import closing
import json
from pathlib import Path
import socket
import sqlite3
import sys
import threading
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent
EXPECTED_SOURCE = 'cf968bfbec88f6836adf37b11a0055173b4b9bf26ee0a3b1bc089d8b0f3f1847'
sys.path[:0] = [str(ROOT / 'app' / 'src'), str(ROOT / 'app' / 'tools')]
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def offline_settings(*_):
    return {'platform_enabled': False, 'runtime': {'text_python': sys.executable,
                                                   'formula_inference_activated': False}}


def local_only_network():
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex

    def checked(self, address, *args):
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            raise RuntimeError('此包仅供离线审校，外部网络连接已关闭。')
        return original(self, address, *args)

    def checked_ex(self, address, *args):
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            raise RuntimeError('此包仅供离线审校，外部网络连接已关闭。')
        return original_ex(self, address, *args)

    socket.socket.connect = checked
    socket.socket.connect_ex = checked_ex


def locate_sources(workspace):
    original = ROOT / 'data' / 'source-cf968.sqlite'
    if sha(original) != EXPECTED_SOURCE:
        raise RuntimeError('包内原始题源数据库已变化，请重新解压完整包。')
    with closing(sqlite3.connect(original.as_uri() + '?mode=ro', uri=True)) as db:
        rows = db.execute('SELECT page,sha FROM pages ORDER BY page').fetchall()
    if [n for n, _ in rows] != list(range(1, 215)):
        raise RuntimeError('包内题源页码不完整。')
    images = {}
    for n, expected in rows:
        path = ROOT / 'data' / 'images' / f'viewer-{n:03d}.jpg'
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f'包内第 {n} 页原图缺失或已变化。')
        images[n] = str(path.resolve())
    derived = workspace / 'source-local.sqlite'
    binding_path = workspace / 'source-location.json'
    binding = json.loads(binding_path.read_text(encoding='utf-8')) if binding_path.exists() else {}
    if (binding.get('root') == str(ROOT) and binding.get('source_sha256') == EXPECTED_SOURCE
            and derived.is_file() and binding.get('derived_sha256') == sha(derived)):
        return derived, images
    temporary = workspace / ('source-local-' + uuid.uuid4().hex + '.sqlite')
    with closing(sqlite3.connect(original.as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(temporary)) as target:
            source.backup(target)
            with target:
                target.executemany('UPDATE pages SET image=? WHERE page=?',
                                   [(path, n) for n, path in images.items()])
    temporary.replace(derived)
    write_json(binding_path, {'root': str(ROOT), 'source_sha256': EXPECTED_SOURCE,
                              'derived_sha256': sha(derived), 'image_count': len(images)})
    return derived, images






def show_portal(store, result, report, *, self_test=False):
    from html import escape
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlsplit
    import webbrowser
    import customer
    from annotation.customer.review import CustomerReviewWorkspace
    from annotation.recognition.content_review_server import make_server
    customer.settings = offline_settings
    jobs = {}
    for item in result['results']:
        if not item.get('job'):
            raise RuntimeError('存在未生成审校任务的课时：' + item['scope_id'])
        job, _ = store.job(item['job'])
        jobs[job['id']] = job
    review_servers = {}
    lock = threading.Lock()
    rows = ''.join('<tr data-job="' + identity + '"><td>' + escape(job['lesson'])
                   + '</td><td>' + str(len(job['candidates'])) + '</td><td>待审校</td><td>'
                   + '<a target="_blank" href="/review?job=' + identity + '">打开审校</a> · '
                   + '<a target="_blank" href="/export?job=' + identity + '">导出</a></td></tr>'
                   for identity, job in jobs.items())
    page = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>全书离线审校 · 46007447</title><style>'
            'body{margin:36px auto;padding:0 24px;max-width:1100px;font:16px/1.7 system-ui;color:#18352f;background:#f5f8f6}'
            'h1{font-size:30px;margin-bottom:8px}p{color:#50655e}table{width:100%;border-collapse:collapse;background:white}'
            'td,th{text-align:left;padding:12px 16px;border-bottom:1px solid #dce7e1}th{background:#e7f0eb}'
            'a{color:#16664e}small{display:block;margin:12px 0 24px;color:#6f5730}</style>'
            '<h1>全书离线审校</h1><p>书 46007447 · 214 页材料 · 106 节 · 1289 个候选</p>'
            '<p>选择课时打开审校，可查看原图、修改候选并导出。材料和修改均保存在解压后的文件夹。</p>'
            '<small>当前题源仍有至少14道真题待补，候选需要逐题核对；当前并非全书完成版。</small>'
            '<table><thead><tr><th>课时</th><th>候选</th><th>状态</th><th>操作</th></tr></thead><tbody>'
            + rows + '</tbody></table></html>').encode('utf-8')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, body, content_type='text/html; charset=utf-8', download=None):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            if download:
                self.send_header('Content-Disposition', 'attachment; filename="' + download + '"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == '/':
                self.send(page)
                return
            identity = parse_qs(parsed.query).get('job', [''])[0]
            if identity not in jobs:
                self.send_error(404)
                return
            if parsed.path == '/review':
                with lock:
                    if identity not in review_servers:
                        review = make_server(CustomerReviewWorkspace(store, identity, settings_provider=lambda: offline_settings()))
                        threading.Thread(target=review.serve_forever, daemon=True).start()
                        review_servers[identity] = review
                    review = review_servers[identity]
                self.send_response(302)
                self.send_header('Location', 'http://127.0.0.1:' + str(review.server_address[1]))
                self.end_headers()
            elif parsed.path in {'/export', '/download'}:
                try:
                    output = Path(customer.export_local(store, identity))
                    if parsed.path == '/export':
                        self.send(('<!doctype html><meta charset="utf-8"><h1>课时已导出</h1><p>'
                                   + escape(jobs[identity]['lesson']) + '</p><a href="/download?job=' + identity
                                   + '&amp;kind=html">下载 HTML</a> · <a href="/download?job=' + identity
                                   + '&amp;kind=json">下载 JSON</a>').encode('utf-8'))
                    else:
                        kind = parse_qs(parsed.query).get('kind', ['html'])[0]
                        name = 'job.json' if kind == 'json' else 'index.html'
                        self.send((output / name).read_bytes(), 'application/octet-stream', name)
                except Exception as exc:
                    self.send(('<meta charset="utf-8"><p>导出暂未完成：' + escape(str(exc)) + '</p>').encode('utf-8'))
            else:
                self.send_error(404)

    for attempt in range(128):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            break
        except PermissionError:
            if attempt == 127:
                raise
    server.daemon_threads = True
    url = 'http://127.0.0.1:' + str(server.server_address[1])
    try:
        if self_test:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url, timeout=15) as response:
                body = response.read()
                if response.status != 200 or body.count(b'data-job=') != 106:
                    raise RuntimeError('离线审校列表课时数不正确。')
            report['portal'] = {'http_status': 200, 'rows': 106}
            identity = next(iter(jobs))
            with opener.open(url + '/review?job=' + identity, timeout=20) as response:
                body = response.read()
                if response.status != 200 or len(body) < 100:
                    raise RuntimeError('课时审校页面未打开。')
                report['review_page'] = {'http_status': 200, 'bytes': len(body)}
            with opener.open(url + '/export?job=' + identity, timeout=20) as response:
                response.read()
            output = Path(customer.export_local(store, identity))
            if not all((output / name).is_file() for name in ['index.html', 'job.json']):
                raise RuntimeError('样例导出文件不完整。')
            report.update(status='PASS', sample_export=str(output))
        else:
            print('离线审校已打开：' + url + '。关闭此窗口可结束本地服务。', flush=True)
            webbrowser.open(url)
            server.serve_forever()
    finally:
        if self_test:
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()
        for review in review_servers.values():
            review.shutdown()
            review.server_close()


def main():
    self_test = sys.argv[1:] == ['--self-test']
    if sys.argv[1:] and not self_test:
        raise RuntimeError('请双击 START_CUSTOMER.cmd 启动。')
    local_only_network()
    workspace = ROOT / 'workspace'
    workspace.mkdir(exist_ok=True)
    started = time.perf_counter()
    database, images = locate_sources(workspace)
    from annotation.customer.store import Store
    from annotation.customer.wholebook import prepare_book
    store = Store(workspace)
    result = prepare_book(store, database, book='46007447')
    write_json(workspace / 'offline-results.json', result)
    if (len(result['results']) != 106 or sum(x.get('candidates', 0) for x in result['results']) != 1289
            or any(x['status'] != 'NEEDS_REVIEW' for x in result['results'])
            or result['new_model_calls'] != 0 or result['platform_actions']):
        raise RuntimeError('离线候选未完整生成，请保留 workspace 中的结果。')
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        paths = [Path(p).resolve() for (p,) in db.execute('SELECT image FROM pages')]
    expected_root = (ROOT / 'data' / 'images').resolve()
    if any(p.parent != expected_root for p in paths):
        raise RuntimeError('工作副本仍引用包外图片。')
    report = {'status': 'STARTED', 'root': str(ROOT), 'python': sys.executable,
              'source_sha256': EXPECTED_SOURCE, 'original_source_unchanged': sha(ROOT / 'data/source-cf968.sqlite') == EXPECTED_SOURCE,
              'derived_database': str(database), 'images_verified': len(images), 'package_image_paths': len(paths),
              'scopes': 106, 'candidates': 1289, 'new_model_calls': 0, 'platform_actions': [],
              'self_test': self_test}
    show_portal(store, result, report, self_test=self_test)
    report['wall_seconds'] = time.perf_counter() - started
    if self_test:
        write_json(workspace / 'startup-result.json', report)
        print(json.dumps(report, ensure_ascii=True), flush=True)
        return 0 if report['status'] == 'PASS' else 2
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('离线启动失败：' + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
