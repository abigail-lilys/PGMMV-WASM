from pathlib import Path
import re
import shutil
import sys

p = Path.home() / "PGMMV-src/Player/Classes/Manager/GameManager.cpp"
raw = p.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")
has_crlf = b"\r\n" in raw
s = raw.decode("utf-8-sig").replace("\r\n", "\n")

start = s.find("void GameManager::loadJsonFile(")
end = s.find("void GameManager::loadProjectData(", start)

if start < 0 or end < 0:
    raise SystemExit("找不到 loadJsonFile() 函数边界；源码未修改。")

fn = s[start:end]
if "[PGMMV-DIAG]" in fn:
    raise SystemExit("诊断日志已经存在，不重复打补丁。")

read_re = re.compile(
    r'(?m)^(?P<i>[ \t]*)'
    r'(?:(?:const\s+)?auto|std::string)\s+jsonData\s*=\s*'
    r'FileUtils::getInstance\(\)->getStringFromFile\(\s*filePath\s*\)\s*;'
    r'[ \t]*(?://[^\n]*)?$'
)

parse_re = re.compile(
    r'(?m)^(?P<i>[ \t]*)doc\.Parse\(jsonData\.c_str\(\)\);\n'
    r'(?P=i)bool error = doc\.HasParseError\(\);[ \t]*$'
)

create_re = re.compile(
    r'(?m)^(?P<i>[ \t]*)auto project = '
    r'agtk::data::ProjectData::create\(doc, projectPath\);\n'
    r'(?P=i)this->setProjectData\(project\);[ \t]*$'
)

checks = [
    ("读取 JSON 的语句", read_re, fn),
    ("JSON 解析语句", parse_re, fn),
    ("ProjectData 创建语句", create_re, fn),
]

for label, pattern, text in checks:
    count = len(list(pattern.finditer(text)))
    if count != 1:
        print(f"定位失败：{label}，匹配数={count}")
        print("相关源码：")
        for n, line in enumerate(fn.splitlines(), 1):
            if any(k in line for k in (
                "getStringFromFile", "doc.Parse", "HasParseError",
                "ProjectData::create", "setProjectData"
            )):
                print(f"{n}: {line}")
        raise SystemExit("未修改源码。请导出上述源码上下文再继续。")

read_diag = r'''
unsigned int b0 = jsonData.empty() ? 0 : (unsigned char)jsonData[0];
unsigned int b1 = jsonData.size() < 2 ? 0 : (unsigned char)jsonData[1];
unsigned int b2 = jsonData.size() < 3 ? 0 : (unsigned char)jsonData[2];
unsigned int b3 = jsonData.size() < 4 ? 0 : (unsigned char)jsonData[3];
CCLOG("[PGMMV-DIAG] path=%s projectPath=%s size=%lu head=%02X %02X %02X %02X",
    filePath.c_str(), projectPath.c_str(),
    (unsigned long)jsonData.size(), b0, b1, b2, b3);
'''

parse_diag = r'''
CCLOG("[PGMMV-DIAG] parseError=%d parseCode=%d offset=%lu rootObject=%d",
    error ? 1 : 0, (int)doc.GetParseError(),
    (unsigned long)doc.GetErrorOffset(), doc.IsObject() ? 1 : 0);
if (doc.IsObject()) {
    CCLOG("[PGMMV-DIAG] keys gameIcon=%d gameType=%d tileWidth=%d tileHeight=%d screenWidth=%d screenHeight=%d sceneList=%d inputMapping=%d",
        doc.HasMember("gameIcon"), doc.HasMember("gameType"),
        doc.HasMember("tileWidth"), doc.HasMember("tileHeight"),
        doc.HasMember("screenWidth"), doc.HasMember("screenHeight"),
        doc.HasMember("sceneList"), doc.HasMember("inputMapping"));
}
'''

def inject(match, extra):
    indent = match.group("i")
    lines = extra.strip("\n").splitlines()
    addition = "\n".join(indent + line if line else "" for line in lines)
    return match.group(0) + "\n" + addition

fn = read_re.sub(lambda m: inject(m, read_diag), fn, count=1)
fn = parse_re.sub(lambda m: inject(m, parse_diag), fn, count=1)

def replace_create(m):
    i = m.group("i")
    return (
        f"{i}auto project = agtk::data::ProjectData::create(doc, projectPath);\n"
        f'{i}CCLOG("[PGMMV-DIAG] create returned=%p", (void*)project);\n'
        f"{i}this->setProjectData(project);\n"
        f'{i}CCLOG("[PGMMV-DIAG] after set=%p", (void*)this->getProjectData());'
    )

fn = create_re.sub(replace_create, fn, count=1)
s = s[:start] + fn + s[end:]

backup = p.with_name(p.name + ".before-pd-diag2")
n = 2
while backup.exists():
    backup = p.with_name(p.name + f".before-pd-diag2.{n}")
    n += 1

shutil.copy2(p, backup)
output = ("\ufeff" if has_bom else "") + s
if has_crlf:
    output = output.replace("\n", "\r\n")
p.write_bytes(output.encode("utf-8"))

print("诊断补丁应用成功。")
print("备份：", backup)
print("修改：", p)
