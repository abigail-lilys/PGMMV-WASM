#!/usr/bin/env python3
"""
Two Emscripten (WebGL) runtime fixes, found with the GL call tracer:

  1. renderer/CCGLProgram.cpp : every shader program failed to link in WebGL with
       "Uniforms with the same name but different type/precision: CC_CosTime".
     The generic non-desktop branch gives the vertex shader 'highp' but the fragment shader 'mediump';
     the shared built-in uniforms (CC_Time, CC_CosTime, ...) are then declared with different precision
     in the two stages, which ANGLE/WebGL rejects at link time.
     New Emscripten branch (inserted before that generic branch): ask the driver whether the fragment
     shader supports highp (glGetShaderPrecisionFormat) and use the SAME precision for both stages.
     RISK: if a device has no fragment highp, both stages fall back to mediump (vertex precision drops).

  2. base/CCConfiguration.cpp : Configuration::supportsMapBuffer() returns true on every platform except
     Android, but WebGL has no map-buffer. Treat Emscripten like Android (uses the extension query
     GL_OES_mapbuffer, which WebGL does not report), so the renderer takes its glBufferData path.

Inserted/changed lines carry '// wasm-fix' (that marker is what makes the script idempotent).
DRY-RUN by default. --apply writes. --root DIR (default ~/PGMMV-src/Player/cocos2d/cocos). --no-git-check for tests.
latin-1 byte-preserving, CRLF/LF kept, all checks before any write.
"""
import sys, os, subprocess, difflib

ROOT = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos')
args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])

MARK = '// wasm-fix'

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def patch_glprogram(lines):
    if any(MARK in l for l in lines):
        return None
    anchor = '#elif (CC_TARGET_PLATFORM != CC_PLATFORM_WIN32 && CC_TARGET_PLATFORM != CC_PLATFORM_LINUX && CC_TARGET_PLATFORM != CC_PLATFORM_MAC)'
    hits = [i for i, l in enumerate(lines) if l.strip() == anchor]
    if len(hits) != 1:
        raise PatchError("expected exactly one generic precision '#elif' line, found %d" % len(hits))
    i = hits[0]
    if not any('CC_PLATFORM_ANDROID' in lines[j] for j in range(max(0, i - 4), i)):
        raise PatchError("the Android precision branch is not just before the generic branch")
    if 'precision highp float' not in lines[i + 1] or 'compileTimeHeaders' not in ''.join(lines[max(0, i - 12):i]):
        raise PatchError("unexpected context around the generic precision branch")
    e = eol(lines[i]) or '\n'
    block = [
        '#elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN ' + MARK,
        '        {',
        '            // Vertex and fragment shaders must declare the SAME precision for the shared built-in',
        '            // uniforms (CC_CosTime ...): WebGL (ANGLE) rejects the link otherwise.',
        '            static int s_fragHigh = -1;',
        '            if (s_fragHigh < 0)',
        '            {',
        '                GLint range[2] = {0, 0}, prec = 0;',
        '                glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER, GL_HIGH_FLOAT, range, &prec);',
        '                s_fragHigh = (prec != 0) ? 1 : 0;',
        '            }',
        '            headersDef = s_fragHigh ? "precision highp float;\\n precision highp int;\\n"',
        '                                    : "precision mediump float;\\n precision mediump int;\\n";',
        '        }',
    ]
    return lines[:i] + [b + e for b in block] + lines[i:]

def patch_config(lines):
    if any(MARK in l for l in lines):
        return None
    fn = [i for i, l in enumerate(lines) if l.startswith('bool Configuration::supportsMapBuffer() const')]
    if len(fn) != 1:
        raise PatchError("expected exactly one 'bool Configuration::supportsMapBuffer() const', found %d" % len(fn))
    # search only inside the function body: from its first line to the first line that starts with '}'
    end = next((j for j in range(fn[0] + 1, len(lines)) if lines[j].startswith('}')), None)
    if end is None:
        raise PatchError("could not find the end of supportsMapBuffer()")
    g = [i for i in range(fn[0], end)
         if lines[i].strip() == '#if (CC_TARGET_PLATFORM == CC_PLATFORM_ANDROID)']
    if len(g) != 1:
        raise PatchError("expected the Android guard inside supportsMapBuffer(), found %d" % len(g))
    i = g[0]
    if 'return _supportsOESMapBuffer;' not in lines[i + 1]:
        raise PatchError("line after the Android guard is not 'return _supportsOESMapBuffer;'")
    new = list(lines)
    new[i] = ('#if (CC_TARGET_PLATFORM == CC_PLATFORM_ANDROID) || (CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN) '
              + MARK + eol(lines[i]))
    return new

PLAN = [
    ('renderer/CCGLProgram.cpp', patch_glprogram),
    ('base/CCConfiguration.cpp', patch_config),
]

def git_ok(path):
    d, b = os.path.dirname(path), os.path.basename(path)
    r = subprocess.run(['git', '-C', d, 'ls-files', '--error-unmatch', b], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        return 'not tracked by git'
    r = subprocess.run(['git', '-C', d, 'status', '--porcelain', '--', b], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.stdout.strip():
        return 'has uncommitted changes: ' + r.stdout.decode().strip()
    return None

results, errors = [], []
for name, fn in PLAN:
    path = os.path.join(ROOT, name)
    if not os.path.isfile(path):
        errors.append('%s: file not found' % name); continue
    if GITCHECK:
        why = git_ok(path)
        if why:
            errors.append('%s: %s' % (name, why)); continue
    old = open(path, 'rb').read().decode('latin-1')
    lines = old.splitlines(True)
    try:
        nl = fn(lines)
    except PatchError as ex:
        errors.append('%s: %s' % (name, ex)); continue
    results.append((path, name, old, None if nl is None else ''.join(nl)))

if errors:
    print('ABORT - nothing was written. Problems:')
    for e in errors:
        print('  -', e)
    sys.exit(1)

for path, name, old, new in results:
    if new is None:
        print('== %s: already patched, no change' % name); continue
    print('== %s' % name)
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + name, 'b/' + name, n=2)
    out = ''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', '')
    sys.stdout.write(out.encode('ascii', 'replace').decode('ascii'))

if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.'); sys.exit(0)
for path, name, old, new in results:
    if new is not None:
        open(path, 'wb').write(new.encode('latin-1'))
        print('written:', path)
print('\nDone.')
