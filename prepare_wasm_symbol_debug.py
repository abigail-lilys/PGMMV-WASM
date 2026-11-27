from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

ROOT = Path.home() / "pgmmv-wasm"
BUILD = ROOT / "build"
FLAGS_DIR = BUILD / "CMakeFiles"
LINK_FILE = FLAGS_DIR / "pgmmv.dir" / "link.txt"
RUNTIME = BUILD / "runtime"

if not FLAGS_DIR.is_dir():
    sys.exit("错误：找不到 build/CMakeFiles")

if not LINK_FILE.is_file():
    sys.exit("错误：找不到 pgmmv.dir/link.txt")

# 备份旧的 WASM 和映射文件
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = ROOT / "symbol_debug_backup" / stamp
backup.mkdir(parents=True, exist_ok=True)

for name in (
    "pgmmv.js",
    "pgmmv.wasm",
    "pgmmv.wasm.map",
    "pgmmv.js.symbols",
):
    src = RUNTIME / name
    if src.is_file():
        shutil.copy2(src, backup / name)

print("旧构建文件备份：", backup)

# 所有本地 CMake 目标都加入精简 DWARF 行号信息
flags_files = sorted(FLAGS_DIR.rglob("flags.make"))
changed = 0

for path in flags_files:
    lines = path.read_text(errors="replace").splitlines()
    modified = False

    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(C_FLAGS|CXX_FLAGS)\s*=(.*)$", line)
        if not m:
            continue

        indent, key, args = m.groups()
        args = args.strip()

        if "-gline-tables-only" not in args.split():
            args += " -gline-tables-only"
            modified = True

        if key == "CXX_FLAGS":
            if "-Wcast-function-type" not in args.split():
                args += " -Wcast-function-type"
                modified = True

        lines[i] = f"{indent}{key} = {args}"

    if modified:
        path.write_text("\n".join(lines) + "\n")
        changed += 1

# 修复链接参数：去掉重复设置，避免 ASSERTIONS=1 覆盖 ASSERTIONS=2
link = LINK_FILE.read_text()

for setting in (
    "ASSERTIONS",
    "SAFE_HEAP",
    "STACK_OVERFLOW_CHECK",
):
    link = re.sub(
        rf"(?<!\S)-s{setting}(?:=[^\s]+)?",
        "",
        link,
    )

# 确保生成 source map、函数名和符号索引
required = [
    "-gsource-map",
    "--emit-symbol-map",
    "--profiling-funcs",
    "-sASSERTIONS=2",
    "-sSTACK_OVERFLOW_CHECK=2",
    "-sSAFE_HEAP=1",
]

for flag in required:
    if flag not in link.split():
        link += " " + flag

LINK_FILE.write_text(link.strip() + "\n")

print("已修改 flags.make 数量：", changed)
print("已更新链接参数：")
for flag in required:
    print("  ", flag)

print("\n构建前检查：")
print("  编译阶段：-gline-tables-only")
print("  C++警告：-Wcast-function-type")
print("  链接阶段：-gsource-map")
print("  运行时：ASSERTIONS=2 / SAFE_HEAP=1")
print("  输出目录：", RUNTIME)
