#!/usr/bin/env python3
"""
Round-2 source fixes needed by clang/Emscripten (MSVC accepted them):

  1. renderer/CCTexture2D.cpp   : USE_AGTK code calls TextureCache members but only a
                                  forward declaration is visible -> include CCTextureCache.h
  2. physics/CCPhysicsWorld.cpp : USE_AGTK code names cocos2d::SpriteBatchNode without
                                  including its header -> include 2d/CCSpriteBatchNode.h
  3. platform/CCFileUtils.cpp   : non-Windows FileUtils::removeFile (USE_AGTK block)
                                  uses an undeclared variable 'fullPath' (3 uses);
                                  the function parameter is 'path' -> use 'path'.
                                  (clearFileExistCache() already erases the full path too.)

DRY-RUN by default.  --apply writes.  --root DIR (default ~/PGMMV-src/Player/cocos2d/cocos)
--no-git-check for tests.  latin-1 byte-preserving (cp932 comments untouched), CRLF/LF kept.
All checks run before anything is written.
"""
import sys, os, re, subprocess, difflib

ROOT = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos')
args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def insert_after(anchor, new_include):
    def fn(lines):
        if any(new_include in l for l in lines):
            return None
        hits = [i for i, l in enumerate(lines) if l.strip() == anchor]
        if len(hits) != 1:
            raise PatchError("expected exactly one '%s' line, found %d" % (anchor, len(hits)))
        i = hits[0]
        return lines[:i + 1] + [new_include + (eol(lines[i]) or '\n')] + lines[i + 1:]
    return fn

def fix_removefile(lines):
    starts = [i for i, l in enumerate(lines) if l.lstrip().startswith('bool FileUtils::removeFile(')]
    cands = [i for i in starts if any('CC_PLATFORM_NX' in lines[j] for j in range(i + 1, min(i + 5, len(lines))))]
    if len(cands) != 1:
        raise PatchError("expected exactly one non-Windows FileUtils::removeFile (with the NX check), found %d" % len(cands))
    s = cands[0]
    e = None
    for j in range(s + 1, min(s + 30, len(lines))):
        if 'remove(path.c_str())' in lines[j]:
            e = j
            break
    if e is None:
        raise PatchError("could not find 'remove(path.c_str())' after removeFile")
    region = lines[s:e]
    n = sum(len(re.findall(r'\bfullPath\b', l)) for l in region)
    if n == 0:
        if any('clearFileExistCache(path)' in l for l in region):
            return None
        raise PatchError("no 'fullPath' in removeFile and not already patched")
    if n != 3:
        raise PatchError("expected 3 uses of 'fullPath' in removeFile, found %d" % n)
    new = list(lines)
    for j in range(s, e):
        new[j] = re.sub(r'\bfullPath\b', 'path', new[j])
    return new

PLAN = [
    ('renderer/CCTexture2D.cpp',   insert_after('#include "renderer/CCGLProgramCache.h"', '#include "renderer/CCTextureCache.h"')),
    ('physics/CCPhysicsWorld.cpp', insert_after('#include "2d/CCScene.h"', '#include "2d/CCSpriteBatchNode.h"')),
    ('platform/CCFileUtils.cpp',   fix_removefile),
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
    # keep terminal output ASCII-safe: cp932 comment lines are shown as '?'
    sys.stdout.write(out.encode('ascii', 'replace').decode('ascii'))

if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.'); sys.exit(0)
for path, name, old, new in results:
    if new is not None:
        open(path, 'wb').write(new.encode('latin-1'))
        print('written:', path)
print('\nDone.')
