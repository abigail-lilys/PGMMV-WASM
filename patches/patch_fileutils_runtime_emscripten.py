#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_fileutils_runtime_emscripten.py — FileUtilsRuntime 在 Emscripten 上继承 FileUtilsEmscripten。

改动 4 处：
  FileUtils-runtime.h:
    1) include 区：WIN32 的 #include 之后加 #elif EMSCRIPTEN 包含 platform/emscripten/CCFileUtils-emscripten.h
    2) 类声明：WIN32 的 "public FileUtilsWin32" 之后加 #elif EMSCRIPTEN "public FileUtilsEmscripten"
  FileUtils-runtime.cpp:
    3) getContents 第一处 #if WIN32 ... #elif NX 加 EMSCRIPTEN 分支 return FileUtils::getContents(...)
    4) getContents 第二处 #if WIN32 ... #elif NX 加 EMSCRIPTEN 分支 auto status = FileUtils::getContents(...)

用法：
  python3 patch_fileutils_runtime_emscripten.py            # dry-run
  python3 patch_fileutils_runtime_emscripten.py --apply    # 写入（要求两个文件在 git 里干净）
幂等：每个插入行尾带 "// [wasm-port] emscripten FileUtils"；文件里出现该标记就跳过。
保留行尾（LF/CRLF）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
MARKER = b'// [wasm-port] emscripten FileUtils'

def nl_of(data):
    return b'\r\n' if b'\r\n' in data else b'\n'

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

H = 'Player/Classes/Lib/Runtime/FileUtils-runtime.h'
C = 'Player/Classes/Lib/Runtime/FileUtils-runtime.cpp'

H_INC_PAT = re.compile(
    rb'#if CC_TARGET_PLATFORM == CC_PLATFORM_WIN32\r?\n'
    rb'#include "platform/win32/CCFileUtils-win32\.h"\r?\n'
    rb'// #AGTK-NX\r?\n'
    rb'#elif \(CC_TARGET_PLATFORM == CC_PLATFORM_NX\)\r?\n'
    rb'#endif\r?\n'
)
def h_inc_rep(nl):
    return (b'#if CC_TARGET_PLATFORM == CC_PLATFORM_WIN32' + nl +
            b'#include "platform/win32/CCFileUtils-win32.h"' + nl +
            b'#elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN ' + MARKER + nl +
            b'#include "platform/emscripten/CCFileUtils-emscripten.h"' + nl +
            b'// #AGTK-NX' + nl +
            b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_NX)' + nl +
            b'#endif' + nl)

H_CLS_PAT = re.compile(
    rb'#if \(CC_TARGET_PLATFORM == CC_PLATFORM_WIN32\)\r?\n'
    rb'class FileUtilsRuntime : public FileUtilsWin32//FileUtils\r?\n'
    rb'// #AGTK-NX\r?\n'
    rb'#elif \(CC_TARGET_PLATFORM == CC_PLATFORM_NX\)\r?\n'
    rb'#endif\r?\n'
    rb'\{\r?\n'
)
def h_cls_rep(nl):
    return (b'#if (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32)' + nl +
            b'class FileUtilsRuntime : public FileUtilsWin32//FileUtils' + nl +
            b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN) ' + MARKER + nl +
            b'class FileUtilsRuntime : public FileUtilsEmscripten' + nl +
            b'// #AGTK-NX' + nl +
            b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_NX)' + nl +
            b'#endif' + nl +
            b'{' + nl)

C_GET1_PAT = re.compile(
    rb'(#if \(CC_TARGET_PLATFORM == CC_PLATFORM_WIN32\)\r?\n'
    rb'([ \t]*)return FileUtilsWin32::getContents\(filename, buffer\);\r?\n)'
    rb'#elif \(CC_TARGET_PLATFORM == CC_PLATFORM_NX\)\r?\n'
    rb'#endif\r?\n'
)
def c_get1_rep(m, nl):
    return (m.group(1) +
            b'#elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN ' + MARKER + nl +
            m.group(2) + b'return FileUtils::getContents(filename, buffer);' + nl +
            b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_NX)' + nl +
            b'#endif' + nl)

C_GET2_PAT = re.compile(
    rb'(#if \(CC_TARGET_PLATFORM == CC_PLATFORM_WIN32\)\r?\n'
    rb'([ \t]*)auto status = FileUtilsWin32::getContents\(filename, &buf\);\r?\n)'
    rb'#elif \(CC_TARGET_PLATFORM == CC_PLATFORM_NX\)\r?\n'
    rb'#endif\r?\n'
)
def c_get2_rep(m, nl):
    return (m.group(1) +
            b'#elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN ' + MARKER + nl +
            m.group(2) + b'auto status = FileUtils::getContents(filename, &buf);' + nl +
            b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_NX)' + nl +
            b'#endif' + nl)

def apply_subs(rel, subs):
    path = os.path.join(REPO, rel)
    data = open(path, 'rb').read()
    if MARKER in data:
        print('[skip] %s: already patched' % rel)
        return None
    nl = nl_of(data)
    new = data
    for pat, rep_fn in subs:
        m = pat.search(new)
        if m is None:
            print('ABORT: %s: pattern not found:' % rel)
            print(pat.pattern.decode('utf-8', 'replace'))
            sys.exit(1)
        rep = rep_fn(m, nl)
        new = new[:m.start()] + rep + new[m.end():]
    return data, new

def main():
    targets = [
        (H, [(H_INC_PAT, lambda m, nl: h_inc_rep(nl)),
             (H_CLS_PAT, lambda m, nl: h_cls_rep(nl))]),
        (C, [(C_GET1_PAT, c_get1_rep),
             (C_GET2_PAT, c_get2_rep)]),
    ]
    if APPLY and not git_clean([H, C]):
        print('ABORT: 目标文件在 git 里不干净：')
        print(subprocess.run(['git', 'status', '--short', '--', H, C], cwd=REPO,
                             stdout=subprocess.PIPE).stdout.decode('utf-8', 'replace'))
        sys.exit(1)
    results = []
    for rel, subs in targets:
        r = apply_subs(rel, subs)
        if r is not None:
            results.append((rel,) + r)
    if not results:
        print('nothing to do.')
        return
    for rel, old, new in results:
        new_lines = new.splitlines(keepends=True)
        print('=== %s ===' % rel)
        for i, line in enumerate(new_lines):
            if MARKER in line:
                lo = max(0, i - 2); hi = min(len(new_lines), i + 3)
                for j in range(lo, hi):
                    mark = '>>>' if j == i else '   '
                    print('%s %4d  %s' % (mark, j + 1, new_lines[j].decode('utf-8', 'replace').rstrip('\r\n')))
                print('')
        if APPLY:
            open(os.path.join(REPO, rel), 'wb').write(new)
            print('    written: %s' % rel)
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')

if __name__ == '__main__':
    main()
