#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ctor_name_and_ptr_cmp_v3.py — v2 的修正版。

v2 要求 "cocos2d::Rect::Rect(0, 0, 1, 1)" 唯一匹配，但 Object.cpp 里 20050 与 20080 两行完全相同，
于是第二次也 ABORT。v3 的规则：Rect::Rect 匹配到几处就替换几处（当前 3 处：20050/20080 的 0,0,1,1
与 20242 的 0,0,8,8），Color4F::Color4F 与 parentObject > 0 仍要求唯一匹配。
类型::构造函数名(...) 是 MSVC 扩展，改成 类型(...) 语义等价。

用法：
  python3 patch_ctor_name_and_ptr_cmp_v3.py            # dry-run
  python3 patch_ctor_name_and_ptr_cmp_v3.py --apply    # 写入（要求所有目标文件在 git 里干净）
幂等：文件里不再有该模式就跳过；已有标记的行不重复处理。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
MARKER = b'// [wasm-port] std ctor/ptr'

# (rel, pattern, repl_fn, require_unique)
RULES = [
    ('Player/Classes/Lib/Object.cpp',
     re.compile(rb'cocos2d::Rect::Rect\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)'),
     lambda m: b'cocos2d::Rect(' + m.group(1) + b', ' + m.group(2) + b', ' + m.group(3) + b', ' + m.group(4) + b')',
     False),
    ('Player/Classes/Lib/RenderTexture.cpp',
     re.compile(rb'cocos2d::Color4F::Color4F\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)'),
     lambda m: b'cocos2d::Color4F(0, 0, 0, 0)',
     True),
    ('Player/Classes/Lib/ObjectCommand.cpp',
     re.compile(rb'if \(parentObject > 0\)'),
     lambda m: b'if (parentObject != nullptr)',
     True),
]

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def process(data, pat, repl_fn, marker):
    matches = list(pat.finditer(data))
    if not matches:
        return data, 0
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
    for rel, pat, repl_fn, uniq in RULES:
        path = os.path.join(REPO, rel)
        data = open(path, 'rb').read()
        matches = list(pat.finditer(data))
        if not matches:
            print('[skip] %s: no match for %s' % (rel, pat.pattern.decode('utf-8', 'replace')))
            continue
        if uniq and len(matches) != 1:
            print('ABORT: %s: pattern matched %d times, expected 1' % (rel, len(matches))); sys.exit(1)
        new, n = process(data, pat, repl_fn, MARKER)
        results.append((rel, data, new, len(matches)))
    if not results:
        print('nothing to do.')
        return
    for rel, old, new, n in results:
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
    for rel, old, new, n in results:
        open(os.path.join(REPO, rel), 'wb').write(new)
        print('    written: %s' % rel)

if __name__ == '__main__':
    main()
