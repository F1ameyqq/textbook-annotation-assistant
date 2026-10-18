"""Export the released fixed raw Git inputs and derive three synthetic fixtures."""
import copy
from pathlib import Path
import shutil
from support import BASE, PRODUCT, WORKFLOW, ROOT, EVIDENCE, canonical, export, load, sha, write


def fixtures(view):
    seed = view / 'examples/a03/T3-closure/inputs/single'
    for tag in ('N', 'E', 'U'):
        dest = ROOT / 'tests/fixtures/i01' / tag
        original = load(seed / 'initial.json')
        # Only identities change. Policy, pixel language and semantic boxes are inherited.
        data = __import__('json').loads(__import__('json').dumps(original).replace('M-single', 'I01-' + tag))
        inventory = __import__('json').loads((seed/'assets/inventory.json').read_text(encoding='utf-8').replace('M-single', 'I01-' + tag))
        write(dest/'assets/inventory.json', inventory)
        for filename in ('page-1.pgm', 'proof.txt'):
            write(dest/'assets'/filename, (seed/'assets'/filename).read_bytes())
        source, evidence, graph, snapshot = data['artifacts']
        source['payload']['scope_integrity']['proof']['sha256'] = sha((dest/'assets/inventory.json').read_bytes())
        sealed = {}
        def update(value):
            if isinstance(value, dict):
                if {'artifact_id','revision','kind','content_hash'} == set(value) and value['artifact_id'] in sealed:
                    return copy.deepcopy(sealed[value['artifact_id']])
                return {k:update(v) for k,v in value.items()}
            if isinstance(value, list): return [update(v) for v in value]
            return value
        output = []
        for artifact in (source, evidence, graph, snapshot):
            artifact = update(artifact)
            artifact['content_hash'] = sha(canonical({k:v for k,v in artifact.items() if k != 'content_hash'}))
            sealed[artifact['artifact_id']] = {k:artifact[k] for k in ('artifact_id','revision','kind','content_hash')}
            output.append(artifact)
        data['artifacts'] = output
        write(dest/'initial.json', data)
    source = view/'examples/a01/R3/bundles/46007447'
    dest = ROOT/'tests/fixtures/i01/source-copy'
    assert not dest.exists()
    shutil.copytree(source, dest)


def main():
    prep = EVIDENCE/'preparation'
    prep.mkdir(parents=True, exist_ok=False)
    view = prep/'raw-view'
    prefixes = ['src/annotation', 'examples/a01/consume.py', 'examples/a01/R3/bundles/46007447',
        'examples/a03/T3-closure/inputs/single', 'examples/a03/T1-capture/capture.py',
        'pyproject.toml', 'requirements.txt']
    rows = export(BASE, prefixes, view)
    # Preserve task text from the workflow commit, not the older integration tree.
    rules = export(WORKFLOW, ['docs/tasks/I01-A-minimal-integration.md',
        'docs/tasks/I01-A-independent-review.md'], prep/'rules')
    native = view/'src/annotation/contracts/a03_native'
    profile = load(native/'data/profile.json')
    pins = []
    for name, expected in profile['implementation_pins']:
        path = view/('src/'+name[1:]) if name.startswith('@') else native/name
        actual = sha(path.read_bytes())
        assert actual == expected, name
        pins.append(dict(path=str(path.relative_to(view)), sha256=actual))
    assert len(pins) == 30
    for name, expected in profile['schema_pins']:
        assert sha((native/'data'/name).read_bytes()) == expected
    for key, name in [('api_sha256','api.json'),('interface_sha256','interface-source.json'),('oracle_sha256','oracle.json')]:
        assert sha((native/'data'/name).read_bytes()) == profile[key]
    assert load(native/'data/adoption.json')['profile_sha256'] == sha((native/'data/profile.json').read_bytes())
    fixtures(view)
    members = [dict(path=str(p.relative_to(ROOT)).replace('\\','/'), bytes=p.stat().st_size,
        sha256=sha(p.read_bytes())) for p in sorted((ROOT/'tests/fixtures/i01').rglob('*')) if p.is_file()]
    write(prep/'identity.json', dict(base=BASE, product=PRODUCT, workflow=WORKFLOW, files=rows,
        rules=rules, implementation_pins=pins, inputs=members, fresh_targets=0, dispatches=0,
        derivation='accepted single-question synthetic language; per-path identities and inventory resealed; original policy and PGM bytes'))
    print('RAW_BYTES_AND_30_PINS_OK; fixture derivation complete; targets=0 dispatch=0')


if __name__ == '__main__': main()
