"""Start the local multi-page draft box editor without any remote service."""
import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))


def main():
    parser = argparse.ArgumentParser(description="离线人工预框：导入书页、自动候选、调整框、保存和导出")
    parser.add_argument("--workspace", required=True, help="本机草稿目录；再次启动使用同一目录")
    parser.add_argument("--images", nargs="*", default=[], help="首次可选导入的PNG/JPEG路径")
    parser.add_argument("--port", type=int, default=0, help="默认随机可用本机端口")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("端口须为0至65535")
    from annotation.prebox.store import Workspace
    from annotation.prebox.server import make_server
    workspace = Workspace(Path(args.workspace))
    if args.images:
        files = [{"name": Path(p).name, "data_base64": base64.b64encode(Path(p).read_bytes()).decode("ascii")} for p in args.images]
        workspace.import_images(files, workspace.state()["revision"])
    server = make_server(workspace, port=args.port)
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}", "workspace": str(Path(args.workspace).resolve()),
                      "pages": len(workspace.state()["pages"]), "decision": "HOLD"}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
