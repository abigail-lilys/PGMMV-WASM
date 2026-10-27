import base64, json, os, shutil, sys
from pathlib import Path
from pgmm_decrypt import decrypt_pgmm_key, decrypt_pgmm_resource

do_apply = '--apply' in sys.argv
root = Path.home() / "pgmmv-wasm/test_game/Resources"
info = root / "data/info.json"
if not info.is_file():
    raise SystemExit(f"info.json not found: {info}")
meta = json.loads(info.read_text(encoding="utf-8-sig"))
if "key" not in meta:
    raise SystemExit("info.json has no 'key'")
key = decrypt_pgmm_key(base64.b64decode(meta["key"]))
print(f"key: {len(key)} bytes")

# 只处理这些目录；data 目录里有 project.json 的 .bak 备份，跳过
dirs = ["img", "audio", "fonts", "script", "plugins"]
total = enc = ok = fail = 0
for d in dirs:
    p = root / d
    if not p.is_dir():
        continue
    for f in sorted(p.rglob("*")):
        if not f.is_file():
            continue
        total += 1
        with open(f, "rb") as fh:
            if fh.read(3) != b"enc":
                continue
        enc += 1
        raw = f.read_bytes()
        try:
            clear = decrypt_pgmm_resource(raw, key)
        except Exception as e:
            print(f"FAIL {f.relative_to(root)}: {e}")
            fail += 1
            continue
        if len(clear) < 8:
            print(f"SHORT {f.relative_to(root)}: clear={len(clear)}")
            fail += 1
            continue
        print(f"{'APPLY' if do_apply else 'DRY'} {f.relative_to(root)}: enc={len(raw)} clear={len(clear)} head={clear[:8].hex()}")
        ok += 1
        if do_apply:
            backup = f.with_name(f.name + ".before-decrypt.bak")
            n = 2
            while backup.exists():
                backup = f.with_name(f.name + f".before-decrypt.{n}.bak")
                n += 1
            shutil.copy2(f, backup)
            tmp = f.with_name(f.name + ".tmp")
            tmp.write_bytes(clear)
            tmp.replace(f)
print(f"--- summary: total={total} enc={enc} ok={ok} fail={fail}")
if not do_apply:
    print("DRY-RUN only; add --apply to write")
