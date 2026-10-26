#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_common_utf8tosjis.py — Common.cpp 的 UTF8toSjis 在 Emscripten 上直通返回 UTF-8。

原因：唯一调用点 GameManager.cpp:6517 把结果写日志文件，浏览器/虚拟文件系统全 UTF-8，
没有“活动代码页”概念，MultiByteToWideChar(CP_UTF8)/WideCharToMultiByte(CP_THREAD_ACP)
在 Emscripten 上不可用。

原代码是 "#if NX / #else"，NX 分支为空（返回空串）。不能改成 "#if NX || EMSCRIPTEN"
（会改变 NX 行为），改为 "#if EMSCRIPTEN / #elif NX / #else"。

用法：
  python3 patch_common_utf8tosjis.py            # dry-run
  python3 patch_common_utf8tosjis.py --apply    # 写入（要求文件在 git 里干净）
幂等：插入行带 "// [wasm-port] emscripten utf8" 标记；有标记就跳过。
保留行尾（本文件行尾按原文捕获）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Lib/Common.cpp'
MARKER = b'// [wasm-port] emscripten utf8'

PAT = re.compile(
    rb'(std::string UTF8toSjis\(std::string srcUTF8\)\s*\{\s*\r?\n'
    rb'// #AGTK-NX\r?\n)'
    rb'#if \(CC_TARGET_PLATFORM == CC_PLATFORM_NX\)(\r?\n)',
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
    eol = m.group(2)
    rep = (m.group(1) +
           b'#if (CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN) ' + MARKER + eol +
           b'        return srcUTF8;' + eol +
           b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_NX)' + eol)
    new = data[:m.start()] + rep + data[m.end():]
    new_lines = new.splitlines(keepends=True)
    print('=== %s ===' % REL)
    for i, line in enumerate(new_lines):
        if MARKER in line:
            lo = max(0, i - 2); hi = min(len(new_lines), i + 4)
            for j in range(lo, hi):
                mark = '>>>' if j == i else '   '
                print('%s %4d  %s' % (mark, j + 1, new_lines[j].decode('utf-8', 'replace').rstrip('\r\n')))
            break
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    if not git_clean(REL):
        print('ABORT: %s 在 git 里不干净' % REL); sys.exit(1)
    open(path, 'wb').write(new)
    print('    written: %s' % REL)

if __name__ == '__main__':
    main()
