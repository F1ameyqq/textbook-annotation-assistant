"""Source-bound immutable assets and transactional, revisioned local drafts."""
import base64
from contextlib import contextmanager
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from PIL import Image
from .detect import detect

SCHEMA = 'b-prebox-draft/0.1'
COORDINATES = 'ORIGINAL_PIXELS_HALF_OPEN'
KINDS = {'candidate', 'question', 'stem', 'option', 'answer', 'explanation', 'figure', 'table', 'ignore'}
ORIGINS = {'AUTO_GEOMETRY', 'MANUAL', 'IMPORTED_DRAFT'}
MAX_IMAGE = 25 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_PAGES = 100
MAX_WORKSPACE_BYTES = 36 * 1024 * 1024


class ConflictError(ValueError):
    pass


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('重复JSON字段')
        result[key] = value
    return result


def read_json(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('无效数值')))


def image_info(raw):
    if not raw or len(raw) > MAX_IMAGE:
        raise ValueError('每张图片须小于25MB')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            if image.format not in {'PNG', 'JPEG'} or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('仅支持单帧PNG/JPEG书页')
            if width < 2 or height < 2 or width*height > MAX_PIXELS:
                raise ValueError('书页须至少2×2，且不超过4000万像素')
            if image.getexif().get(274, 1) != 1:
                raise ValueError('请先将带EXIF旋转的图片转正另存后导入')
            image.load()
            return width, height, 'png' if image.format == 'PNG' else 'jpg'
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError('图片无法完整解码') from exc


