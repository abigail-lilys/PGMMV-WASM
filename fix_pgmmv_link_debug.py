from pathlib import Path
import re

p = Path("build/CMakeFiles/pgmmv.dir/link.txt")
if not p.exists():
    raise SystemExit("找不到 link.txt")

s = p.read_text()

# 暂时撤销上一轮附加的选项
for flag in (
    "--profiling-funcs",
    "-sSAFE_HEAP=1",
    "-sSTACK_OVERFLOW_CHECK=2",
):
    s = s.replace(flag, "")

# 去除所有 ASSERTIONS 设置，再明确只设置一次为 2
s = re.sub(r"(?<!\S)-sASSERTIONS(?:=[^\s]+)?", "", s)
s = re.sub(r"\s+", " ", s).strip()
s += " -sASSERTIONS=2\n"

p.write_text(s)

print("已更新链接参数：")
print(s)
