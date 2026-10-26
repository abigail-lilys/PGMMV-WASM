#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_macros_va_args.py — 把 Macros.h 里 ", __VA_ARGS__" 改成 ", ##__VA_ARGS__"。

原因：MSVC 的预处理器在 __VA_ARGS__ 为空时会吞掉前面的逗号（非标准扩展），
clang 不会；AGTK_ACTION_LOG(1, "x") 这类两参数调用在 clang 上展开成
GameManager::actionLog(1, "x", ); 尾部逗号 → expected expression。
##__VA_ARGS__ 是 GNU 扩展，clang 支持，空参数时同样吞逗号。
第 66 行 PreviewError 已经是 ", ##__VA_ARGS__"，不动。

用法：
  python3 patch_macros_va_args.py            # dry-run
  python3 patch_macros_va_args.py --apply    # 写入（要求文件在 git 里干净）
幂等：文件里不再有 ", __VA_ARGS__"（不带 ##）就跳过。
保留行尾（LF/CRLF）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Lib/Macros.h'
PAT = re.compile(rb'(?<!##), __VA_ARGS__')

def git_clean(path):
    r = subprocess.run(['git', 'status', '--porcelain', '--', path], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    path = os.path.join(REPO, REL)
    data = open(path, 'rb').read()
    if PAT.search(data) is None:
        print('[skip] %s: no ", __VA_ARGS__" left' % REL)
        return
    new = PAT.sub(rb', ##__VA_ARGS__', data)
    old_lines = data.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
    print('=== %s: %d line(s) changed ===' % (REL, len(changed)))
    for i in changed:
        print('>>> %4d  %s' % (i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
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
