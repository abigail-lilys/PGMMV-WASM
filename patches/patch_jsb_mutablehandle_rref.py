#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_jsb_mutablehandle_rref.py — 把 Jsb 文件里的 "auto &X = args[N];" 改成 "auto &&X = args[N];"。

原因：JS::CallArgs::operator[] 返回 JS::MutableHandleValue 临时对象；
"auto &X = args[N]" 用非 const 左值引用绑定临时对象，clang 拒绝（MSVC 放行）。
"auto &&X = args[N]" 绑定右值并把生命周期延长到 X 的作用域结束，
X 仍指向 argv_[N]，作为表达式是左值，传给 getInt32(JS::MutableHandleValue&) 等形参合法。

用法：
  python3 patch_jsb_mutablehandle_rref.py            # dry-run
  python3 patch_jsb_mutablehandle_rref.py --apply    # 写入（要求所有目标文件在 git 里干净）
幂等：文件里不再有 "auto &...= args[" 就跳过。
保留行尾。
"""
import os, re, subprocess, sys, glob

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
GLOB = 'Player/Classes/Lib/Jsb/*.cpp'

PAT = re.compile(rb'\bauto &([A-Za-z_][A-Za-z0-9_]*) = args\[(\d+)\];')

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    paths = sorted(glob.glob(os.path.join(REPO, GLOB)))
    if not paths:
        print('no files matched'); sys.exit(1)
    rels = [os.path.relpath(p, REPO) for p in paths]
    results = []
    total = 0
    for p, rel in zip(paths, rels):
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
        for i in changed[:5]:
            print('>>> %4d  %s' % (i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
        if len(changed) > 5:
            print('    ... (%d more)' % (len(changed) - 5))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    if not git_clean(rels):
        print('ABORT: 有文件在 git 里不干净'); sys.exit(1)
    for rel, old, new in results:
        open(os.path.join(REPO, rel), 'wb').write(new)
        print('    written: %s' % rel)

if __name__ == '__main__':
    main()
