"""The sole permitted protocol child: import frozen product and emit synthetic zero only."""
import hashlib
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
product = Path(__file__).resolve().parent.parent / 'tools/headless_native_reuse_probe_r1.py'
if hashlib.sha256(product.read_bytes()).hexdigest() != '3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9':
    raise SystemExit(70)
spec = importlib.util.spec_from_file_location('independent_protocol_product', product)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.emit_occupancy_count(0)
