#!/usr/bin/env python3
"""
2d/CCRenderTexture.cpp : RenderTexture::setupDepthAndStencil() on Emscripten (WebGL1).

Observed: RenderTexture::create(..., GL_DEPTH24_STENCIL8) (what PGMMV's Classes/Lib/RenderTexture.cpp and
PhysicsObject.cpp use) raises GL_INVALID_ENUM (0x0500) and the node is not drawn.
WebGL1 has no DEPTH24_STENCIL8 renderbuffer format; packed depth+stencil is GL_DEPTH_STENCIL (0x84F9) and must be
attached ONCE to GL_DEPTH_STENCIL_ATTACHMENT (0x821A) (attaching it to DEPTH_ATTACHMENT / STENCIL_ATTACHMENT is invalid).
Literal hex values are used so no GLES2 header has to define them.

The generic '#else' branch is used on Emscripten today; a new '#elif CC_PLATFORM_EMSCRIPTEN' branch is inserted before it.
The marker '// wasm-fix' on the '#elif' line makes the script idempotent.
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

REL = '2d/CCRenderTexture.cpp'
MARK = '// wasm-fix'

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def patch(lines):
    if any(MARK in l for l in lines):
        return None
    fn = [i for i, l in enumerate(lines) if l.startswith('void RenderTexture::setupDepthAndStencil(')]
    if len(fn) != 1:
        raise PatchError("expected exactly one 'void RenderTexture::setupDepthAndStencil(', found %d" % len(fn))
    end = next((j for j in range(fn[0] + 1, len(lines)) if lines[j].startswith('}')), None)
    if end is None:
        raise PatchError("could not find the end of setupDepthAndStencil()")
    ifs = [i for i in range(fn[0], end) if lines[i].strip().replace(' ', '') == '#if(CC_TARGET_PLATFORM==CC_PLATFORM_ANDROID)']
    els = [i for i in range(fn[0], end) if lines[i].strip() == '#else']
    if len(ifs) != 1 or len(els) != 1 or not ifs[0] < els[0]:
        raise PatchError("expected one Android '#if' and one '#else' inside the function, found %d / %d" % (len(ifs), len(els)))
    e_i = els[0]
    nxt = ''.join(lines[e_i + 1:e_i + 6])
    if 'glRenderbufferStorage(GL_RENDERBUFFER, _depthAndStencilFormat' not in nxt:
        raise PatchError("the '#else' branch does not look like the generic depth/stencil setup")
    e = eol(lines[e_i]) or '\n'
    block = [
        '#elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN ' + MARK,
        '    // WebGL1: no DEPTH24_STENCIL8 renderbuffer. Packed depth+stencil = GL_DEPTH_STENCIL (0x84F9), attached once',
        '    // to GL_DEPTH_STENCIL_ATTACHMENT (0x821A). Other formats keep the generic behaviour.',
        '    glGenRenderbuffers(1, &_depthRenderBuffer);',
        '    glBindRenderbuffer(GL_RENDERBUFFER, _depthRenderBuffer);',
        '    if (_depthAndStencilFormat == GL_DEPTH24_STENCIL8)',
        '    {',
        '        glRenderbufferStorage(GL_RENDERBUFFER, 0x84F9, (GLsizei)powW, (GLsizei)powH);',
        '        glFramebufferRenderbuffer(GL_FRAMEBUFFER, 0x821A, GL_RENDERBUFFER, _depthRenderBuffer);',
        '    }',
        '    else',
        '    {',
        '        glRenderbufferStorage(GL_RENDERBUFFER, _depthAndStencilFormat, (GLsizei)powW, (GLsizei)powH);',
        '        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, _depthRenderBuffer);',
        '    }',
    ]
    return lines[:e_i] + [b + e for b in block] + lines[e_i:]

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
