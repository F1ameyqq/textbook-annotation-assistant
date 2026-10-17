"""Independent D01 installed-environment probes; no product source insertion."""
import base64
import copy
import csv
import hashlib
import importlib
import importlib.metadata as metadata
import io
import json
import os
from pathlib import Path
import runpy
import sys
import traceback
import unittest
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    Path(path).write_bytes((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def inside(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def imports():
    for name in ("annotation.contracts", "annotation.source.static", "annotation.geometry", "PIL"):
        importlib.import_module(name)
    root = Path(sys.prefix) / "Lib" / "site-packages"
    result = []
    for name, module in sorted(sys.modules.items()):
        if name == "annotation" or name.startswith("annotation.") or name == "PIL" or name.startswith("PIL."):
            filename = getattr(module, "__file__", None)
            if filename:
                assert inside(filename, root), (name, filename, root)
                result.append(dict(module=name, file=str(Path(filename).resolve()), sha256=sha(Path(filename).read_bytes())))
    return result


def environment():
    return dict(executable=sys.executable, version=sys.version, implementation=sys.implementation.name,
                prefix=sys.prefix, base_prefix=sys.base_prefix, cwd=os.getcwd(), sys_path=sys.path,
                isolated=sys.flags.isolated, ignore_environment=sys.flags.ignore_environment,
                no_user_site=sys.flags.no_user_site, imports=imports())


def provenance(wheel, output):
    result = environment()
    assert sys.version_info[:2] == (3, 9)
    assert sys.flags.isolated == 1 and sys.flags.no_user_site == 1
    assert Path(sys.prefix) != Path(sys.base_prefix)
    dist = metadata.distribution("annotation-contracts")
    result["metadata"] = {name: dist.read_text(name) for name in ("METADATA", "RECORD", "direct_url.json", "INSTALLER")}
    result["distribution_location"] = str(dist.locate_file(""))
    result["requires_dist"] = dist.requires
    assert "Pillow==11.3.0" in dist.requires and "pydantic==2.12.5" in dist.requires
    direct = json.loads(result["metadata"]["direct_url.json"])
    wheel_hash = sha(Path(wheel).read_bytes())
    assert direct["archive_info"]["hashes"]["sha256"] == wheel_hash
    assert direct["url"].startswith("file:") and not direct.get("dir_info", {}).get("editable")
    rows = list(csv.reader(io.StringIO(result["metadata"]["RECORD"])))
    records = {row[0]: row for row in rows}
    result["wheel_installed_binding"] = []
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith("annotation/") and name.endswith(".py"):
                raw = archive.read(name)
                installed = Path(dist.locate_file(name))
                assert raw == installed.read_bytes(), name
                record = records[name]
                digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
                assert record[1] == "sha256=" + digest and int(record[2]) == len(raw)
                result["wheel_installed_binding"].append(dict(path=name, installed=str(installed), sha256=sha(raw), bytes=len(raw), record=record))
    result["wheel_sha256"] = wheel_hash
    result["installed_versions"] = {name: metadata.version(name) for name in ("annotation-contracts", "Pillow", "pydantic", "pip", "setuptools", "wheel")}
    write(output, result)


def consume(consumer, exchange, book, output):
    result = dict(before=environment(), consumer=str(Path(consumer).resolve()), consumer_sha256=sha(Path(consumer).read_bytes()),
                  exchange=str(Path(exchange).resolve()), book_id=book, original_argv=[consumer, exchange, "--book-id", book],
                  observer="runpy.run_path; only sys.argv changed, no sys.path insertion")
    try:
        sys.argv = result["original_argv"]
        runpy.run_path(consumer, run_name="__main__")
        from annotation.source.static import load_static_bundle
        from PIL import Image
        bundle = load_static_bundle(exchange, expected_book_id=book)
        source = bundle.artifacts[0]
        images = []
        for asset in source.payload.assets:
            path = Path(exchange).parent / asset.path
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image.load()
                assert image.size == (asset.width, asset.height)
                images.append(dict(asset_id=asset.asset_id, file=str(path), sha256=sha(path.read_bytes()), size=image.size,
                                   format=image.format, full_load="OK"))
        limitations = json.loads((Path(exchange).parent / "limitations.json").read_text(encoding="utf-8"))
        expected = {"46006966": (6, 250, 14), "46007447": (2, 214, 1)}[book]
        assert (len(images), source.payload.metadata_page_count, len(source.payload.scope_manifest)) == expected
        assert limitations["coverage_eligible"] is False and limitations["scope_manifest_status"] == "REFERENCE_ONLY"
        assert limitations["independent_denominator_status"] == "UNKNOWN"
        result.update(result="ACCEPTED_INPUT_ONLY", images=images, limitations=limitations)
    except BaseException as error:
        result.update(result="REJECTED", error_type=type(error).__name__, error=str(error),
                      code=getattr(error, "code", None), location=getattr(error, "location", getattr(error, "path", None)),
                      traceback=traceback.format_exc())
        raise
    finally:
        result["after"] = environment()
        write(output, result)


def replace(value, old, new):
    if isinstance(value, dict):
        return {key: replace(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [replace(item, old, new) for item in value]
    return new if value == old else value


def decode_case(exchange, book, output, delta_dir):
    from annotation.contracts import load_bundle, seal_artifact
    from annotation.source.static import load_static_bundle
    from PIL import Image
    path = Path(exchange)
    original = json.loads(path.read_text(encoding="utf-8"))
    value = copy.deepcopy(original)
    asset = value["artifacts"][0]["payload"]["assets"][0]
    image_path = path.parent / asset["path"]
    original_image = image_path.read_bytes()
    truncated = original_image[:len(original_image)//2]
    assert len(truncated) < len(original_image)
    old_sha = asset["sha256"]
    new_sha = sha(truncated)
    old_id = asset["asset_id"]
    new_id = "asset-" + book + "-" + new_sha
    image_path.write_bytes(truncated)
    value = replace(replace(value, old_sha, new_sha), old_id, new_id)
    provenance_path = path.parent / "provenance.json"
    provenance_value = json.loads(provenance_path.read_text(encoding="utf-8"))
    write(provenance_path, replace(replace(provenance_value, old_sha, new_sha), old_id, new_id))
    provenance_sha = sha(provenance_path.read_bytes())

    def rebind(node):
        if isinstance(node, dict):
            if node.get("path") == "provenance.json" and "sha256" in node:
                node["sha256"] = provenance_sha
            for item in node.values():
                rebind(item)
        elif isinstance(node, list):
            for item in node:
                rebind(item)
    rebind(value)
    value["artifacts"] = [seal_artifact(item) for item in value["artifacts"]]
    write(path, value)
    delta = Path(delta_dir)
    delta.mkdir(parents=True, exist_ok=False)
    for changed in (image_path, provenance_path, path):
        target = delta / changed.relative_to(path.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(changed.read_bytes())
    result = dict(environment=environment(), book_id=book, exchange=str(path),
                  old_image_sha256=old_sha, new_image_sha256=new_sha, original_bytes=len(original_image), truncated_bytes=len(truncated),
                  changed_paths=[image_path.relative_to(path.parent).as_posix(), "provenance.json", "exchange.json"],
                  public_resource_layer="NOT_RUN", pillow_verify="NOT_RUN", pillow_full_load="NOT_RUN", source_layer="NOT_RUN")
    try:
        load_bundle(path, verify_assets=True)
        result["public_resource_layer"] = "PASS"
        with Image.open(image_path) as image:
            image.verify()
        result["pillow_verify"] = "PASS_HEADER_ONLY"
        try:
            with Image.open(image_path) as image:
                image.load()
        except OSError as error:
            result["pillow_full_load"] = "REJECTED"
            result["pillow_load_error"] = str(error)
        else:
            raise AssertionError("Truncated JPEG unexpectedly fully decoded")
        try:
            load_static_bundle(path, expected_book_id=book)
        except Exception as error:
            result.update(source_layer="REJECTED", code=getattr(error, "code", None),
                          location=getattr(error, "location", None), error=str(error), traceback=traceback.format_exc())
            assert result["code"] == "IMAGE_DECODE", result
            raise
        else:
            raise AssertionError("Installed A01 accepted truncated image")
    finally:
        result["actual_imports_after"] = imports()
        write(output, result)


def regression(root, output):
    result = dict(before=environment(), fixture_root=root, source_directory_exists=(Path(root)/"src").exists())
    assert result["source_directory_exists"] is False
    tests = Path(root) / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests), pattern="test_contracts*.py")
    actual = unittest.TextTestRunner(verbosity=2).run(suite)
    result.update(tests_run=actual.testsRun, failures=len(actual.failures), errors=len(actual.errors),
                  skipped=actual.skipped, successful=actual.wasSuccessful(), after=environment(),
                  child_path_boundary="Original subprocesses may set PYTHONPATH to this src-free fixture root; not separate -I installation proofs.")
    write(output, result)
    if not actual.wasSuccessful():
        raise SystemExit(1)


def source_regression(old, new, output):
    from annotation.contracts import load_bundle
    from annotation.source.static import load_static_bundle, StaticSourceError
    result = dict(environment=environment(), cases=[])
    for book, path in (("46006966", old), ("46007447", new)):
        public = load_bundle(path, verify_assets=True)
        accepted = load_static_bundle(path, expected_book_id=book)
        assert accepted == public
        result["cases"].append(dict(book_id=book, kind="VALID_PUBLIC_AND_SOURCE", result="PASS"))
        wrong = "46007447" if book == "46006966" else "46006966"
        try:
            load_static_bundle(path, expected_book_id=wrong)
        except StaticSourceError as error:
            assert error.code == "BOOK_CONFLICT"
            result["cases"].append(dict(book_id=book, kind="CROSS_BOOK", code=error.code, location=error.location, result="EXPECTED_REJECTION"))
        else:
            raise AssertionError("cross-book input accepted")
    result["actual_imports_after"] = imports()
    write(output, result)


if __name__ == "__main__":
    command, *args = sys.argv[1:]
    {"provenance": provenance, "consume": consume, "decode": decode_case,
     "regression": regression, "source-regression": source_regression}[command](*args)
