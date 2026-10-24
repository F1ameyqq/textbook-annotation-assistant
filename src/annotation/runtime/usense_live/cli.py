import argparse
import asyncio
import json

from .config import configure
from .core import doctor, freeze, load_binding, load_login_binding, parse, profile_identity


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book 46007447 guarded read/login runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--config")
    d.add_argument("--sha256")
    c = sub.add_parser("configure")
    c.add_argument("--profile", required=True)
    c.add_argument("--output-root", required=True)
    c.add_argument("--config", required=True)
    for actor in ("coordinator", "executor", "reviewer"):
        c.add_argument("--"+actor, required=True)
    c.add_argument("--authorization-reference", required=True)
    c.add_argument("--tls-approval-reference")
    c.add_argument("--proxy-server", help="Explicit credentialless http://127.0.0.1:port; no automatic system proxy or fallback")
    c.add_argument("--orders", type=int, nargs="*", default=[])
    c.add_argument("--pages", type=int, nargs="*", default=[])
    c.add_argument("--source", action="store_true")
    c.add_argument("--login", action="store_true")
    c.add_argument("--seconds", type=int, default=600)
    for command in ("validate", "capture", "login", "export"):
        action = sub.add_parser(command)
        action.add_argument("--config", required=True)
        action.add_argument("--sha256", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--draft", required=True)
    f.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "configure":
        kwargs = vars(args).copy()
        del kwargs["command"]
        kwargs["config_path"] = kwargs.pop("config")
        result = configure(**kwargs)
        status = 0
    elif args.command == "doctor":
        result = doctor(args.config, args.sha256)
        status = 0 if not result["missing"] else 2
    elif args.command == "freeze":
        result = freeze(args.draft, args.output)
        status = 0
    elif args.command == "validate":
        from pathlib import Path
        data = parse(Path(args.config).read_bytes())
        loader = load_login_binding if data.get("operation") == "MANUAL_LOGIN_ONLY" else load_binding
        loader(args.config, args.sha256).check(profile=True)
        result = {"configuration_valid": True, "platform_ready": False, "resources_created": False}
        status = 0
    elif args.command == 'export':
        from .native_export import capture
        result=asyncio.run(capture(args.config,args.sha256))
        status=0 if result['status']=='NATIVE_EXPORT_CAPTURED_PENDING_MAPPING' and result['release']['context_runtime_release_confirmed'] else 2
    elif args.command == "capture":
        from .capture import capture
        result = asyncio.run(capture(args.config, args.sha256))
        status = 0 if result["status"] == "NATIVE_GETS_CAPTURED" else 2
    else:
        from .login import run
        result = asyncio.run(run(args.config, args.sha256))
        status = 0 if result["status"] == "LOGIN_HTTP200_NAVIGATION_OBSERVED" else 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return status
