"""One independent full binding control under the protected fake runner."""
import copy
import json
import sys
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tests/a24_current_context'))
import fixtures as f
from fixtures import p, gate

RECORDS = []


class CompleteBinding(TestCase):
    def test_all_103_typed_fields_three_documents_and_real_templates(self):
        scope = gate.scope_binding('a' * 64)
        self.assertEqual(len(scope), 103)
        originals = f.authority()
        self.assertEqual(f.validate(*originals).candidate_sha256, 'a' * 64)
        rejected = 0
        for index in range(3):
            for field, expected in scope.items():
                docs = [copy.deepcopy(doc) for doc in originals]
                del docs[index][field]
                with self.assertRaises(gate.Stop):
                    f.validate(*docs)
                rejected += 1
                docs = [copy.deepcopy(doc) for doc in originals]
                if type(expected) is bool:
                    changed = int(expected)
                elif type(expected) is int:
                    changed = bool(expected) if expected in (0, 1) else str(expected)
                elif type(expected) is list:
                    changed = list(expected) + ['FORBIDDEN_EXTRA']
                else:
                    changed = expected + '__WRONG'
                docs[index][field] = changed
                with self.assertRaises(gate.Stop):
                    f.validate(*docs)
                rejected += 1
        candidate = 'c68ce354be516552e1aadafe253cd3f9c12785b3107d2454e59f10446ef31b77'
        real_scope = gate.scope_binding(candidate)
        for name in ('activation', 'decision', 'independent-report'):
            document = json.loads((ROOT / ('docs/evidence/A24/revisions/current-context-r1/' +
                name + '-template-NONEXECUTABLE.json')).read_bytes())
            for key, value in real_scope.items():
                self.assertTrue(gate.same_typed(document.get(key), value), (name, key))
        self.assertEqual(real_scope['source_contract_supplement_sha256'],
            '34a2f98a22d8e62e192ef0dfdb58601a3b76edfea7f213256bf62eb10f00c4b1')
        self.assertEqual(real_scope['source_contract_supplement_workflow'],
            'cd591394db393b8f27d9f45d1e1890725d95d800')
        self.assertEqual(real_scope['prior_readonly_allocation_remaining'], 0)
        self.assertEqual(real_scope['logical_json_slot_names'], ['book', 'directory', 'frames', 'source', 'page14', 'page173'])
        self.assertEqual(real_scope['business_write_limit'], 0)
        self.assertEqual(real_scope['sample_limit'], 0)
        RECORDS.append({'group': 'complete_103_typed_bindings', 'scope_count': 103,
            'rejected_mutations': rejected, 'templates_compared': 3, 'real_scope': real_scope})
