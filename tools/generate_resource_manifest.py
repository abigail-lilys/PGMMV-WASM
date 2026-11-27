from pathlib import Path
import json
import time
import sys

repo = Path.home() / "pgmmv-wasm"
src = repo / "dist" / "Resources"
dst = Path("/storage/emulated/0/Download/dist/Resources")
old_path = dst / "manifest.json"

if not src.is_dir():
    sys.exit(f"错误：资源源目录不存在：{src}")

if not dst.is_dir():
    sys.exit(f"错误：外部资源目录不存在：{dst}")

old = {}
if old_path.is_file():
    try:
        old = json.loads(old_path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"旧 manifest.json 无法读取：{e}")

files = []
total = 0

for path in sorted(src.rglob("*")):
    if not path.is_file() or path.name == "manifest.json":
        continue

    rel = path.relative_to(src).as_posix()
    size = path.stat().st_size
    files.append({"p": rel, "s": size})
    total += size

if not files:
    sys.exit("错误：源目录中没有找到资源文件，未覆盖清单。")

manifest = {
    key: value
    for key, value in old.items()
    if key not in ("format", "files", "total", "version")
}
manifest["format"] = 1
manifest.setdefault("root", "/app/Resources")
manifest["version"] = str(time.time_ns())
manifest["total"] = total
manifest["files"] = files

content = json.dumps(
    manifest, ensure_ascii=False, indent=2
) + "\n"

(src / "manifest.json").write_text(content, encoding="utf-8")
(dst / "manifest.json").write_text(content, encoding="utf-8")

print("manifest.json 已重新生成并覆盖外部旧版本")
print(f"资源文件数：{len(files)}")
print(f"资源总大小：{total:,} bytes")
print(f"版本标识：{manifest['version']}")
print(f"清单 root：{manifest['root']}")

target = next((f for f in files if f["p"] == "img/006.png"), None)
print(f"img/006.png 清单记录：{target}")
