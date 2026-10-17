"""R1 minimal coverage shape/completeness checks using actual PGM bytes."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from annotation.contracts.a03_native import NativeSchemas, _documents
from annotation.contracts.a03_bridge._schema import validate as validate_schema
from annotation.contracts.recovery import _node
from annotation.quality.synthetic_precheck import compare_synthetic_inputs, _pre_coverage_decision
from annotation.quality.targetcheck import coverage_for
from annotation.runtime.storage.common import digest, reference

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/a03/P2-R8-R1-producer'


class R8R1MinimalTests(unittest.TestCase):
    def test_coverage_shape_and_complete_decisions(self):
        original = json.loads((FIXTURE / 'initial.json').read_bytes())
        records = []
        for incomplete in (False, True):
            data = copy.deepcopy(original)
            if incomplete:
                evidence = data['artifacts'][1]
                evidence['payload']['coverage_clues'][0]['disposition'] = 'UNASSIGNED'
                evidence['payload']['coverage_clues'][0]['reason'] = 'Explicit incomplete synthetic coverage control'
                evidence['content_hash'] = digest({k: v for k, v in evidence.items() if k != 'content_hash'})
                graph = data['artifacts'][2]
                graph['payload']['evidence'] = reference(evidence)
                graph['input_refs'] = [reference(evidence) if r['kind'] == 'EvidenceBundle' else r for r in graph['input_refs']]
                graph['content_hash'] = digest({k: v for k, v in graph.items() if k != 'content_hash'})
            NativeSchemas().check(data)
            bundle = _node(data)
            source, evidence, graph, snapshot = bundle.artifacts
            policy = bundle.policies[0]
            policy_ref = {k: policy[k] for k in ('policy_id', 'revision', 'content_hash')}
            actual_checks = compare_synthetic_inputs(bundle, reference(source), reference(evidence), reference(graph), policy_ref, asset_root=FIXTURE)
            pair = coverage_for(bundle, graph)
            self.assertIs(type(pair), tuple)
            self.assertEqual(pair[1], not incomplete)
            coverage, checks, decision = _pre_coverage_decision(bundle, graph, actual_checks)
            self.assertIs(type(coverage), dict)
            document = _documents()['exchange']
            validate_schema(coverage, document['$defs']['Coverage'], document)
            self.assertEqual(decision, 'HOLD' if incomplete else 'PASS')
            self.assertEqual(checks['coverage'], 'FAIL' if incomplete else 'PASS')
            self.assertEqual(checks, actual_checks)
            records.append({'incomplete': incomplete, 'coverage_type': type(coverage).__name__,
                'complete': pair[1], 'actual_checks': actual_checks, 'decision': decision,
                'actual_pgm_sha256': hashlib.sha256((FIXTURE / 'assets/page.pgm').read_bytes()).hexdigest(),
                'runtime_admission_claim': False})
        print(json.dumps({'minimal_cases': records}, sort_keys=True))


if __name__ == '__main__':
    unittest.main(failfast=True)
