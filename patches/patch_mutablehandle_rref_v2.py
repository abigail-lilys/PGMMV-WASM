#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_mutablehandle_rref_v2.py — 扩展 patch_jsb_mutablehandle_rref.py 到 JavascriptManager.cpp。

原因：JavascriptManager.cpp 的 20 条 non-const lvalue reference 与 Jsb 文件同模式
（auto &v = args[N]; / auto &v2 = args[N];），但它在 Classes/Manager/ 下，
第一个脚本的 glob 只覆盖 Classes/Lib/Jsb/*.cpp，所以没被修。

对已打过补丁的 Lib/Jsb/*.cpp 是 no-op（没有 auto &...= args[ 就跳过）。

用法：
  python3 patch_mutablehandle_rref_v2.py            # dry-run
  python3 patch_mutablehandle_rref_v2.py --apply    # 写入（要求目标文件在 git 里干净）
幂等：文件里不再有 "auto &...= args[" 就跳过。
保留行尾。
"""
import os, re, subprocess, sys, glob

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
GLOBS = [
    'Player/Classes/Lib/Jsb/*.cpp',
    'Player/Classes/Manager/JavascriptManager.cpp',
]

PAT = re.compile(rb'\bauto &([A-Za-z_][A-Za-z0-9_]*) = args\[(\d+)\];')

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    paths = []
    for g in GLOBS:
        paths.extend(sorted(glob.glob(os.path.join(REPO, g))))
    if not paths:
        print('no files matched'); sys.exit(1)
    results = []
    total = 0
    for p in paths:
        rel = os.path.relpath(p, REPO)
        data = open(p, 'rb').read()
        matches = PAT.findall(data)
        if not matches:
            continue
        new = PAT.sub(lambda m: b'auto &&' + m.group(1) + b' = args[' + m.group(2) + b'];', data)
        if PAT.search(new) is not None:
            print('ABORT: %s: replacement did not consume all matches' % rel); sys.exit(1)
        total += len(matches)
        results.append((rel, data, new))
    if not results:
        print('nothing to do.')
        return
    print('total occurrences: %d in %d file(s)' % (total, len(results)))
    for rel, old, new in results:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
        print('=== %s: %d line(s) ===' % (rel, len(changed)))
        for i in changed[:8]:
            print('>>> %4d  %s' % (i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
        if len(changed) > 8:
            print('    ... (%d more)' % (len(changed) - 8))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    rels = [rel for rel, _, _ in results]
    if not git_clean(rels):
        print('ABORT: 有文件在 git 里不干净'); sys.exit(1)
    for rel, old, new in results:
        open(os.path.join(REPO, rel), 'wb').write(new)
        print('    written: %s' % rel)

if __name__ == '__main__':
    main()
