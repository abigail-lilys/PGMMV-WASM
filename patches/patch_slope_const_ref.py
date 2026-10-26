#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_slope_const_ref.py — 把 Slope::checkUpSide 的形参从 Vec2& 改成 const Vec2&。

原因：Slope.h:59 的内联重载 checkUpSide(float,float) 调用 checkUpSide(cocos2d::Vec2(x,y))，
临时对象不能绑定到非 const 左值引用；clang 拒绝，MSVC 放行。Slope.cpp:1858 的实现只读
targetPos（targetPos - _worldStartPoint），不修改它，所以改成 const Vec2& 语义不变，
一次性解决 67 个 TU 的 Slope.h:59 根因，以及 Slope.cpp 里 11 处传临时对象的调用点。

用法：
  python3 patch_slope_const_ref.py            # dry-run，只打印
  python3 patch_slope_const_ref.py --apply    # 写入（要求两个目标文件在 git 里干净）

幂等：目标行尾会加标记 "// [wasm-port] const-ref"；脚本看到标记就跳过。
保留行尾（LF/CRLF）与文件字节（含日文注释的编码）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
FILES = {
    'Player/Classes/Lib/Slope.h': [
        (re.compile(rb'^([ \t]*)bool checkUpSide\(Vec2& targetPos\);[ \t]*(\r?\n)', re.M),
         rb'\1bool checkUpSide(const Vec2& targetPos); // [wasm-port] const-ref\2'),
    ],
    'Player/Classes/Lib/Slope.cpp': [
        (re.compile(rb'^([ \t]*)bool Slope::checkUpSide\(Vec2& targetPos\)[ \t]*(\r?\n)', re.M),
         rb'\1bool Slope::checkUpSide(const Vec2& targetPos) // [wasm-port] const-ref\2'),
    ],
}
MARKER = b'// [wasm-port] const-ref'

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    if APPLY and not git_clean(list(FILES)):
        print('ABORT: 目标文件在 git 里不干净：')
        print(subprocess.run(['git', 'status', '--short', '--'] + list(FILES), cwd=REPO,
                             stdout=subprocess.PIPE).stdout.decode('utf-8', 'replace'))
        sys.exit(1)
    changed = []
    for rel, subs in FILES.items():
        path = os.path.join(REPO, rel)
        data = open(path, 'rb').read()
        if MARKER in data:
            print('[skip] %s: already patched (marker found)' % rel)
            continue
        new = data
        hit = False
        for pat, rep in subs:
            new2, n = pat.subn(rep, new)
            if n == 1:
                new = new2
                hit = True
            elif n > 1:
                print('ABORT: %s: pattern matched %d times, expected 1' % (rel, n))
                sys.exit(1)
        if not hit:
            print('ABORT: %s: target line not found (pattern did not match)' % rel)
            sys.exit(1)
        changed.append((rel, data, new))
    if not changed:
        print('nothing to do.')
        return
    for rel, old, new in changed:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        idx = next(i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b)
        print('=== %s (first change at line %d) ===' % (rel, idx + 1))
        lo = max(0, idx - 1); hi = min(len(new_lines), idx + 2)
        for i in range(lo, hi):
            mark = '>>>' if i == idx else '   '
            print('%s %4d  %s' % (mark, i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
        if APPLY:
            open(os.path.join(REPO, rel), 'wb').write(new)
            print('    written: %s' % rel)
    if not APPLY:
        print('\n(dry-run; 加 --apply 才会写文件)')

if __name__ == '__main__':
    main()
