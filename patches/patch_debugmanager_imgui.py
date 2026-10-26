#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_debugmanager_imgui.py — DebugManager.cpp 的 ImGui 依赖在 Emscripten 上不可用。

4 处改动：
  A) initFont() 里 const ImWchar *glyphRanges = glyphRangesJapanese;
     → const ImWchar *glyphRanges = io.Fonts->GetGlyphRangesJapanese();
     （glyphRangesJapanese 来自被 #if (WIN32||MAC) 包住的 imgui_ja_gryph_ranges.cpp；
       标准 imgui.h 自带 GetGlyphRangesJapanese()）
  B) start() 里 CCIMGUI::getInstance()->addImGUI(...) 整段包 #if (WIN32||MAC)
  C) start() 里 static const char *scheduleName = ... 到 ... scheduleName); 整段包 #if (WIN32||MAC)
     （这段里用 ImGuiLayer::create()）
  D) end() 里 CCIMGUI::getInstance()->removeImGUI("DebugWindowId"); 包 #if (WIN32||MAC)

保留 scheduleUpdate / setLayer / _running 这些与 ImGui 无关的逻辑。

用法：
  python3 patch_debugmanager_imgui.py            # dry-run
  python3 patch_debugmanager_imgui.py --apply    # 写入（要求文件在 git 里干净）
幂等：插入行带 "// [wasm-port] imgui win-only" 标记；有标记就跳过。
保留行尾。
"""
import os, re, subprocess, sys

APPLY = '--apply' in sys.argv
REPO = os.path.expanduser('~/PGMMV-src')
REL = 'Player/Classes/Manager/DebugManager.cpp'
MARKER = b'// [wasm-port] imgui win-only'
GUARD = b'#if (CC_TARGET_PLATFORM == CC_PLATFORM_WIN32) || (CC_TARGET_PLATFORM == CC_PLATFORM_MAC) '

def guard_block(block, indent, eol):
    return (indent + GUARD + MARKER + eol +
            block +
            indent + b'#endif ' + MARKER + eol)

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
    new = data

    # A
    pat_a = re.compile(rb'const ImWchar \*glyphRanges = glyphRangesJapanese;')
    m = pat_a.search(new)
    if m is None:
        print('ABORT: A not found'); sys.exit(1)
    new = new[:m.start()] + b'const ImWchar *glyphRanges = io.Fonts->GetGlyphRangesJapanese(); ' + MARKER + new[m.end():]

    # B
    pat_b = re.compile(
        rb'(^([ \t]*)CCIMGUI::getInstance\(\)->addImGUI\(\[\&\]\(\) \{\r?\n'
        rb'[ \t]*this->draw\(\);\r?\n'
        rb'[ \t]*\}, "DebugWindowId"\);\r?\n)',
        re.M)
    m = pat_b.search(new)
    if m is None:
        print('ABORT: B not found'); sys.exit(1)
    eol = b'\r\n' if m.group(1).endswith(b'\r\n') else b'\n'
    new = new[:m.start()] + guard_block(m.group(1), m.group(2), eol) + new[m.end():]

    # C
    pat_c = re.compile(
        rb'(^([ \t]*)static const char \*scheduleName = "checkImGUI";\r?\n'
        rb'.*?'
        rb'^[ \t]*\}, this, 0, false, scheduleName\);\r?\n)',
        re.M | re.S)
    m = pat_c.search(new)
    if m is None:
        print('ABORT: C not found'); sys.exit(1)
    eol = b'\r\n' if m.group(1).endswith(b'\r\n') else b'\n'
    new = new[:m.start()] + guard_block(m.group(1), m.group(2), eol) + new[m.end():]

    # D
    pat_d = re.compile(rb'^([ \t]*)CCIMGUI::getInstance\(\)->removeImGUI\("DebugWindowId"\);(\r?\n)', re.M)
    m = pat_d.search(new)
    if m is None:
        print('ABORT: D not found'); sys.exit(1)
    block = m.group(1) + b'CCIMGUI::getInstance()->removeImGUI("DebugWindowId");' + m.group(2)
    new = new[:m.start()] + guard_block(block, m.group(1), m.group(2)) + new[m.end():]

    # 打印每处标记
    new_lines = new.splitlines(keepends=True)
    print('=== %s ===' % REL)
    for i, line in enumerate(new_lines):
        if MARKER in line:
            mark = '>>>' if GUARD in line or b'#endif' in line else '   '
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
