"""Independent frozen-data checks; no author code, product import or network."""
import hashlib
import json
import ntpath
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from PIL import Image, ImageChops, ImageStat

PUBLIC = Path('D:/1800/docs/evidence/A28-independent/content-v1-review')
PRIVATE = Path('D:/1800/.local/stages/a28-independent-20261023/content-v1-review')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(path):
    return ntpath.normcase(ntpath.normpath(path))


intake = json.loads((PUBLIC / 'intake.json').read_bytes())
remote_intake = json.loads((PUBLIC / 'remote-intake.json').read_bytes())
members = intake['members'] + remote_intake['members']
mapping = {norm(m['source']): m for m in members}
assert len(mapping) == 83
for m in members:
    data = Path(m['copy']).read_bytes()
    assert len(data) == m['bytes'] and sha(data) == m['sha256']


def read_source(path):
    return Path(mapping[norm(path)]['copy']).read_bytes()


def obj(path):
    return json.loads(read_source(path))


def file_named(name, remote=False):
    group = remote_intake['members'] if remote else intake['members']
    matches = [m for m in group if ntpath.basename(m['source']) == name]
    assert len(matches) == 1, name
    return matches[0]


refs = []


def verify_refs(value, owner):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            member = mapping[norm(value['path'])]
            assert value['sha256'] == member['sha256'], (owner, value['path'])
            if 'bytes' in value:
                assert value['bytes'] == member['bytes']
            refs.append({'owner': owner, 'source': value['path'], 'sha256': value['sha256']})
        for child in value.values():
            verify_refs(child, owner)
    elif isinstance(value, list):
        for child in value:
            verify_refs(child, owner)


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


bundle = obj(file_named('bundle-manifest.json')['source'])
assert file_named('bundle-manifest.json')['sha256'] == intake['bundle_manifest_sha256']
verify_refs(bundle, 'bundle-manifest')
sources = {s['viewer_page']: s for s in bundle['sources']}
source_images = {}
for page, source in sources.items():
    im = Image.open(mapping[norm(source['path'])]['copy']).convert('RGB')
    im.load()
    assert list(im.size) == source['dimensions']
    source_images[page] = im
    metadata = obj(source['current_metadata']['path'])
    assert metadata['code'] == 0 and metadata['data']['file_id'] == '46007447'
    entry = metadata['data']['pages'][0]
    assert entry['page_index'] == page - 1
    assert entry['image'] == source['official_image_url']
    url = urlsplit(entry['image'])
    assert url.scheme == 'https' and not url.query and not url.fragment
    assert url.path == '/upload_images/46007447/46007447_page_%d.jpg' % (page - 1)

candidates = [obj(x['path']) for x in bundle['candidates']]
assert [x['logical_key'] for x in candidates] == ['q6', 'q7', 'q8', 'q8-variant']
crops = {x['key']: x for x in bundle['crops']}
assert len(crops) == 14
all_ids = set()
frames = {}
question_results = []
crop_results = []
for candidate in candidates:
    key = candidate['logical_key']
    verify_refs(candidate, key + '-candidate')
    review = obj(candidate['review']['path'])
    verify_refs(review, key + '-review')
    assert review['logical_key'] == key
    assert candidate['book_id'] == bundle['book_id'] == '46007447'
    assert candidate['target_directory_id'] == review['target_directory_id'] == bundle['target_directory_id']
    for zone, text in candidate['zone_values'].items():
        assert sha(text.encode('utf-8')) == candidate['zone_text_sha256'][zone] == review['zone_text_sha256'][zone]
        assert '\ufffd' not in text
    evidence = obj(review['question_info_evidence']['path'])['data']
    assert all(evidence[k] == v for k, v in candidate['question_info'].items())
    assert set(review['frame_keys']) == {f['key'] for f in candidate['frames']}
    assert {c['key'] for c in review['local_crops']} == set(review['frame_keys'])
    for frame in candidate['frames']:
        frame_key = frame['key']
        assert frame_key not in frames
        frames[frame_key] = frame
        assert frame['planned_rect_id'] not in all_ids
        all_ids.add(frame['planned_rect_id'])
        crop = crops[frame_key]
        assert crop == next(c for c in review['local_crops'] if c['key'] == frame_key)
        assert frame['source'] == crop['source']
        assert frame['bbox'] == crop['bbox'] and frame['viewer_page'] == crop['viewer_page']
        page = frame['viewer_page']
        assert frame['source']['sha256'] == sources[page]['sha256']
        assert frame['source_dimensions'] == list(source_images[page].size)
        x1, y1, x2, y2 = frame['bbox']
        assert 0 <= x1 < x2 <= source_images[page].width
        assert 0 <= y1 < y2 <= source_images[page].height
        expected = source_images[page].crop((x1, y1, x2, y2))
        actual = Image.open(mapping[norm(crop['path'])]['copy']).convert('RGB')
        actual.load()
        assert expected.size == actual.size and expected.tobytes() == actual.tobytes(), frame_key
        assert crop['dimensions'] == list(actual.size)
        u = urlsplit(frame['image_path'])
        official = urlsplit(sources[page]['official_image_url'])
        assert (u.scheme, u.netloc, u.path) == (official.scheme, official.netloc, official.path)
        assert not u.fragment
        assert parse_qs(u.query, strict_parsing=True) == {'x-oss-process': [
            'image/crop,x_%d,y_%d,w_%d,h_%d' % (x1, y1, x2 - x1, y2 - y1)]}
        assert frame['image_path'] == crop['official_crop_url']
        crop_results.append({'key': frame_key, 'bbox': frame['bbox'], 'viewer_page': page,
            'source_sha256': frame['source']['sha256'], 'crop_sha256': crop['sha256'],
            'dimensions': list(actual.size), 'pixel_equal_to_source_bbox': True,
            'exact_url_geometry': True})
    parser = Images()
    parser.feed(candidate['zone_values']['question'])
    image_frames = [f for f in candidate['frames'] if f['content_type'] == 'image']
    assert len(parser.images) == len(image_frames) == 1
    assert parser.images[0]['src'] == image_frames[0]['image_path'] == review['figure_linkage']['html_src']
    assert parser.images[0]['alt'] and '\ufffd' not in parser.images[0]['alt']
    question_results.append({'logical_key': key, 'frame_count': len(candidate['frames']),
        'zone_hashes': candidate['zone_text_sha256'], 'html_image_count': 1,
        'html_image_matches_own_figure': True, 'source_review_link': 'PASS'})

