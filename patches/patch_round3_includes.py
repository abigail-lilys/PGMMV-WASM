#!/usr/bin/env python3
"""
Round-3 include fixes for clang (MSVC accepted them):

  1. renderer/CCTexture2D.cpp   : TextureCache is still incomplete at the USE_AGTK use site
                                  (an existing include is conditional or not effective)
                                  -> add an unconditional '#include "renderer/CCTextureCache.h"'
  2. physics/CCPhysicsWorld.cpp : SpriteBatchNode::getPhysicsChildren() yields Sprite*; Sprite must be
                                  complete to convert to Node* -> '#include "2d/CCSprite.h"'

Each added line carries a marker comment ('clang-fix'); that marker is what makes the script idempotent
(not the mere presence of the header name, which was too loose in round 2).

DRY-RUN by default.  --apply writes.  --root DIR (default ~/PGMMV-src/Player/cocos2d/cocos)
--no-git-check for tests.  latin-1 byte-preserving, CRLF/LF kept, all checks before any write.
"""
import sys, os, subprocess, difflib

ROOT = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos')
args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])

MARK = 'clang-fix'

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def insert_after(anchor, new_line):
    def fn(lines):
        if any(l.startswith(new_line.split(' //')[0]) and MARK in l for l in lines):
            return None
        hits = [i for i, l in enumerate(lines) if l.strip() == anchor]
        if len(hits) != 1:
            raise PatchError("expected exactly one '%s' line, found %d" % (anchor, len(hits)))
        i = hits[0]
        return lines[:i + 1] + [new_line + (eol(lines[i]) or '\n')] + lines[i + 1:]
    return fn

PLAN = [
    ('renderer/CCTexture2D.cpp',
     insert_after('#include "renderer/CCGLProgramCache.h"',
                  '#include "renderer/CCTextureCache.h" // clang-fix: full TextureCache type (USE_AGTK code)')),
    ('physics/CCPhysicsWorld.cpp',
     insert_after('#include "2d/CCSpriteBatchNode.h"',
                  '#include "2d/CCSprite.h" // clang-fix: Sprite must be complete to convert to Node*')),
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
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + name, 'b/' + name, n=1)
    out = ''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', '')
    sys.stdout.write(out.encode('ascii', 'replace').decode('ascii'))

if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.'); sys.exit(0)
for path, name, old, new in results:
    if new is not None:
        open(path, 'wb').write(new.encode('latin-1'))
        print('written:', path)
print('\nDone.')
