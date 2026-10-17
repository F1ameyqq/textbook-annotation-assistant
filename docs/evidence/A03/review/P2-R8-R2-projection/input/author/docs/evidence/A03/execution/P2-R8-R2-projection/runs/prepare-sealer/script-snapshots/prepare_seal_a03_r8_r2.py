"""Prepare the R2 file-only sealing helper from frozen R1 utility text."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]


def main():
    source = ROOT / 'examples/a03/P2-R8-R1-producer/seal_a03_r8_r1.py'
    text = source.read_text(encoding='utf-8')
    changes = [
        ('P2-R8-R1-producer', 'P2-R8-R2-projection'),
        ('fa6edeb7e9dd0c9502781747e5fce012931d9441', 'a0c40886f3076f84c46377e03fc2206d2fdc5585'),
        ('src/annotation/quality/synthetic_precheck.py', 'src/annotation/runtime/storage/__init__.py'),
        ('@annotation/quality/synthetic_precheck.py', '@annotation/runtime/storage/__init__.py'),
        ('producer pin change', 'projection pin change'),
        ('only_producer_and_affected_pins_changed', 'only_projection_and_affected_pins_changed'),
        ('product_reruns_after_N1_failure', 'product_reruns_after_N2_failure'),
        ('REVIEW_N1_BLOCKED', 'REVIEW_N2_BLOCKED'),
        ("('minimal', 'N1', 'C01', 'A02', 'R7')", "('minimal', 'N1', 'N2', 'C01', 'A02', 'R7')"),
        ('minimal_N1_C01_A02_R7_sources_identical', 'minimal_N1_N2_C01_A02_R7_sources_identical')]
    for old, new in changes:
        if old not in text:
            raise RuntimeError('missing frozen helper anchor: ' + old)
        text = text.replace(old, new)
    target = Path(__file__).with_name('seal_a03_r8_r2.py')
    with target.open('xb') as stream:
        stream.write(text.encode('utf-8'))
    print(json.dumps({'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'new_helper_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'product_executed': False}))


if __name__ == '__main__':
    main()
