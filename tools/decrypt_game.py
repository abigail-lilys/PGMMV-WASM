#!/usr/bin/env python3
"""decrypt_game.py <Resources dir> -- decrypt PGMMV 'enc' files in place (run on a COPY, no backups).
Merges decrypt_project.py + decrypt_resources.py; same pgmm_decrypt calls, path is a parameter.
Exit code: 0 ok, 1 some files failed, 2 bad input."""
import base64, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent, Path.home() / "pgmmv-wasm"):
    sys.path.insert(0, str(p))
try:
    from pgmm_decrypt import decrypt_pgmm_key, decrypt_pgmm_resource
except ImportError:
    sys.exit("pgmm_decrypt.py not found (looked in tools/, repo root, ~/pgmmv-wasm)")

if len(sys.argv) < 2:
    sys.exit(2)
root = Path(sys.argv[1])
info = root / "data" / "info.json"
key = None
if info.is_file():
    meta = json.loads(info.read_text(encoding="utf-8-sig"))
    if meta.get("key"):
        key = decrypt_pgmm_key(base64.b64decode(meta["key"]))
        print(f"key: {len(key)} bytes")
else:
    print("warning: data/info.json not found, trying legacy decrypt (key=None)")

total = enc = ok = fail = 0
for d in ["data", "img", "audio", "fonts", "script", "plugins"]:
    base = root / d
    if not base.is_dir():
        continue
    for f in sorted(base.rglob("*")):
        if not f.is_file() or f.name == "info.json":
            continue
        total += 1
        raw = f.read_bytes()
        if raw[:3] != b"enc":
            continue
        enc += 1
        try:
            clear = decrypt_pgmm_resource(raw, key)
            if len(clear) < 8:
                raise ValueError(f"clear text too short ({len(clear)})")
            if f.name == "project.json":
                json.loads(clear.decode("utf-8-sig"))
        except Exception as e:
            print(f"FAIL {f.relative_to(root)}: {e}")
            fail += 1
            continue
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_bytes(clear)
        tmp.replace(f)
        ok += 1
print(f"decrypt summary: total={total} enc={enc} ok={ok} fail={fail}")
sys.exit(1 if fail else 0)
