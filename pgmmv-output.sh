#!/data/data/com.termux/files/usr/bin/bash
set -eu
set -o pipefail

SRC="${1:-}"
if [ -z "$SRC" ]; then
  echo "用法: $0 <资源目录> [输出目录] [游戏名]"
  echo "例:   $0 /storage/emulated/0/0webpgmmv/lewdgod/Resources"
  echo "      $0 /storage/emulated/0/0webpgmmv/lewdgod/Resources /storage/emulated/0/0webpgmmv/lewdgod_out lewdgod"
  exit 1
fi

if [ ! -d "$SRC" ]; then
  echo "错误: 源资源目录不存在: $SRC"
  exit 1
fi
SRC="$(cd "$SRC" && pwd)"

GAME_NAME="${3:-$(basename "$(dirname "$SRC")")}"
OUT="${2:-$(dirname "$SRC")/${GAME_NAME}_out}"

REPO="$HOME/pgmmv-wasm"
VENV="$REPO/.venv-pgmm-decrypt"

echo "源资源:    $SRC"
echo "输出目录:  $OUT"
echo "游戏名:    $GAME_NAME"
echo

if [ ! -d "$REPO/dist" ]; then
  echo "错误: $REPO/dist 不存在"
  exit 1
fi

# 1. 准备输出目录
mkdir -p "$OUT"
rm -rf "$OUT/Resources" "$OUT/runtime" "$OUT/index.html"
cp -a "$SRC" "$OUT/Resources"

# 2. 解密
if [ -f "$VENV/bin/activate" ]; then
  . "$VENV/bin/activate"
fi
DECRYPT_PROJECT="$REPO/decrypt_project.py"
DECRYPT_RES="$REPO/decrypt_resources.py"
if [ -f "$DECRYPT_PROJECT" ]; then
  echo "[解密] decrypt_project.py $OUT/Resources"
  python "$DECRYPT_PROJECT" "$OUT/Resources" || echo "[警告] decrypt_project.py 返回非零，继续"
fi
if [ -f "$DECRYPT_RES" ]; then
  echo "[解密] decrypt_resources.py --apply $OUT/Resources"
  if ! python "$DECRYPT_RES" --apply "$OUT/Resources"; then
    echo "错误: decrypt_resources.py 执行失败"
    exit 1
  fi
fi

# 3. 生成 manifest.json
echo "[manifest] 生成 manifest.json"
python - "$OUT/Resources" <<'PY'
import json, os, sys, time
root = sys.argv[1]
files, total = [], 0
for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        if fn == "manifest.json":
            continue
        if ".before-decrypt" in fn or fn.endswith(".tmp"):
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, root).replace(os.sep, "/")
        size = os.path.getsize(full)
        files.append({"p": rel, "s": size})
        total += size
files.sort(key=lambda x: x["p"])
manifest = {
    "root": "/app/Resources",
    "format": 1,
    "version": str(int(time.time() * 1000)),
    "total": total,
    "files": files,
}
with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))
print(f"  {len(files)} 个文件, total={total}")
PY

# 4. 复制前端壳与运行时
echo "[复制] index.html + runtime"
cp "$REPO/dist/index.html" "$OUT/index.html"
mkdir -p "$OUT/runtime"
if [ -f "$REPO/build/runtime/pgmmv.js" ] && [ -f "$REPO/build/runtime/pgmmv.wasm" ]; then
  cp "$REPO/build/runtime/pgmmv.js"   "$OUT/runtime/pgmmv.js"
  cp "$REPO/build/runtime/pgmmv.wasm" "$OUT/runtime/pgmmv.wasm"
  echo "  使用 build/runtime（最新构建）"
else
  echo "  [警告] build/runtime 缺失，回退 dist/runtime（旧产物）"
  cp "$REPO/dist/runtime/pgmmv.js"   "$OUT/runtime/pgmmv.js"
  cp "$REPO/dist/runtime/pgmmv.wasm" "$OUT/runtime/pgmmv.wasm"
fi

# 5. 完成
echo
echo "[完成] 输出目录: $OUT"
echo "  index.html"
echo "  runtime/pgmmv.js, pgmmv.wasm"
echo "  Resources/manifest.json + 资源"
echo
echo "启动（必需，除非容器支持 file:// + COI）:"
echo "  cd \"$OUT\" && python3 \"$REPO/serve.py\" 8000"
echo "  浏览器打开 http://127.0.0.1:8000/"
echo
echo "注意: 直接双击 index.html (file://) 会因 SharedArrayBuffer/fetch CORS 失败，"
echo "      标准浏览器不支持无服务器运行。"
