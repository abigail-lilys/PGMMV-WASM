#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_ctor_name_and_ptr_cmp.py — 三处 MSVC 扩展写法改成标准 C++。

1) Object.cpp:20050  cocos2d::Rect::Rect(0, 0, 1, 1)      -> cocos2d::Rect(0, 0, 1, 1)
2) RenderTexture.cpp:210  cocos2d::Color4F::Color4F(0,0,0,0) -> cocos2d::Color4F(0,0,0,0)
3) ObjectCommand.cpp:1650  if (parentObject > 0)          -> if (parentObject != nullptr)

原因：类型::构造函数名(...) 是 MSVC 扩展；指针与 int 比较 clang 拒绝。

用法：
  python3 patch_ctor_name_and_ptr_cmp.py            # dry-run
  python3 patch_ctor_name_and_ptr_cmp.py --apply    # 写入（要求所有目标文件在 git 里干净）
幂等：每处替换后文件里不再有该模式就跳过。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
MARKER = b'// [wasm-port] std ctor/ptr'

RULES = [
    ('Player/Classes/Lib/Object.cpp',
     re.compile(rb'cocos2d::Rect::Rect\('),
     lambda m: b'cocos2d::Rect('),
    ('Player/Classes/Lib/RenderTexture.cpp',
     re.compile(rb'cocos2d::Color4F::Color4F\('),
     lambda m: b'cocos2d::Color4F('),
    ('Player/Classes/Lib/ObjectCommand.cpp',
     re.compile(rb'if \(parentObject > 0\)'),
     lambda m: b'if (parentObject != nullptr)'),
]

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    results = []
    for rel, pat, rep in RULES:
        path = os.path.join(REPO, rel)
        data = open(path, 'rb').read()
        matches = list(pat.finditer(data))
        if not matches:
            print('[skip] %s: no match for %s' % (rel, pat.pattern.decode('utf-8', 'replace')))
            continue
        if len(matches) != 1:
            print('ABORT: %s: pattern matched %d times, expected 1' % (rel, len(matches))); sys.exit(1)
        m = matches[0]
        # 在该行行尾加标记（如果还没标记）
        line_end = data.find(b'\n', m.start())
        if line_end < 0:
            print('ABORT: %s: no newline after match' % rel); sys.exit(1)
        line = data[data.rfind(b'\n', 0, m.start()) + 1:line_end]
        if MARKER in line:
            print('[skip] %s: already patched' % rel)
            continue
        # 替换匹配体 + 在行尾插入标记
        new_data = (data[:m.start()] + rep(m) + data[m.end():line_end] +
                    b' ' + MARKER + data[line_end:])
        results.append((rel, data, new_data, m.start()))
    if not results:
        print('nothing to do.')
        return
    for rel, old, new, pos in results:
        new_lines = new.splitlines(keepends=True)
        start = old[:pos].count(b'\n')
        print('=== %s (line %d) ===' % (rel, start + 1))
        for i in range(max(0, start - 1), min(len(new_lines), start + 2)):
            mark = '>>>' if MARKER in new_lines[i] else '   '
            print('%s %4d  %s' % (mark, i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    rels = [r[0] for r in results]
    if not git_clean(rels):
        print('ABORT: 有文件在 git 里不干净'); sys.exit(1)
    for rel, old, new, pos in results:
        open(os.path.join(REPO, rel), 'wb').write(new)
        print('    written: %s' % rel)

if __name__ == '__main__':
    main()
