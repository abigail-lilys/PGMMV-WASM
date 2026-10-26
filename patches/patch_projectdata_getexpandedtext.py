#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_projectdata_getexpandedtext.py — 给 ProjectData 加 getExpandedText 的右值引用重载。

原因：Gui.cpp 有 7 处调用传 std::list<int>(1, textId) 临时对象给
  std::string getExpandedText(const char*, const std::string&, std::list<int>&);
定义体里 textIdList.push_back(...) 会修改它，所以不能改成 const&。
加一个右值引用重载：临时对象绑定到 &&，函数体内以左值传给原函数，
语义不变（同一个 list 对象，去重集合不变，递归调用走原重载）。

用法：
  python3 patch_projectdata_getexpandedtext.py            # dry-run
  python3 patch_projectdata_getexpandedtext.py --apply    # 写入（要求文件在 git 里干净）
幂等：插入行带 "// [wasm-port] rvalue overload" 标记；有标记就跳过。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Data/ProjectData.h'
MARKER = b'// [wasm-port] rvalue overload'

PAT = re.compile(
    rb'(^([ \t]*)std::string getExpandedText\(const char \*locale, const std::string &text, std::list<int> &textIdList\);)(\r?\n)',
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
    eol = m.group(3)
    indent = m.group(2)
    rep = (m.group(1) + eol +
           indent + b'std::string getExpandedText(const char *locale, const std::string &text, std::list<int> &&textIdList) ' + MARKER + eol +
           indent + b'{' + eol +
           indent + b'    return getExpandedText(locale, text, textIdList);' + eol +
           indent + b'}' + eol)
    new = data[:m.start()] + rep + data[m.end():]
    new_lines = new.splitlines(keepends=True)
    print('=== %s ===' % REL)
    for i, line in enumerate(new_lines):
        if MARKER in line:
            lo = max(0, i - 1); hi = min(len(new_lines), i + 5)
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
