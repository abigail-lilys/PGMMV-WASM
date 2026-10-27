import base64
import json
import shutil
from pathlib import Path

from pgmm_decrypt import decrypt_pgmm_key, decrypt_pgmm_resource

root = Path.home() / "pgmmv-wasm/test_game"
src = root / "Resources/data/project.json"

if not src.is_file():
    matches = list(root.rglob("project.json"))
    if len(matches) != 1:
        raise SystemExit(
            f"无法唯一定位 project.json：{matches[:10]}"
        )
    src = matches[0]

info = src.parent / "info.json"
if not info.is_file():
    matches = list(root.rglob("info.json"))
    if len(matches) == 1:
        info = matches[0]

key = None

if info.is_file():
    metadata = json.loads(info.read_text(encoding="utf-8-sig"))
    encoded_key = metadata.get("key")
    if encoded_key:
        key = decrypt_pgmm_key(
            base64.b64decode(encoded_key)
        )
        print(f"已读取解密密钥：{len(key)} bytes")
else:
    print("警告：未找到 info.json，将尝试旧式解密")

raw = src.read_bytes()
print(f"目标：{src}")
print(f"文件大小：{len(raw)} bytes")
print(f"原始文件头：{raw[:16]!r}")

if not raw.startswith(b"enc"):
    try:
        json.loads(raw.decode("utf-8-sig"))
        print("project.json 已经是有效 JSON，无需解密")
        raise SystemExit(0)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SystemExit(
            "文件既不是标准 enc 格式，也不是有效 JSON；未修改文件"
        )

clear = decrypt_pgmm_resource(raw, key)

try:
    document = json.loads(clear.decode("utf-8-sig"))
except (UnicodeDecodeError, json.JSONDecodeError) as exc:
    candidate = src.with_name(
        src.name + ".decrypted-candidate"
    )
    candidate.write_bytes(clear)
    raise SystemExit(
        f"解密结果未通过 JSON 校验：{exc}\n"
        f"原文件未修改；诊断输出：{candidate}"
    )

backup = src.with_name(src.name + ".before-decrypt.bak")
n = 2
while backup.exists():
    backup = src.with_name(
        src.name + f".before-decrypt.{n}.bak"
    )
    n += 1

tmp = src.with_name(src.name + ".tmp")

try:
    shutil.copy2(src, backup)
    tmp.write_bytes(clear)
    tmp.replace(src)
except Exception:
    if tmp.exists():
        tmp.unlink()
    raise

print("解密成功，JSON 解析通过")
print(f"备份：{backup}")
print(f"替换文件：{src}")
print(f"解密后大小：{len(clear)} bytes")
print(f"JSON 根节点类型：{type(document).__name__}")
print(f"解密后文件头：{src.read_bytes()[:16]!r}")
