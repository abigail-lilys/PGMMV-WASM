#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_playdata_addmember.py — PlayData.cpp 里 AddMember 的第一个参数从
rapidjson::Value("KEY", allocator) 改成字符串字面量 "KEY"。

原因：cocos2d-x 自带的 rapidjson 版本里
  AddMember(GenericValue& name, T value, Allocator&)
需要 name 是左值；AddMember(rapidjson::Value("k", allocator), ...) 传的是临时对象。
但 document.h:1328 有
  AddMember(StringRefType name, T value, Allocator&)
模板重载，直接传 "k" 就能匹配（ProjectData.cpp:1524 的 AddMember("system", ...) 一直是这个写法且未报错）。
所以把第一个参数从 rapidjson::Value("k", allocator) 换成 "k"，不需要引入局部变量。

用法：
  python3 patch_playdata_addmember.py            # dry-run
  python3 patch_playdata_addmember.py --apply    # 写入（要求文件在 git 里干净）
幂等：替换后文件里不再有 AddMember(rapidjson::Value("...", allocator)，有就说明已打过或本来就没有。
保留行尾与字节（含日文注释的 cp932/UTF-8 编码）。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Data/PlayData.cpp'

# 只匹配 AddMember( 后紧跟 rapidjson::Value("...", allocator) 的形式，
# 允许空白、跨行空白（\s）。
PAT = re.compile(
    rb'(AddMember\(\s*)rapidjson::Value\(\s*"([^"]+)"\s*,\s*allocator\s*\)',
    re.M)

def git_clean(path):
    r = subprocess.run(['git', 'status', '--porcelain', '--', path], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    path = os.path.join(REPO, REL)
    data = open(path, 'rb').read()
    matches = list(PAT.finditer(data))
    if not matches:
        print('[skip] %s: no AddMember(rapidjson::Value(...)) left' % REL)
        return
    print('%s: %d occurrence(s) matched' % (REL, len(matches)))
    # 逐个打印上下文（按行号）
    line_starts = [0]
    for i, b in enumerate(data):
        if b == 0x0A:
            line_starts.append(i + 1)
    def lineno(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1
    for m in matches:
        n = lineno(m.start())
        # 打印该行全文
        ls = line_starts[n - 1]
        le = data.find(b'\n', ls)
        line = data[ls:le if le >= 0 else len(data)].decode('utf-8', 'replace').rstrip('\r\n')
        print('  L%d  %s' % (n, line))
    # 替换
    new = PAT.sub(lambda m: m.group(1) + b'"' + m.group(2) + b'"', data)
    # 二次确认：所有匹配都被替换（防止 lambda 里 group 拼接出错）
    if PAT.search(new) is not None:
        print('ABORT: replacement did not consume all matches')
        sys.exit(1)
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
