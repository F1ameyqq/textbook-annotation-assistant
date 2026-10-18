"""Read the already published six-source Q15 fixture; never run recognition."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'handoffs/b/46007447/B-46007447-Q15-revision9-current-baseline-HOLD-2026-10-18.zip'
SHA256 = '8c812330b93cc60b920f6ccd1cd7784f0afe8d293336166a586e1aeaab8231ad'
TARGET = 'a-17f4ef3ee25046f8e3f583a2'


def inputs(directory):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == SHA256
    with zipfile.ZipFile(ARCHIVE) as z:
        entries = {v['path']: v for v in json.loads(z.read('manifest.json'))['files']}

        def raw(name):
            data = z.read(name)
            assert hashlib.sha256(data).hexdigest() == entries[name]['sha256']
            return data

        def read(name):
            return json.loads(raw(name))

        report = read('reference/final/merged-cold-report.json')
        stages = {s['stage_id']: s for s in report['payload']['stages']}

        def result(stage):
            return read('reference/'+stages[stage]['output']['path'])['payload']['result']['payload']

        evidence = result('inline_prepare')['base_evidence_archive']
        graph = read('reference/final/graph.json')
        state = graph['payload']['content_revision']
        review = result('recovery_review')['review']
        files = {hashlib.sha256(raw(n)).hexdigest(): n for n in entries
                 if n.startswith('base/source/') and n.endswith('.jpg')}
        manifests = []
        # Two roots deliberately exercise source lookup beyond the first manifest.
        for index, pages in enumerate((evidence['payload']['pages'][:1], evidence['payload']['pages'][1:])):
            folder = root/str(index)
            folder.mkdir(exist_ok=True)
            assets = []
            for i, page in enumerate(pages):
                source = page['source']
                name = str(i)+'.jpg'
                (folder/name).write_bytes(raw(files[source['sha256']]))
                assets.append({k: source[k] for k in ('asset_id', 'sha256', 'width', 'height')}
                              | dict(path=name, reading_order=i))
            manifest = dict(schema_version='b-source-trial/0.1', artifact_id='q15-review-source-'+str(index),
                            book_id='46007447', scope_id='q15-review-source', assets=assets)
            path = folder/'source.json'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            manifests.append(path)
        return [evidence, state['base_graph_archive'], state['base_check_archive'], review,
                read('plans/revision9.json')], manifests, graph
