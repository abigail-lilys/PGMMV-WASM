#!/data/data/com.termux/files/usr/bin/bash
# PGMMV 运行时结构调查：JS 加载方式 / JSB 脚本顺序 / ScriptingCore 执行点
set -u

cd "$HOME/pgmmv-wasm" 2>/dev/null || { echo "cd ~/pgmmv-wasm 失败"; exit 1; }

DIST_RES="/storage/emulated/0/Download/dist/Resources"
SRC="$HOME/PGMMV-src/Player"
SRC_RES="$SRC/Resources"
SCRIPTING_CORE="$SRC/cocos2d/cocos/scripting/js-bindings/manual/ScriptingCore.cpp"

echo "======================================================"
echo " 1) 搜索 JS 里的 cc.Class / Class 定义（引擎类型）"
echo "======================================================"
python - "$DIST_RES" "$SRC_RES" <<'PY'
import sys, re
from pathlib import Path

roots = [Path(p) for p in sys.argv[1:]]
patterns = [
    r'cc\s*\.\s*Class',
    r'cc\s*\[\s*["\']Class["\']\s*\]',
    r'Class\s*=\s*function',
    r'Class\s*=\s*\([^)]*\)\s*=>',
]

for root in roots:
    if not root.exists():
        print(f"\n[SKIP] 不存在: {root}")
        continue
    print(f"\n========== 目录: {root} ==========")
    files = sorted(root.rglob("*.js"))
    print(f"共 {len(files)} 个 .js")

    for p in files:
        try:
            data = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raw = p.read_bytes()
            print(f"\n[UTF8 ERROR] {p}")
            print(f"  offset={e.start}, bytes={raw[e.start:e.start+16].hex()}")
            continue

        found = []
        for pat in patterns:
            for m in re.finditer(pat, data):
                line = data.count("\n", 0, m.start()) + 1
                snip = data[max(0, m.start()-100):m.start()+180].replace("\n", " ")
                found.append((line, snip[:260]))

        if found:
            print(f"\n--- {p} ---")
            for line, snip in found[:12]:
                print(f"L{line}: {snip}")

print("\n扫描结束。")
PY

echo
echo "======================================================"
echo " 2) 资源清单里跟脚本加载相关的字段"
echo "======================================================"
python - "$DIST_RES" <<'PY'
import sys, re
from pathlib import Path

root = Path(sys.argv[1])
for name in ("manifest.json", "data/project.json", "data/info.json",
             "project.json", "game.json"):
    p = root / name
    if not p.exists():
        continue
    print(f"\n--- {name} ---")
    s = p.read_text(encoding="utf-8", errors="replace")
    hits = list(re.finditer(r'.{0,100}(?:jsb_boot|jsb_cocos2d|jsb\.js|script|\.js\b).{0,160}', s, re.I))
    if not hits:
        print("  (无相关字段)")
    for m in hits[:20]:
        print("  " + m.group(0).replace("\n", " ")[:260])
PY

echo
echo "======================================================"
echo " 3) ScriptingCore 里脚本执行位置"
echo "======================================================"
if [ -f "$SCRIPTING_CORE" ]; then
  grep -n -E 'compileScript|runScript|JS::Evaluate|JS_ExecuteScript' \
    "$SCRIPTING_CORE" | head -80
else
  echo "[SKIP] 不存在: $SCRIPTING_CORE"
  echo "      如果你本地没拉源码，这一步只看 dist 结果即可。"
fi

echo
echo "完成。"
