#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_bulletmanager_fwd_decl.py — 把 BulletManager.h 里带命名空间限定的前向声明
"class agtk::Bullet;" 改成 "namespace agtk { class Bullet; }"。

原因：clang 拒绝 "forward declaration of class cannot have a nested name specifier"。
该行在 NS_AGTK_END 之后的全局作用域，用 namespace 块等价且合法；
保留外层 #if CC_TARGET_PLATFORM != CC_PLATFORM_NX。

用法：
  python3 patch_bulletmanager_fwd_decl.py            # dry-run
  python3 patch_bulletmanager_fwd_decl.py --apply    # 写入（要求文件在 git 里干净）
幂等：改后行尾带标记 "// [wasm-port] nested-fwd-decl"；保留行尾（CRLF/LF）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Manager/BulletManager.h'
PAT = re.compile(rb'^([ \t]*)class agtk::Bullet;[ \t]*(\r?\n)', re.M)
REP = rb'\1namespace agtk { class Bullet; } // [wasm-port] nested-fwd-decl\2'
MARKER = b'// [wasm-port] nested-fwd-decl'

def git_clean(path):
    r = subprocess.run(['git', 'status', '--porcelain', '--', path], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    path = os.path.join(REPO, REL)
    data = open(path, 'rb').read()
    if MARKER in data:
        print('[skip] %s: already patched' % REL)
        return
    new, n = PAT.subn(REP, data)
    if n != 1:
        print('ABORT: pattern matched %d times, expected 1' % n)
        sys.exit(1)
    old_lines = data.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    idx = next(i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b)
    print('=== %s (change at line %d) ===' % (REL, idx + 1))
    lo = max(0, idx - 2); hi = min(len(new_lines), idx + 3)
    for i in range(lo, hi):
        mark = '>>>' if i == idx else '   '
        print('%s %4d  %s' % (mark, i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
    if not APPLY:
        print('\n(dry-run; 加 --apply 才会写文件)')
        return
    if not git_clean(REL):
        print('ABORT: %s 在 git 里不干净：' % REL)
        print(subprocess.run(['git', 'status', '--short', '--', REL], cwd=REPO,
                             stdout=subprocess.PIPE).stdout.decode('utf-8', 'replace'))
        sys.exit(1)
    open(path, 'wb').write(new)
    print('    written: %s' % REL)

if __name__ == '__main__':
    main()