assert len(frames) == len(all_ids) == 14
existing = obj(file_named('frames.json')['source'])['data']
assert not all_ids.intersection({f['rect_id'] for f in existing})
directory = obj(file_named('directory.json')['source'])
nodes = []


def find_node(value):
    if isinstance(value, dict):
        if value.get('id') == bundle['target_directory_id']:
            nodes.append(value)
        for child in value.values():
            find_node(child)
    elif isinstance(value, list):
        for child in value:
            find_node(child)


find_node(directory)
assert len(nodes) == 1 and nodes[0]['label'] == bundle['semantic_lesson']
variant_review = obj(candidates[3]['review']['path'])
assert variant_review['content_checks']['antecedent_logical_key'] == 'q8'
assert variant_review['content_checks']['inherited_conditions'] == {'truck_height_m': 4.1, 'truck_width_m': 3}
assert candidates[2]['printed_question'] == candidates[3]['printed_question'] == 8
assert candidates[3]['variant'] is True

proof = obj(file_named('crop-proof.json', True)['source'])
assert len(proof['images']) == 14
assert {x['key'] for x in proof['images']} == set(frames)
remote_results = []
for remote in proof['images']:
    key = remote['key']
    frame = frames[key]
    assert remote['url'] == frame['image_path']
    assert remote['bbox'] == frame['bbox'] and remote['source_sha256'] == frame['source']['sha256']
    assert remote['http_status'] == 200 and remote['attempts'] == 1
    assert remote['content_type'] == 'image/jpeg' and remote['full_pixel_decode'] is True
    response = obj(file_named(key + '.response.json', True)['source'])
    intent = obj(file_named(key + '.intent.json', True)['source'])
    assert response == remote
    assert all(response[k] == v for k, v in intent.items())
    raw = read_source(remote['file'])
    assert len(raw) == remote['bytes'] and sha(raw) == remote['sha256']
    actual = Image.open(mapping[norm(remote['file'])]['copy']).convert('RGB')
    actual.load()
    expected = source_images[frame['viewer_page']].crop(tuple(frame['bbox']))
    assert actual.size == expected.size and list(actual.size) == remote['dimensions']
    assert sha(actual.tobytes()) == remote['rgb_sha256']
    stats = ImageStat.Stat(ImageChops.difference(expected, actual))
    remote_results.append({'key': key, 'sha256': remote['sha256'], 'decoded_rgb_sha256': remote['rgb_sha256'],
        'dimensions': list(actual.size), 'exact_url_and_intent_response_link': True,
        'recorded_attempts': 1, 'recorded_http_status': 200,
        'source_crop_mean_absolute_channel_difference': stats.mean,
        'source_crop_rms_channel_difference': stats.rms,
        'pixel_metric_is_not_standalone_semantic_acceptance': True})

# Exact arithmetic is independent of the author-provided math strings.
F = Fraction
ladder_sq = F(7, 10)**2 + F(24, 10)**2
assert ladder_sq == F(25, 4)
assert ladder_sq - F(15, 10)**2 == 4
assert F(7, 10) + 2 == F(27, 10)
assert 24 + (24 - 4) == 44
assert F(52, 10)**2 - 3**2 == F(1804, 100)
assert F(41, 10)**2 == F(1681, 100) < F(1804, 100)
assert F(43, 10)**2 - F(15, 10)**2 == F(1624, 100) < F(1681, 100)

result = {'schema': 'A28IndependentContentMechanicalChecks/v1', 'status': 'PASS_FINITE_CONTENT_DATA_CHECKS',
    'frozen_members_reverified': 83, 'nested_current_content_references': len(refs),
    'references': refs, 'questions': question_results, 'local_crops': crop_results,
    'remote_crops': remote_results, 'unique_planned_frame_ids': 14, 'current_frame_collisions': 0,
    'target_directory_unique_label_match': True, 'target_directory_current_children': len(nodes[0]['children']),
    'variant_antecedent_declared': 'q8', 'bundle_order_retains_antecedent_adjacency': True,
    'math': {'q6': 'C:2.7m', 'q7': 'D:44', 'q8': '16.81<18.04:can_pass',
             'q8-variant': '16.81>16.24:cannot_pass'},
    'scope': 'Content and fixed remote image evidence only; no author/product code executed.',
    'new_network_requests': 0, 'new_browser_runs': 0, 'product_tests': 0}
data = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
with (PUBLIC / 'mechanical-checks.json').open('xb') as stream:
    stream.write(data)
print(json.dumps({'status': result['status'], 'refs': len(refs), 'local_crops': len(crop_results),
    'remote_crops': len(remote_results), 'maximum_remote_channel_MAE': max(max(r['source_crop_mean_absolute_channel_difference']) for r in remote_results),
    'sha256': sha(data)}))
