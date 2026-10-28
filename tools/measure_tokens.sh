#!/usr/bin/env bash
# tools/measure_tokens.sh <会话目录(Windows 路径)>
# 作用：把会话目录内联进 measure_tokens.mjs 的临时副本（ego 不继承环境变量），再用 ego 的 Node 跑
set -u
DIR="${1:?用法: measure_tokens.sh <会话目录>}"
SRC="/c/Users/LIHAOYANG/Desktop/网页标注自动化/tools/measure_tokens.mjs"
TMP="/c/anno-helper/_mt_run.mjs"
mkdir -p /c/anno-helper

python - "$DIR" "$SRC" "$TMP" <<'PYEOF'
import sys
d, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src, encoding="utf-8").read()
s = s.replace("const dir = process.argv[2] || process.env.SESSION_DIR;",
              "const dir = %r;" % d.replace("/", "\\\\"))
open(dst, "w", encoding="utf-8").write(s)
print("runner ->", dst)
PYEOF

export PATH="/c/Users/LIHAOYANG/.local/share/ego/active_version_dir:$PATH"
ego-browser.exe nodejs < "$TMP" 2>&1 | grep -v "ego-browser:notice"
