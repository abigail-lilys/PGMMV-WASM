#!/usr/bin/env python3
"""
renderer/ccGLStateCache.cpp : GL::bindVAO() on Emscripten (-sFULL_ES2).

Problem (shown by the GL call-sequence log): after a draw that uses client-side vertex arrays (LayerColor:
GL::enableVertexAttribs + glVertexAttribPointer(..., _noMVPVertices)), the NEXT draw with a VAO bound (DrawNode,
batched sprites) is preceded by vertexAttribPointer(0,3,FLOAT,..)/(1,4,FLOAT,..) with the LayerColor's layout, which
overwrites the VAO's real pointers. Emscripten's FULL_ES2 emulation keeps per-attribute-INDEX client-array state
(libwebgl.js: GL.currentContext.clientBuffers[i] = {clientside, enabled, ...}) that is not per-VAO, and
glBindVertexArray does not touch it; preDrawHandleClientVertexAttribBindings() re-applies every entry that is
"clientside && enabled".

Fix: when switching from the default VAO (0) to a real VAO, first disable the attributes that the state cache says
are enabled (the default VAO is still bound, so only its state changes) and clear the cache. That clears the
emulation's "enabled" flag; the next client-array draw re-enables through GL::enableVertexAttribs() as before.
Only done when s_VAO == 0, otherwise glDisableVertexAttribArray would modify another VAO's state.

The inserted '#if' line ends with '// wasm-fix' (idempotence marker).
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

REL = 'renderer/ccGLStateCache.cpp'
MARK = '// wasm-fix'

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def patch(lines):
    if any(MARK in l for l in lines):
        return None
    text = ''.join(lines)
    if 'static uint32_t s_attributeFlags' not in text or 'MAX_ATTRIBUTES' not in text:
        raise PatchError("s_attributeFlags / MAX_ATTRIBUTES not found in the file")
    fn = [i for i, l in enumerate(lines) if l.startswith('void bindVAO(GLuint vaoId)')]
    if len(fn) != 1:
        raise PatchError("expected exactly one 'void bindVAO(GLuint vaoId)', found %d" % len(fn))
    end = next((j for j in range(fn[0] + 1, len(lines)) if lines[j].startswith('}')), None)
    if end is None:
        raise PatchError("could not find the end of bindVAO()")
    hits = [i for i in range(fn[0], end) if lines[i].strip() == 's_VAO = vaoId;']
    if len(hits) != 1:
        raise PatchError("expected exactly one 's_VAO = vaoId;' inside bindVAO(), found %d" % len(hits))
    i = hits[0]
    if lines[i - 1].strip() != '{' or lines[i - 2].strip() != 'if (s_VAO != vaoId)':
        raise PatchError("'s_VAO = vaoId;' is not the first statement of 'if (s_VAO != vaoId) {'")
    ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    e = eol(lines[i]) or '\n'
    block = [
        '#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN ' + MARK,
        '// -sFULL_ES2 emulates client-side vertex arrays with per-attribute-INDEX state that is not per-VAO',
        '// (libwebgl.js: GL.currentContext.clientBuffers). After a client-array draw (e.g. LayerColor) those entries',
        '// stay "clientside + enabled" and are re-applied on top of the real pointers stored in a VAO bound later.',
        '// Coming from the default VAO, disable the cached attributes so they are not re-applied.',
        'if (s_VAO == 0 && vaoId != 0 && s_attributeFlags != 0)',
        '{',
        '    for (int i = 0; i < MAX_ATTRIBUTES; ++i)',
        '        if (s_attributeFlags & (1u << i))',
        '            glDisableVertexAttribArray(i);',
        '    s_attributeFlags = 0;',
        '}',
        '#endif',
    ]
    out = []
    for b in block:
        if b.startswith('#'):
            out.append(b + e)          # preprocessor lines at column 0
        else:
            out.append(ind + b + e)
    return lines[:i] + out + lines[i:]

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
diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + REL, 'b/' + REL, n=3)
out = ''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', '')
sys.stdout.write(out.encode('ascii', 'replace').decode('ascii'))
if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.'); sys.exit(0)
open(path, 'wb').write(new.encode('latin-1'))
print('written:', path)
