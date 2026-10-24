import json
from .cli import main

try:
    raise SystemExit(main())
except Exception as exc:
    print(json.dumps({"status": "BLOCKED", "code": getattr(exc, "code", "RUNTIME_ERROR"),
                      "error_type": type(exc).__name__}), flush=True)
    raise SystemExit(2)
