"""Dependency changes after genuine qualification; no DB/target/effects."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from annotation.contracts import ContractError
from annotation.contracts.a03_native import validate_native_bundle, derive_context
from annotation.runtime.storage.native import NativeRegistry, NativeRuntimeStore
from annotation.runtime.storage.common import RuntimeFailure


class ValidationReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='a03-r1-controls-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'assets'
        shutil.copytree(Path(__file__).resolve().parents[1] / 'examples/a03/T3-closure/inputs/single', self.root)
        self.data = json.loads((self.root / 'initial.json').read_bytes())
        self.store = NativeRuntimeStore.__new__(NativeRuntimeStore)
        self.store.native_registry = NativeRegistry(self.store)

    def test_unchanged_bytes_reuse_but_input_mutation_rejects(self):
        good = self.store._validate(self.data, asset_root=self.root)
        counts = self.store.native_registry.validation_counts
        complete = counts['complete']
        validate_native_bundle(good, bridge_context=good.bridge_context)
        self.assertEqual(complete, counts['complete'])
        self.assertGreater(counts['resource_reads'], 0)
        bad = copy.deepcopy(self.data)
        bad['artifacts'][-1]['input_refs'] = []
        with self.assertRaises(ContractError):
            self.store._validate(bad, asset_root=self.root)
        self.assertGreater(counts['complete'], complete)

    def test_resource_replacement_same_size_and_mtime_rejected_on_reuse(self):
        good = self.store._validate(self.data, asset_root=self.root)
        file = self.root / 'assets/proof.txt'
        stamp = file.stat()
        raw = file.read_bytes()
        file.write_bytes(b'X' * len(raw))
        os.utime(file, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaises(ContractError):
            validate_native_bundle(good, bridge_context=good.bridge_context)

    def test_root_registry_and_declarations_are_distinct_dependencies(self):
        good = self.store._validate(self.data, asset_root=self.root)
        other = Path(self.temp.name) / 'other'
        shutil.copytree(self.root, other)
        b = self.store._validate(self.data, asset_root=other)
        self.assertNotEqual(good.bridge_context.asset_root, b.bridge_context.asset_root)
        self.assertEqual(2, self.store.native_registry.validation_counts['complete'])
        fresh = NativeRuntimeStore.__new__(NativeRuntimeStore)
        fresh.native_registry = NativeRegistry(fresh)
        fresh._validate(self.data, asset_root=self.root)
        self.assertEqual(1, fresh.native_registry.validation_counts['complete'])
        with self.assertRaises(RuntimeFailure) as raised:
            derive_context(good.bridge_context, self.data, asset_root=Path(self.temp.name))
        self.assertEqual('NATIVE_CONTEXT_ROOT_FOREIGN', raised.exception.code)


if __name__ == '__main__':
    unittest.main()
