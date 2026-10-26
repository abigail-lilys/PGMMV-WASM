#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_rendertexture_ptr_bool.py — 第 1 类：RenderTextureCtrl* 与 bool 比较 -> == nullptr。

变量名已核实：renderTexture / renderTextureCtrl / withMenuRenderTextureCtrl 都是
getRenderTexture()/getWithMenuRenderTexture() 的返回值（指针）。
不碰 isCreate == false / bRemove == false / isDisableLimitCamera() == false 等 bool 返回值。

匹配到几处就替换几处（Scene.cpp 约 19 处、RenderTexture.cpp 2 处、ObjectCommand.cpp 3 处）。

用法：
  python3 patch_rendertexture_ptr_bool.py            # dry-run
  python3 patch_rendertexture_ptr_bool.py --apply    # 写入（要求所有目标文件在 git 里干净）
幂等：已有 "// [wasm-port] ptr-null" 标记的行跳过。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
MARKER = b'// [wasm-port] ptr-null'

PAT = re.compile(rb'if \((renderTexture|renderTextureCtrl|withMenuRenderTextureCtrl) == false\)')

FILES = [
    'Player/Classes/Lib/Scene.cpp',
    'Player/Classes/Lib/RenderTexture.cpp',
    'Player/Classes/Lib/ObjectCommand.cpp',
]

def git_clean(paths):
    r = subprocess.run(['git', 'status', '--porcelain', '--'] + paths, cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.returncode == 0 and r.stdout.strip() == b''

def main():
    results = []
    for rel in FILES:
        path = os.path.join(REPO, rel)
        data = open(path, 'rb').read()
        matches = list(PAT.finditer(data))
        if not matches:
            print('[skip] %s: no match' % rel)
            continue
        new = data
        for m in reversed(matches):
            line_end = new.find(b'\n', m.start())
            if line_end < 0:
                line_end = len(new)
            line_start = new.rfind(b'\n', 0, m.start()) + 1
            line = new[line_start:line_end]
            if MARKER in line:
                continue
            rep = b'if (' + m.group(1) + b' == nullptr)'
            new = new[:m.start()] + rep + new[m.end():line_end] + b' ' + MARKER + new[line_end:]
        results.append((rel, data, new, len(matches)))
    if not results:
        print('nothing to do.')
        return
    for rel, old, new, n in results:
        print('=== %s: %d match(es) ===' % (rel, n))
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        for i, (a, b) in enumerate(zip(old_lines, new_lines)):
            if a != b:
                print('>>> %4d  %s' % (i + 1, b.decode('utf-8', 'replace').rstrip('\r\n')))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    rels = [r[0] for r in results]
    if not git_clean(rels):
        print('ABORT: 有文件在 git 里不干净'); sys.exit(1)
    for rel, old, new, n in results:
        open(os.path.join(REPO, rel), 'wb').write(new)
        print('    written: %s' % rel)

if __name__ == '__main__':
    main()
