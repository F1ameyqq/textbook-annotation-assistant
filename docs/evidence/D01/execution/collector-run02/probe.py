"""D01 installed-package probes. Run with the new environment's python -I.

Only the regression mode adds the frozen *test* directory, which contains no
src/ tree. The public A01 consumer is executed unchanged using runpy.
"""
import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
from pathlib import Path
import runpy
import sys
import unittest


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance():
    imports = {}
    prefix = Path(sys.prefix).resolve()
    for name in ("annotation.contracts", "annotation.source.static", "annotation.geometry", "PIL"):
        importlib.import_module(name)
    for name, module in sorted(sys.modules.items()):
        if name == "PIL" or name.startswith(("PIL.", "annotation.")):
            filename = getattr(module, "__file__", None)
            if filename:
                path = Path(filename).resolve()
                if prefix not in path.parents:
                    raise AssertionError("import outside new environment: " + str(path))
                imports[name] = {"file": str(path), "sha256": digest(path)}
    return {"executable": sys.executable, "version": sys.version,
            "prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "isolated": sys.flags.isolated, "no_user_site": sys.flags.no_user_site,
            "ignore_environment": sys.flags.ignore_environment,
            "sys_path": list(sys.path), "imports": imports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("metadata", "consumer", "regression", "source"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--consumer", type=Path)
    parser.add_argument("--exchange", type=Path)
    parser.add_argument("--book-id")
    parser.add_argument("--tests", type=Path)
    args = parser.parse_args()
    result = {"mode": args.mode, "cwd": str(Path.cwd()), "argv": list(sys.argv)}
    try:
        result["before"] = provenance()
        assert sys.flags.isolated == 1 and sys.version_info[:2] == (3, 9)
        if args.mode == "metadata":
            dist = metadata.distribution("annotation-contracts")
            result["distribution"] = {
                "name": dist.metadata["Name"], "version": dist.version,
                "requires_python": dist.metadata["Requires-Python"],
                "requires_dist": dist.requires,
                "dist_info": str(dist._path),
                "direct_url": json.loads(dist.read_text("direct_url.json")),
                "distributions": sorted(
                    [{"name": d.metadata["Name"], "version": d.version,
                      "location": str(d.locate_file(""))} for d in metadata.distributions()],
                    key=lambda d: d["name"].lower())}
            assert "Pillow==11.3.0" in dist.requires
            assert result["distribution"]["requires_python"] == ">=3.9"
            assert result["distribution"]["direct_url"]["archive_info"]["hashes"]["sha256"] == digest(args.wheel)
            assert not result["distribution"]["direct_url"].get("dir_info", {}).get("editable", False)
            # Match every product .py byte to the actually installed wheel.
            import zipfile
            with zipfile.ZipFile(args.wheel) as archive:
                result["wheel_files"] = []
                for name in archive.namelist():
                    if name.startswith("annotation/") and name.endswith(".py"):
                        installed = Path(dist.locate_file(name))
                        expected = hashlib.sha256(archive.read(name)).hexdigest()
                        assert digest(installed) == expected
                        result["wheel_files"].append({"path": name, "sha256": expected,
                                                       "installed": str(installed)})
            result["metadata_text"] = dist.read_text("METADATA")
            result["record_text"] = dist.read_text("RECORD")
        elif args.mode == "consumer":
            sys.argv = [str(args.consumer), str(args.exchange), "--book-id", args.book_id]
            runpy.run_path(str(args.consumer), run_name="__main__")
        elif args.mode == "regression":
            assert not (args.tests.parent / "src").exists()
            sys.path.insert(0, str(args.tests))
            suites = [unittest.defaultTestLoader.discover(str(args.tests), pattern=pattern)
                      for pattern in ("test_contracts.py", "test_contracts_platform_refs.py")]
            checks = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
            result["tests"] = {"ran": checks.testsRun, "failures": len(checks.failures),
                               "errors": len(checks.errors), "skips": checks.skipped}
            assert checks.wasSuccessful() and checks.testsRun == 70 and not checks.skipped
        elif args.mode == "source":
            from annotation.source.static.importer import StaticSourceError, url_index, decode_image
            result["url_cases"] = []
            for book, index in (("46006966", 7), ("46007447", 13)):
                url = "https://archive.example.invalid/upload_images/{0}/{0}_page_{1}.jpg".format(book, index)
                assert url_index(url, book, "d01.image") == index
                result["url_cases"].append({"book": book, "url": url, "index": index})
            for tail in ("?", "#", "?token=opaque", "#view", "?echo=/upload_images/46006966/46006966_page_1.jpg"):
                url = "https://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg" + tail
                try:
                    url_index(url, "46007447", "d01.image")
                    raise AssertionError("unsupported URL accepted")
                except StaticSourceError as error:
                    assert error.code == "SOURCE_URL_COMPONENT" and error.location == "d01.image"
                    result["url_cases"].append({"url": url, "code": error.code, "location": error.location})
            broken = args.output.parent / "invalid-image.jpg"
            broken.write_bytes(b"D01 controlled non-JPEG bytes\n")
            try:
                decode_image(broken)
                raise AssertionError("invalid image decoded")
            except StaticSourceError as error:
                assert error.code == "IMAGE_DECODE" and error.location == broken.name
                result["decode_rejection"] = {"path": str(broken), "sha256": digest(broken),
                                              "code": error.code, "location": error.location}
        result["completed"] = True
    finally:
        result["after"] = provenance()
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
