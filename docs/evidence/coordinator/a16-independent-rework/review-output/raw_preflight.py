"""Read raw local Git and fixed isolated input. Writes reviewer evidence only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('D:/1800')
FIXED = Path('D:/1800-worktrees/a16-independent-fixed')
OUT = FIXED / 'docs/evidence/A16/independent-offline-review'
PREP = Path('D:/1800-worktrees/a16-review-preparation')
BASE = '7432122b9fd5602785ebfb2b3f24e407fdf76eda'
PRODUCT = '2a604c2d0b0f7781ec0d7ca4b5925ae9ff53b595'
FINAL = '4fe417d5246f20fbbbedc577495c7ca400d4ded8'
WORKFLOW = '7409a94d9e94eb1b5a7414a7cbb701b320a9f329'
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1')


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true'] + list(args), cwd=str(ROOT), env=ENV)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def tree(commit):
    entries = {}
    for entry in git('ls-tree', '-rz', commit).split(b'\0'):
        if entry:
            header, raw_path = entry.split(b'\t', 1)
            entries[raw_path.decode('utf-8')] = header.decode('ascii').split()
    return entries


base, final = tree(BASE), tree(FINAL)
changed_old = [p for p, value in base.items() if final.get(p) != value]
assert len(base) == 31259 and not changed_old
added = sorted(set(final) - set(base))
assert len(added) == 47
native_paths = ['docs/evidence/A15/certificate-exception/reviewed-native/native_windows.py',
                'docs/evidence/A15/certificate-exception/reviewed-native/process_check.py']
inputs = []
for path in added + native_paths:
    mode, kind, blob = final[path]
    expected = git('cat-file', 'blob', blob)
    actual = (FIXED / path).read_bytes()
    assert actual == expected, path
    inputs.append({'path': path, 'mode': mode, 'type': kind, 'blob': blob,
        'bytes': len(actual), 'sha256': sha(actual)})
evidence = FIXED / 'docs/evidence/A16/current-readonly'
assert sha((evidence / 'candidate-manifest.json').read_bytes()) == '2579b043d65e665263796d0922f080ad101f4d20c1e9ea500fd7894ba41d966c'
assert sha((evidence / 'delivery-manifest.json').read_bytes()) == '41d965083d188f7021cb1e64b9d9a98c2b97541aa31f5d39e267b1ff228f7ca1'
for manifest_name in ('candidate-manifest.json', 'delivery-manifest.json'):
    manifest = json.loads((evidence / manifest_name).read_bytes())
    for item in manifest['members']:
        raw = (FIXED / item['path']).read_bytes()
        assert len(raw) == item['size'] and sha(raw) == item['sha256'], item['path']
        assert final[item['path']][2] == item['blob']
assert (evidence / 'dependencies/a15_native_reference.py').read_bytes() == git('show', BASE + ':tools/headless_cert_exception_reuse_probe.py')
for path in native_paths:
    assert git('show', BASE + ':' + path) == (FIXED / path).read_bytes()

prep_manifest = (PREP / 'raw-manifest.json').read_bytes()
assert sha(prep_manifest) == 'f5c270c9ddaf53b18425e7e93be84a5b33b0df5474ae684cc2e2f752f3dca2d0'
prep_members = json.loads(prep_manifest)['members']
assert len(prep_members) == 37
for item in prep_members:
    raw = (PREP / item['path']).read_bytes()
    assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], item['path']

dispatch = git('show', WORKFLOW + ':docs/tasks/A16-fixed-offline-review-dispatch.md')
assert sha(dispatch) == 'f718d2e5aa697644598f1f7bd80a5a8d31180b22586d0eb562976bec19a15500'
with (OUT / 'dispatch.raw.md').open('xb') as stream:
    stream.write(dispatch)
save('input-raw-manifest.json', {'task': 'A16', 'base': BASE, 'product': PRODUCT, 'final': FINAL,
    'workflow': WORKFLOW, 'member_count': len(inputs), 'members': inputs})
save('raw-preflight-result.json', {'task': 'A16', 'result': 'PASS_RAW_ONLY',
    'input_raw_verified': len(inputs), 'old_members_verified': len(base), 'old_differences': changed_old,
    'new_paths': len(added), 'native_reference_matches_fixed_A15': True,
    'preparation_members_preserved': len(prep_members), 'dispatch_hash_verified': True,
    'author_floating_tree_read': False, 'git_lazy_fetch': False, 'product_executed': False,
    'semantic_acceptance': 'NOT_ASSESSED_BY_THIS_CHECK'})
print(json.dumps({'raw': 'PASS', 'inputs': len(inputs), 'old_members': len(base),
    'preparation_members': len(prep_members), 'product_executed': False}))
