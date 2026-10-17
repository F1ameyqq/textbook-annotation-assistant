"""Minimal offline command line interface."""
import argparse
import json
import sys

from . import ContractError, load_bundle, schema


def main(argv=None):
    parser = argparse.ArgumentParser(description="C01 offline contract proposal validator")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate a closed exchange and resource bytes")
    validate.add_argument("bundle")
    validate.add_argument("--structure-only", action="store_true", help="skip resource file bytes, not reference semantics")
    commands.add_parser("schema", help="emit generated JSON Schema (semantic validation is additional)")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            print(json.dumps(schema(), ensure_ascii=False, indent=2))
        else:
            bundle = load_bundle(args.bundle, verify_assets=not args.structure_only)
            print(json.dumps({"valid": True, "schema_version": "1.0.0-a-proposal",
                              "artifacts": len(bundle.artifacts), "resources_verified": not args.structure_only,
                              "validation_layer": "OFFLINE_CONTRACT"}, ensure_ascii=False))
        return 0
    except ContractError as error:
        print(json.dumps({"valid": False, "issues": error.issues}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
