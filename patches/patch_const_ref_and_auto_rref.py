#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_const_ref_and_auto_rref.py — 第 4/6 类：临时对象绑非 const 左值引用。

函数体只读参数（已核实），改形参为 const&，调用点不动：
  1) CollisionUtils.hpp / .cpp 的 std::vector<CollisionLine>& wallList
  2) Object.cpp 的 getFilteredListByTileGroup(..., std::vector<agtk::Tile *> &list, ...)
  3) Object.cpp 的 updateObjectOverlapMaskEffect(..., std::vector<agtk::Tile *> &tileList, ...)
  4) Scene.cpp 的 auto &attackVert2 / auto &hitVert1（get*VertListCache() 返回临时对象）-> auto &&

用法：
  python3 patch_const_ref_and_auto_rref.py            # dry-run
  python3 patch_const_ref_and_auto_rref.py --apply    # 写入（要求所有目标文件在 git 里干净）
幂等：插入行带 "// [wasm-port] const-ref" 或 "// [wasm-port] auto-rref" 标记；有标记就跳过。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
MARK1 = b'// [wasm-port] const-ref'
MARK2 = b'// [wasm-port] auto-rref'

RULES = [
    # (rel, pattern, repl_fn, marker, require_unique)
    ('Player/Classes/External/collision/CollisionUtils.hpp',
     re.compile(rb'std::vector<CollisionLine>& wallList'),
     lambda m: b'const std::vector<CollisionLine>& wallList',
     MARK1, True),
    ('Player/Classes/External/collision/CollisionUtils.cpp',
     re.compile(rb'std::vector<CollisionLine>& wallList'),
     lambda m: b'const std::vector<CollisionLine>& wallList',
     MARK1, True),
    ('Player/Classes/Lib/Object.cpp',
     re.compile(rb'(std::vector<agtk::Tile \*> getFilteredListByTileGroup\()std::vector<agtk::Tile \*> &list(, int collideWithTileGroupBit\))'),
     lambda m: m.group(1) + b'const std::vector<agtk::Tile *> &list' + m.group(2),
     MARK1, True),
    ('Player/Classes/Lib/Object.cpp',
     re.compile(rb'(void updateObjectOverlapMaskEffect\(agtk::Object \*object, )std::vector<agtk::Tile \*> &tileList(, agtk::data::TileData::EnumConditionType conditionType\))'),
     lambda m: m.group(1) + b'const std::vector<agtk::Tile *> &tileList' + m.group(2),
     MARK1, True),
    ('Player/Classes/Lib/Scene.cpp',
     re.compile(rb'\bauto &attackVert2 = '),
     lambda m: b'auto &&attackVert2 = ',
     MARK2, True),
    ('Player/Classes/Lib/Scene.cpp',
     re.compile(rb'\bauto &hitVert1 = '),
     lambda m: b'auto &&hitVert1 = ',
     MARK2, True),
]

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def process(data, pat, repl_fn, marker, uniq):
    matches = list(pat.finditer(data))
    if not matches:
        return data, 0
    if uniq and len(matches) != 1:
        print('ABORT: pattern matched %d times, expected 1' % len(matches)); sys.exit(1)
    new = data
    for m in reversed(matches):
        line_end = new.find(b'\n', m.start())
        if line_end < 0:
            line_end = len(new)
        line_start = new.rfind(b'\n', 0, m.start()) + 1
        line = new[line_start:line_end]
        if marker in line:
            continue
        new = new[:m.start()] + repl_fn(m) + new[m.end():line_end] + b' ' + marker + new[line_end:]
    return new, len(matches)

def main():
    results = []
    for rel, pat, repl_fn, marker, uniq in RULES:
        path = os.path.join(REPO, rel)
        data = open(path, 'rb').read()
        matches = list(pat.finditer(data))
        if not matches:
            print('[skip] %s: no match for %s' % (rel, pat.pattern.decode('utf-8', 'replace')))
            continue
        new, n = process(data, pat, repl_fn, marker, uniq)
        results.append((rel, data, new, marker, len(matches)))
    if not results:
        print('nothing to do.')
        return
    for rel, old, new, marker, n in results:
        print('=== %s: %d match(es) ===' % (rel, n))
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        for i, (a, b) in enumerate(zip(old_lines, new_lines)):
            if a != b:
                print('>>> %4d  %s' % (i + 1, b.decode('utf-8', 'replace').rstrip('\r\n')))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    rels = [r[0] for r in results]
    if not git_clean(rels):
        print('ABORT: 有文件在 git 里不干净'); sys.exit(1)
    for rel, old, new, marker, n in results:
        open(os.path.join(REPO, rel), 'wb').write(new)
        print('    written: %s' % rel)

if __name__ == '__main__':
    main()