def validate_boxes(boxes, width, height, ids):
    if not isinstance(boxes, list) or len(boxes) > 5000:
        raise ValueError('每页最多5000个草稿框')
    result = []
    for box in boxes:
        if not isinstance(box, dict) or set(box) != {'box_id', 'bbox', 'kind', 'origin', 'status'}:
            raise ValueError('草稿框字段不完整或包含未知字段')
        identity = box['box_id']
        if not isinstance(identity, str) or not 1 <= len(identity) <= 100 or identity in ids:
            raise ValueError('框ID无效或重复')
        ids.add(identity)
        bbox = box['bbox']
        if (not isinstance(bbox, list) or len(bbox) != 4 or
                not all(type(v) in (int, float) and math.isfinite(v) for v in bbox)):
            raise ValueError('坐标必须是四个有限数值')
        x0, y0, x1, y1 = bbox
        if not (0 <= x0 <= x1-2 <= width-2 and 0 <= y0 <= y1-2 <= height-2):
            raise ValueError('框必须在原图内，最小2×2像素')
        if box['kind'] not in KINDS or box['origin'] not in ORIGINS or box['status'] != 'DRAFT':
            raise ValueError('未知类型/来源，或试图核准草稿')
        result.append(copy.deepcopy(box))
    return result


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root/'assets').mkdir(exist_ok=True)
        self.db = self.root/'drafts.sqlite3'
        self.lock = threading.RLock()
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS revisions (revision INTEGER PRIMARY KEY, pages BLOB NOT NULL, digest TEXT NOT NULL, created TEXT NOT NULL, action TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('schema', SCHEMA))
            db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('workspace_id', str(uuid.uuid4())))
            if db.execute("SELECT value FROM meta WHERE key='schema'").fetchone()[0] != SCHEMA:
                raise ValueError('工作区版本不兼容，请使用新目录')
            db.execute('INSERT OR IGNORE INTO revisions VALUES (?,?,?,?,?)',
                       (0, encode([]), sha(encode([])), self._now(), 'INITIAL'))
        self.state()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _read(self, db, revision=None):
        row = db.execute('SELECT revision,pages,digest FROM revisions '+
                         ('ORDER BY revision DESC LIMIT 1' if revision is None else 'WHERE revision=?'),
                         () if revision is None else (revision,)).fetchone()
        if row is None or sha(row[1]) != row[2]:
            raise ValueError('版本不存在或快照已损坏')
        return row[0], read_json(row[1])

    def _assets_valid(self, pages):
        seen, ids, total_bytes = set(), set(), 0
        for page in pages:
            if page['page_id'] in seen or page['page_id'] != 'page-'+page['sha256']:
                raise ValueError('页面身份重复或错误')
            seen.add(page['page_id'])
            raw = self._asset_path(page).read_bytes()
            total_bytes += len(raw)
            if sha(raw) != page['sha256']:
                raise ValueError('原图SHA已改变，拒绝套用旧框')
            validate_boxes(page['boxes'], page['width'], page['height'], ids)
        if total_bytes > MAX_WORKSPACE_BYTES or len(ids) > 10000:
            raise ValueError('演示工作区原图总量限36MB、总框数限10000，请拆成多个工作区以保证JSON可重导入')

    def _asset_path(self, page):
        path = (self.root/page['asset_path']).resolve()
        if not path.is_relative_to((self.root/'assets').resolve()):
            raise ValueError('来源路径越界')
        return path

    def state(self):
        with self.lock, self._connect() as db:
            revision, pages = self._read(db)
            self._assets_valid(pages)
            workspace_id = db.execute("SELECT value FROM meta WHERE key='workspace_id'").fetchone()[0]
        return dict(schema_version=SCHEMA, coordinate_space=COORDINATES, workspace_id=workspace_id,
                    revision=revision, decision='HOLD', human_verified=False, platform_actions=[], pages=pages)

    def _commit(self, expected_revision, operation, action):
        with self.lock, self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            revision, pages = self._read(db)
            if type(expected_revision) is not int or expected_revision != revision:
                raise ConflictError('版本已变化，请保留草稿并刷新工作区')
            self._assets_valid(pages)
            result = operation(copy.deepcopy(pages), db)
            if len(result) > MAX_PAGES:
                raise ValueError('演示版最多100页')
            self._assets_valid(result)
            raw = encode(result)
            db.execute('INSERT INTO revisions VALUES (?,?,?,?,?)',
                       (revision+1, raw, sha(raw), self._now(), action))

    def _image_page(self, name, data):
        try:
            raw = base64.b64decode(data, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError('图片Base64无效') from exc
        width, height, ext = image_info(raw)
        digest = sha(raw)
        path = self.root/'assets'/(digest+'.'+ext)
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError('已存来源发生损坏')
        else:
            # A failed transaction may leave an unreferenced blob; never a committed revision.
            with path.open('xb') as stream:
                stream.write(raw)
        return dict(page_id='page-'+digest, name=Path(str(name).replace('\\', '/')).name[:200] or '书页',
                    sha256=digest, width=width, height=height,
                    asset_path='assets/'+path.name, boxes=[], detector=None)

    def import_images(self, files, expected_revision):
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_PAGES:
            raise ValueError('请选择1至100张图片')
        def operation(pages, _):
            seen = {p['page_id'] for p in pages}
            for file in files:
                if not isinstance(file, dict) or set(file) != {'name', 'data_base64'}:
                    raise ValueError('图片导入字段错误')
                page = self._image_page(file['name'], file['data_base64'])
                if page['page_id'] in seen:
                    continue
                page['boxes'], page['detector'] = detect(self._asset_path(page).read_bytes(), page['sha256'])
                pages.append(page)
                seen.add(page['page_id'])
            return pages
        self._commit(expected_revision, operation, 'IMPORT_IMAGES_GEOMETRY')

    def save(self, incoming, expected_revision):
        def operation(pages, _):
            if not isinstance(incoming, list) or len(incoming) != len(pages):
                raise ValueError('页面数量不一致')
            ids = set()
            for old, new in zip(pages, incoming):
                if not isinstance(new, dict) or set(new) != {'page_id', 'sha256', 'width', 'height', 'boxes'}:
                    raise ValueError('保存字段错误')
                if any(new[k] != old[k] for k in ('page_id', 'sha256', 'width', 'height')):
                    raise ValueError('页面身份/尺寸变化，拒绝套用旧框')
                boxes = validate_boxes(new['boxes'], old['width'], old['height'], ids)
                previous = {box['box_id']: box for box in old['boxes']}
                for box in boxes:
                    prior = previous.get(box['box_id'])
                    if prior is None or box['bbox'] != prior['bbox'] or box['kind'] != prior['kind']:
                        box['origin'] = 'MANUAL'
                    else:
                        box['origin'] = prior['origin']
                old['boxes'] = boxes
            return pages
        self._commit(expected_revision, operation, 'SAVE_DRAFT')

    def asset_bytes(self, page_id):
        page = next((p for p in self.state()['pages'] if p['page_id'] == page_id), None)
        if page is None:
            raise ValueError('页面不存在')
        raw = self._asset_path(page).read_bytes()
        if sha(raw) != page['sha256']:
            raise ValueError('原图SHA不一致')
        return raw

    def export_document(self):
        state = self.state()
        pages = []
        for page in state['pages']:
            item = {k: copy.deepcopy(page[k]) for k in ('page_id', 'name', 'sha256', 'width', 'height', 'boxes')}
            raw = self._asset_path(page).read_bytes()
            if sha(raw) != page['sha256']:
                raise ValueError('导出时原图SHA不一致')
            item['image_base64'] = base64.b64encode(raw).decode('ascii')
            pages.append(item)
        return dict(schema_version=SCHEMA, coordinate_space=COORDINATES, decision='HOLD',
                    human_verified=False, pages=pages)

    def import_document(self, document, expected_revision):
        if isinstance(document, str):
            document = read_json(document)
        if (not isinstance(document, dict) or
                set(document) != {'schema_version', 'coordinate_space', 'decision', 'human_verified', 'pages'} or
                document['schema_version'] != SCHEMA or document['coordinate_space'] != COORDINATES or
                document['decision'] != 'HOLD' or document['human_verified'] is not False or
                not isinstance(document['pages'], list) or len(document['pages']) > MAX_PAGES):
            raise ValueError('JSON版本、坐标系或草稿状态不兼容')
        def operation(_, db):
            pages, seen, ids = [], set(), set()
            for item in document['pages']:
                if not isinstance(item, dict) or set(item) != {'page_id', 'name', 'sha256', 'width', 'height', 'boxes', 'image_base64'}:
                    raise ValueError('JSON页面字段错误')
                page = self._image_page(item['name'], item['image_base64'])
                if any(item[k] != page[k] for k in ('page_id', 'sha256', 'width', 'height')) or page['page_id'] in seen:
                    raise ValueError('JSON来源身份/尺寸不匹配或重复')
                seen.add(page['page_id'])
                page['boxes'] = validate_boxes(item['boxes'], page['width'], page['height'], ids)
                for box in page['boxes']:
                    box['origin'] = 'IMPORTED_DRAFT'
                page['detector'] = dict(method='IMPORTED_SOURCE_BOUND_DRAFT', ocr_enabled=False,
                                        can_identify_complete_questions=False)
                pages.append(page)
            return pages
        self._commit(expected_revision, operation, 'IMPORT_JSON')

    def history(self):
        with self._connect() as db:
            return [dict(revision=r, created=t, action=a) for r, t, a in
                    db.execute('SELECT revision,created,action FROM revisions ORDER BY revision DESC')]

    def restore(self, revision, expected_revision):
        if type(revision) is not int:
            raise ValueError('历史版本无效')
        def operation(_, db):
            return self._read(db, revision)[1]
        self._commit(expected_revision, operation, 'RESTORE_'+str(revision))
