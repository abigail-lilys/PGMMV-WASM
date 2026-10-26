#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_collision_local_vec.py — Collision.cpp:2001 的 Vec2(0, 0) 临时对象改局部变量。

原因：USE_MULTITHREAD_OBJECT_UPDATE 下 newCheckWallHit 的形参是 Vec2& tileThresholdMoveVec，
调用点传 Vec2(0, 0) 临时对象，clang 拒绝（MSVC 放行）。函数体里该参数只读（fabsf(...x/.y)），
但改 const& 要动 4 个定义 + 8 个声明；改调用点为局部变量只动 1 行，Windows 行为不变。

用法：
  python3 patch_collision_local_vec.py            # dry-run
  python3 patch_collision_local_vec.py --apply    # 写入（要求文件在 git 里干净）
幂等：插入行带 "// [wasm-port] local vec" 标记；有标记就跳过。
只改多线程分支的那一行（#ifdef USE_MULTITHREAD_OBJECT_UPDATE 下的 2001），
非多线程分支的同类调用当前不编译，不动。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Lib/Collision.cpp'
MARKER = b'// [wasm-port] local vec'

# 匹配：
#   #ifdef USE_MULTITHREAD_OBJECT_UPDATE
#           agtk::MtVector<agtk::Slope *> slopeList;
#           newCheckWallHit(info, hitX, hitY, 0, tileList, &slopeList, nullptr, moveVec, Vec2(0, 0), objectRect, false, false, hitTiles);
PAT = re.compile(
    rb'(#ifdef USE_MULTITHREAD_OBJECT_UPDATE\r?\n'
    rb'[ \t]*agtk::MtVector<agtk::Slope \*> slopeList;\r?\n)'
    rb'([ \t]*)(newCheckWallHit\(info, hitX, hitY, 0, tileList, &slopeList, nullptr, moveVec, )Vec2\(0, 0\)'
    rb'(, objectRect, false, false, hitTiles\);\r?\n)',
    re.M)

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
    m = PAT.search(data)
    if m is None:
        print('ABORT: pattern not found'); sys.exit(1)
    rep = (m.group(1) +
           m.group(2) + b'Vec2 tileThresholdMoveVec(0, 0); ' + MARKER + b'\n' +
           m.group(2) + m.group(3) + b'tileThresholdMoveVec' + m.group(4))
    new = data[:m.start()] + rep + data[m.end():]
    # 打印改动区域
    new_lines = new.splitlines(keepends=True)
    start = data[:m.start()].count(b'\n')
    print('=== %s ===' % REL)
    for i in range(max(0, start - 1), min(len(new_lines), start + 6)):
        mark = '>>>' if MARKER in new_lines[i] else '   '
        print('%s %4d  %s' % (mark, i + 1, new_lines[i].decode('utf-8', 'replace').rstrip('\r\n')))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    if not git_clean(REL):
        print('ABORT: %s 在 git 里不干净' % REL); sys.exit(1)
    open(path, 'wb').write(new)
    print('    written: %s' % REL)

if __name__ == '__main__':
    main()
