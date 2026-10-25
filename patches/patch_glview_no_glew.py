#!/usr/bin/env python3
"""
platform/desktop/CCGLViewImpl-desktop.cpp : make the desktop GLFW view usable on Emscripten (WebGL).

  1. initGlew()                : skip GLEW on Emscripten (no GLEW; WebGL needs no extension loader)
       '#if (CC_TARGET_PLATFORM != CC_PLATFORM_MAC)'  (the one inside initGlew)
    -> '#if (CC_TARGET_PLATFORM != CC_PLATFORM_MAC) && (CC_TARGET_PLATFORM != CC_PLATFORM_EMSCRIPTEN)'
       (initGlew then just returns true; the matching #endif is unchanged)
  2. 'OpenGL 1.5 or higher' check : WebGL's GL_VERSION is "OpenGL ES 2.0 (WebGL ...)", atof() gives 0
       -> the check would fail and the window creation would return false. Skip it on Emscripten.
  3. GL_VERTEX_PROGRAM_POINT_SIZE / GL_MULTISAMPLE are desktop-only enums (INVALID_ENUM on WebGL);
       skip those two glEnable calls on Emscripten (WebGL: gl_PointSize always works, MSAA = context attribute).

Every inserted '#if' line ends with '// clang-fix' so the script is idempotent.
DRY-RUN by default. --apply writes. --root DIR (default ~/PGMMV-src/Player/cocos2d/cocos). --no-git-check for tests.
latin-1 byte-preserving (cp932 comments untouched), CRLF/LF kept, all checks before any write.
"""
import sys, os, subprocess, difflib

ROOT = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos')
args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])

REL = 'platform/desktop/CCGLViewImpl-desktop.cpp'
MARK = '// clang-fix'
NOT_EM = '#if (CC_TARGET_PLATFORM != CC_PLATFORM_EMSCRIPTEN) ' + MARK

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def patch(lines):
    if any(MARK in l for l in lines):
        return None
    e = eol(lines[0]) or '\n'
    new = list(lines)

    # ---- 1. initGlew guard
    fn = [i for i, l in enumerate(lines) if l.startswith('bool GLViewImpl::initGlew()')]
    if len(fn) != 1:
        raise PatchError("expected exactly one 'bool GLViewImpl::initGlew()', found %d" % len(fn))
    g = [i for i in range(fn[0], min(fn[0] + 6, len(lines)))
         if lines[i].strip() == '#if (CC_TARGET_PLATFORM != CC_PLATFORM_MAC)']
    if len(g) != 1:
        raise PatchError("expected the MAC guard right after initGlew(), found %d" % len(g))
    old_if = lines[g[0]]
    new[g[0]] = ('#if (CC_TARGET_PLATFORM != CC_PLATFORM_MAC) && (CC_TARGET_PLATFORM != CC_PLATFORM_EMSCRIPTEN) '
                 + MARK + eol(old_if))

    # ---- 2. GL version check block
    c = [i for i, l in enumerate(lines) if l.strip() == '// check OpenGL version at first']
    if len(c) != 1:
        raise PatchError("expected one '// check OpenGL version at first', found %d" % len(c))
    c = c[0]
    if 'glGetString(GL_VERSION)' not in lines[c + 1]:
        raise PatchError("line after the version comment is not glGetString(GL_VERSION)")
    end = None
    for j in range(c + 2, min(c + 20, len(lines))):
        if lines[j].rstrip('\r\n') == '    }' and 'return false;' in lines[j - 1]:
            end = j
            break
    if end is None:
        raise PatchError("could not find the end of the version-check block")

    # ---- 3. point size / multisample
    ps = [i for i, l in enumerate(lines) if l.strip() == 'glEnable(GL_VERTEX_PROGRAM_POINT_SIZE);']
    ms = [i for i, l in enumerate(lines) if l.strip() == 'glEnable(GL_MULTISAMPLE);']
    if len(ps) != 1 or len(ms) != 1:
        raise PatchError("expected one point-size and one multisample glEnable, found %d / %d" % (len(ps), len(ms)))
    ps, ms = ps[0], ms[0]
    if not (end < ps < ms):
        raise PatchError("unexpected order of the blocks")
    # the multisample glEnable is the body of an 'if' on the previous line: wrap BOTH lines,
    # otherwise the 'if' would swallow the next statement when the glEnable is compiled out.
    if lines[ms - 1].strip() != 'if(_glContextAttrs.multisamplingCount > 0)':
        raise PatchError("glEnable(GL_MULTISAMPLE) is not directly preceded by its 'if(...multisamplingCount > 0)'")

    # apply insertions from the bottom up so indices stay valid
    ins = [(ms + 1, '#endif' + e), (ms - 1, NOT_EM + e),
           (ps + 1, '#endif' + e), (ps, NOT_EM + e),
           (end + 1, '#endif' + e), (c, NOT_EM + e)]
    for idx, text in ins:
        new.insert(idx, text)
    return new

path = os.path.join(ROOT, REL)
if not os.path.isfile(path):
    print('ABORT - file not found:', path); sys.exit(1)
if GITCHECK:
    d, b = os.path.dirname(path), os.path.basename(path)
    r = subprocess.run(['git', '-C', d, 'ls-files', '--error-unmatch', b], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        print('ABORT - not tracked by git:', REL); sys.exit(1)
    r = subprocess.run(['git', '-C', d, 'status', '--porcelain', '--', b], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.stdout.strip():
        print('ABORT - uncommitted changes:', r.stdout.decode().strip()); sys.exit(1)

old = open(path, 'rb').read().decode('latin-1')
lines = old.splitlines(True)
try:
    nl = patch(lines)
except PatchError as ex:
    print('ABORT - nothing was written. Problem:', ex); sys.exit(1)
if nl is None:
    print('already patched, no change'); sys.exit(0)
new = ''.join(nl)

print('== ' + REL)
diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + REL, 'b/' + REL, n=1)
out = ''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', '')
sys.stdout.write(out.encode('ascii', 'replace').decode('ascii'))
if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.'); sys.exit(0)
open(path, 'wb').write(new.encode('latin-1'))
print('written:', path)
