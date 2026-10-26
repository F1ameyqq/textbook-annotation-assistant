"""Rebuild a private offline bundle without launching it or copying old state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
from contextlib import closing
import uuid
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-package', type=Path, required=True,
                        help='Previously repaired self-contained folder; reuse only runtime and launcher.')
    parser.add_argument('--runtime-source', type=Path,
                        help='Known working portable Python folder; defaults to base-package/python.')
    parser.add_argument('--app', type=Path, required=True, help='New frozen application source folder.')
    parser.add_argument('--output-dir', type=Path, default=Path.cwd() / 'outputs')
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--database-sha256', required=True)
    parser.add_argument('--candidates', type=int, required=True)
    parser.add_argument('--scopes', type=int, default=106)
    parser.add_argument('--missing-questions', type=int)
    parser.add_argument('--freeze-manifest', type=Path,
                        help='Optional exact key_source_sha256 mapping from the executor freeze.')
    parser.add_argument('--name', required=True, help='New output folder basename, never an existing output.')
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    workspace = output_dir.parent
    if Path(args.name).name != args.name or args.name in {'.', '..'}:
        raise ValueError('Output name must be a simple folder basename.')
    target = output_dir / args.name
    archive = target.with_suffix('.zip')
    if target.exists() or archive.exists():
        raise FileExistsError('Existing packages are preserved; choose a new name.')
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = args.database_sha256.lower()
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected) or sha(args.database) != expected:
        raise ValueError('Source SQLite does not match the supplied frozen hash.')
    base = args.base_package.resolve(strict=True)
    base_meta = json.loads((base / 'bundle.json').read_text(encoding='utf-8'))
    app = args.app.resolve(strict=True)
    source_files = {p.relative_to(app).as_posix(): p.read_bytes()
                    for sub in ['src', 'tools'] for p in (app / sub).rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    for name in ['requirements-b.txt', 'requirements-customer.txt', 'constraints-customer.txt']:
        source_files[name] = (app / name).read_bytes()
    key_paths = ['src/annotation/customer/wholebook.py', 'src/annotation/customer/prepare.py', 'tools/customer.py']
    key_hashes = {name: hashlib.sha256(source_files[name]).hexdigest() for name in key_paths}
    if args.freeze_manifest:
        frozen = json.loads(args.freeze_manifest.read_text(encoding='utf-8'))
        frozen = frozen.get('key_source_sha256', frozen)
        if any(key_hashes[name] != frozen[name].lower() for name in key_paths):
            raise ValueError('Application source does not match the executor freeze.')
    stage = workspace / 'work' / ('bundle-build-' + uuid.uuid4().hex)
    stage.mkdir()
    for name, content in source_files.items():
        path = stage / 'app' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    runtime = args.runtime_source.resolve(strict=True) if args.runtime_source else base / 'python'
    shutil.copytree(runtime, stage / 'python')
    subprocess.run([str(stage / 'python' / 'python.exe'), '-I', '-B', '-X', 'utf8',
                    '-c', 'import PIL.Image, numpy, sqlite3'], check=True, timeout=30)
    data = stage / 'data'
    (data / 'images').mkdir(parents=True)
    shutil.copy2(args.database, data / 'source.sqlite')
    with closing(sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        pages = db.execute('SELECT page,image,sha FROM pages ORDER BY page').fetchall()
    if [row[0] for row in pages] != list(range(1, 215)):
        raise ValueError('Expected all 214 source pages.')
    for n, original_path, digest in pages:
        source = Path(original_path)
        if not source.is_file():
            source = base / 'data' / 'images' / f'viewer-{n:03d}.jpg'
        destination = data / 'images' / f'viewer-{n:03d}.jpg'
        shutil.copy2(source, destination)
        if sha(destination) != digest:
            raise ValueError('Image hash mismatch: ' + str(n))
    launcher = ('@echo off\r\nchcp 65001 >nul\r\nsetlocal\r\n'
                '"%~dp0python\\python.exe" -I -B -X utf8 "%~dp0app\\tools\\customer.py" offline %*\r\n'
                'set "A30_EXIT=%ERRORLEVEL%"\r\n'
                'if not "%A30_EXIT%"=="0" pause\r\nexit /b %A30_EXIT%\r\n')
    (stage / 'START_CUSTOMER.cmd').write_bytes(launcher.encode('utf-8'))
    for name, key in [('graphic-review.json', 'graphic_review_sha256'),
                      ('graphic-preview.html', 'graphic_preview_sha256')]:
        source = base / 'data' / name
        if key in base_meta:
            if not source.is_file() or sha(source) != base_meta[key]:
                raise ValueError('Bundled graphic source changed: ' + name)
            shutil.copy2(source, data / name)
    meta = {'scope': 'SELF_CONTAINED_WINDOWS_X64_OFFLINE_REVIEW', 'book_id': '46007447',
            'source_database_sha256': expected, 'key_source_sha256': key_hashes,
            'python_entry': 'app/tools/customer.py offline', 'images': 214,
            'graphic_review_sha256': base_meta.get('graphic_review_sha256'),
            'graphic_preview_sha256': base_meta.get('graphic_preview_sha256'),
            'runtime_included': True, 'credentials_or_profiles_included': False,
            'old_workspace_included': False, 'candidate_count': args.candidates,
            'scope_count': args.scopes, 'known_missing_questions': args.missing_questions,
            'source_index_complete': False, 'entry': 'START_CUSTOMER.cmd',
            'interface': 'LOCAL_BROWSER_OFFLINE_PORTAL', 'startup_check': 'NOT_RUN_THIS_BUILD'}
    (stage / 'bundle.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (stage / '使用说明.txt').write_text(
        '完整解压后双击 START_CUSTOMER.cmd。首次启动会准备来源材料，随后在本机浏览器打开统一入口。\n'
        '首页可切换首批50个和第51–100个来源实例（含例题、变式）：逐条打开课时审校、查看214页原图、改框、人工核对题答、确认，并可导出课时结果。\n'
        '“已审校待平台核对”和“已核对可保存”分别显示；新包不含旧平台账本，不会把本地未执行冒充线上不存在。\n'
        '逐题批次预演只生成本地计划，不执行平台保存。材料与修改保存在解压目录的 workspace；关闭启动窗口可结束本地服务。\n'
        '来源候选仍需逐题核对，本包不是全书最终完成版。请勿公开推送原图或题源。\n', encoding='utf-8')
    if (sha(args.database) != expected
            or any((app / name).read_bytes() != content for name, content in source_files.items())):
        raise ValueError('Source changed while building; staging files retained in work.')
    if (stage / 'workspace').exists():
        raise ValueError('A clean bundle must not contain an existing workspace.')
    temporary_zip = stage.with_suffix('.zip')
    with zipfile.ZipFile(temporary_zip, 'x', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                z.write(path, Path(args.name) / path.relative_to(stage))
    if not target.resolve().is_relative_to(workspace) or not stage.resolve().is_relative_to(workspace):
        raise ValueError('Package move leaves the intended workspace.')
    stage.rename(target)
    temporary_zip.rename(archive)
    print(json.dumps({'package': str(archive), 'bytes': archive.stat().st_size,
                      'sha256': sha(archive), 'key_source_sha256': key_hashes,
                      'application_started': False}, ensure_ascii=True))


if __name__ == '__main__':
    main()
