#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_gamescene_ccimgui.py — GameScene::debugInit 里用 CCIMGUI / ImGuiLayer 的那一段
包进 #if (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32) || (CC_TARGET_PLATFORM == CC_PLATFORM_MAC)。

原因：
  - GameScene.cpp:18 的 #if 只在 WIN32/MAC 下 include ImGUI/CCIMGUI.h 与 ImGuiLayer.h；
  - CCIMGUI.cpp / ImGuiLayer.cpp 不在 Emscripten 构建里（CMakeLists.txt:168 只是 include 目录）；
  - debugInit 的唯一调用点（307 行）已被注释；debugDraw 只被 3482 行的 lambda 调用。
所以把这 12 行包掉，Emscripten 上既不报 CCIMGUI/ImGuiLayer 未声明，也不会在链接期缺符号。

保留 debugInit 的其它部分（ImFontConfig / ImGui::GetIO / io.Fonts->Build / _bShowFrameRate）。

用法：
  python3 patch_gamescene_ccimgui.py            # dry-run
  python3 patch_gamescene_ccimgui.py --apply    # 写入（要求文件在 git 里干净）
幂等：插入行带 "// [wasm-port] imgui win-only" 标记；有标记就跳过。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/GameScene.cpp'
MARKER = b'// [wasm-port] imgui win-only'

# 匹配 3481-3492：
#   CCIMGUI::getInstance()->addImGUI([&]() {
#       this->debugDraw();
#   }, "DebugWindowId");
#   (空行)
#   cocos2d::Director::getInstance()->getScheduler()->schedule([&](float delta)
#   {
#       ...
#   }, this, 0, false, "checkImGUI");
# 用非贪婪 .*? 跨行匹配到 "checkImGUI"); 为止。
PAT = re.compile(
    rb'(^([ \t]*)CCIMGUI::getInstance\(\)->addImGUI\(\[\&\]\(\) \{\r?\n'
    rb'.*?'
    rb'^[ \t]*\}, this, 0, false, "checkImGUI"\);\r?\n)',
    re.M | re.S)

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
    block = m.group(1)
    if block.count(b'"checkImGUI"') != 1:
        print('ABORT: matched block does not end at the expected line'); sys.exit(1)
    # 检测行尾：块内第一行的行尾
    eol = b'\r\n' if block.endswith(b'\r\n') else b'\n'
    indent = m.group(2)
    rep = (indent + b'#if (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32) || (CC_TARGET_PLATFORM == CC_PLATFORM_MAC) ' + MARKER + eol +
           block +
           indent + b'#endif ' + MARKER + eol)
    new = data[:m.start()] + rep + data[m.end():]
    # 打印改动区域
    new_lines = new.splitlines(keepends=True)
    start = data[:m.start()].count(b'\n')
    end = start + rep.count(b'\n')
    print('=== %s (lines %d-%d) ===' % (REL, start + 1, end))
    for i in range(max(0, start - 1), min(len(new_lines), end + 2)):
        line = new_lines[i]
        mark = '>>>' if MARKER in line else '   '
        print('%s %4d  %s' % (mark, i + 1, line.decode('utf-8', 'replace').rstrip('\r\n')))
    if not APPLY:
        print('(dry-run; 加 --apply 才会写文件)')
        return
    if not git_clean(REL):
        print('ABORT: %s 在 git 里不干净' % REL); sys.exit(1)
    open(path, 'wb').write(new)
    print('    written: %s' % REL)

if __name__ == '__main__':
    main()
