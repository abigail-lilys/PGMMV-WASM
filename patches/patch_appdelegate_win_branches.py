#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_appdelegate_win_branches.py — AppDelegate.cpp 的 Windows 专用分支在 Emscripten 上不可编译。

4 处改动：
  A) 311 行 getWebSocketPortAndProjectPathAndLocale(...) 调用包进 #if WIN32
     （函数定义本身在 #if WIN32 里；Emscripten 保持 port/projectFilePath/editorLocale 默认值，
      浏览器传入路径的方案以后单独做）
  B) USE_RUNTIME 块里的 "#if NX / #else" 改成 "#elif WIN32"（#else 里是 CommandLineToArgvW/HLOCAL）
  C) 335 行 getAppInfo(); 调用包进 #if WIN32（函数定义在 #if WIN32 里）
  D) gm->getSystem()->getAppName() 改成 gm->getAppName()
     （ProjectData::getSystem() 返回 bool；GameManager::getAppName() 在 272 行已使用）

用法：
  python3 patch_appdelegate_win_branches.py            # dry-run
  python3 patch_appdelegate_win_branches.py --apply    # 写入（要求文件在 git 里干净）
幂等：插入行带 "// [wasm-port] win-only" 标记；有标记就跳过对应改动。
保留行尾（本文件混合 LF/CRLF 时按每处原文）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/AppDelegate.cpp'
MARKER = b'// [wasm-port] win-only'

A_PAT = re.compile(
    rb'^([ \t]*)getWebSocketPortAndProjectPathAndLocale\(&port, &projectFilePath, &editorLocale, &logNumber, &autoTestFilePath\);(\r?\n)',
    re.M)

B_PAT = re.compile(
    rb'(#ifdef USE_RUNTIME(\r?\n)'
    rb'// #AGTK-NX\2'
    rb'#if \(CC_TARGET_PLATFORM == CC_PLATFORM_NX\)\2)'
    rb'#else(\r?\n)',
    re.M)

C_PAT = re.compile(rb'^([ \t]*)getAppInfo\(\);(\r?\n)', re.M)

D_PAT = re.compile(rb'gm->getSystem\(\)->getAppName\(\)')

def git_clean(path):
    r = subprocess.run(['git', 'status', '--porcelain', '--', path], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def apply_all(data):
    # A
    m = A_PAT.search(data)
    if m is None:
        print('ABORT: pattern A not found'); sys.exit(1)
    eol = m.group(2)
    rep = (b'#if (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32) ' + MARKER + eol +
           m.group(1) + b'getWebSocketPortAndProjectPathAndLocale(&port, &projectFilePath, &editorLocale, &logNumber, &autoTestFilePath);' + eol +
           b'#endif ' + MARKER + eol)
    data = data[:m.start()] + rep + data[m.end():]
    # B
    m = B_PAT.search(data)
    if m is None:
        print('ABORT: pattern B not found'); sys.exit(1)
    eol = m.group(2)
    rep = m.group(1) + b'#elif (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32) ' + MARKER + eol
    data = data[:m.start()] + rep + data[m.end():]
    # C
    m = C_PAT.search(data)
    if m is None:
        print('ABORT: pattern C not found'); sys.exit(1)
    eol = m.group(2)
    rep = (b'#if (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32) ' + MARKER + eol +
           m.group(1) + b'getAppInfo();' + eol +
           b'#endif ' + MARKER + eol)
    data = data[:m.start()] + rep + data[m.end():]
    # D
    n = len(D_PAT.findall(data))
    if n == 0:
        print('ABORT: pattern D not found'); sys.exit(1)
    data = D_PAT.sub(b'gm->getAppName()', data)
    print('  D: %d occurrence(s) replaced' % n)
    return data

def main():
    path = os.path.join(REPO, REL)
    data = open(path, 'rb').read()
    if MARKER in data:
        print('[skip] %s: already patched' % REL)
        return
    new = apply_all(data)
    new_lines = new.splitlines(keepends=True)
    print('=== %s ===' % REL)
    for i, line in enumerate(new_lines):
        if MARKER in line:
            lo = max(0, i - 1); hi = min(len(new_lines), i + 2)
            for j in range(lo, hi):
                mark = '>>>' if j == i else '   '
                print('%s %4d  %s' % (mark, j + 1, new_lines[j].decode('utf-8', 'replace').rstrip('\r\n')))
            print('')
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
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
