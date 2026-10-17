"""Static candidate checks and exact implementation-pin update; no product import."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle'
BASE = 'c83f956c5c29c64ab10735ba11c153201d3f3f4b'
IMPLEMENTATIONS = ('src/annotation/runtime/recovery/__init__.py', 'src/annotation/runtime/recovery/native_quality.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=ROOT)


if __name__ == '__main__':
    profile = ROOT / 'src/annotation/contracts/a03_native/data/profile.json'
    adoption = profile.with_name('adoption.json')
    original = json.loads(git('show', BASE + ':' + profile.relative_to(ROOT).as_posix()))
    assert json.loads(profile.read_bytes()) == original
    expected = json.loads(json.dumps(original))
    for row in expected['implementation_pins']:
        path = 'src/' + row[0].lstrip('@')
        if path in IMPLEMENTATIONS:
            row[1] = sha((ROOT / path).read_bytes())
    profile.write_bytes((json.dumps(expected, ensure_ascii=False, indent=2) + '\n').encode())
    old_adoption = json.loads(git('show', BASE + ':' + adoption.relative_to(ROOT).as_posix()))
    assert json.loads(adoption.read_bytes()) == old_adoption
    old_adoption['profile_sha256'] = sha(profile.read_bytes())
    adoption.write_bytes((json.dumps(old_adoption, ensure_ascii=False, indent=2) + '\n').encode())
    paths = [ROOT / 'tests/test_a03_p2_r9_r1_owner_lifecycle.py'] + list(Path(__file__).parent.glob('*.py'))
    paths += [ROOT / name for name in IMPLEMENTATIONS]
    for path in paths:
        ast.parse(path.read_bytes(), filename=str(path))
    old_tree = ast.parse(git('show', BASE + ':' + IMPLEMENTATIONS[0]))
    new_tree = ast.parse((ROOT / IMPLEMENTATIONS[0]).read_bytes())
    def legacy(tree):
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'publish_quality')
        return [ast.dump(n, include_attributes=False) for n in function.body[2:]]
    assert legacy(old_tree) == legacy(new_tree), 'legacy report path changed'
    allowed = set(IMPLEMENTATIONS) | {profile.relative_to(ROOT).as_posix(), adoption.relative_to(ROOT).as_posix()}
    assert set(git('diff', '--name-only').decode().splitlines()) == allowed
    for logical, expected_sha in expected['implementation_pins']:
        path = ROOT / ('src/' + logical.lstrip('@')) if logical.startswith('@annotation/') else profile.parent.parent / logical
        assert sha(path.read_bytes()) == expected_sha, logical
    drivers = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
        for p in paths if p.relative_to(ROOT).as_posix() not in IMPLEMENTATIONS]
    product = [{'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': sha((ROOT / p).read_bytes())} for p in sorted(allowed)]
    record = {'base': BASE, 'drivers': drivers, 'product': product, 'syntax_checked': True,
        'legacy_report_path_AST_unchanged': True, 'only_two_implementation_pins_and_adoption_chain_updated': True,
        'static_ownership_review': 'Borrowed pair validated before projection; no claim/release; standalone claims/releases; all three report transactions recheck existing _lease pending_ok=True; run_plan finally unchanged.',
        'product_calls': 0}
    with (OUT / 'candidate-frozen.json').open('xb') as stream:
        stream.write((json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps(record))
