"""Collect/check local source-region OCR for unbound candidate items."""
import argparse
import json
from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from annotation.recognition.source_region_ocr import collect, check_inventory


def blocked(*args, **kwargs):
    raise RuntimeError("SOURCE_REGION_OCR_NETWORK_DISABLED")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("collect")
    run.add_argument("--spec", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("check")
    check.add_argument("--run", type=Path, required=True)
    args = parser.parse_args(argv)
    socket.create_connection = socket.getaddrinfo = blocked
    socket.socket.connect = socket.socket.connect_ex = blocked
    if args.command == "collect":
        result = collect(args.spec, args.out)
        result = {key: result[key] for key in ("status", "inference_calls", "wall_seconds")}
    else:
        result = check_inventory(args.run)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
