#!/usr/bin/env python3
"""
B71 (3)+(4, partial): engine-side Emscripten branches.

  (3) cocos2d.h : add an Emscripten include block right after the LINUX block
        #if (CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN)
            #include "platform/emscripten/CCApplication-emscripten.h"
            #include "platform/desktop/CCGLViewImpl-desktop.h"
            #include "platform/emscripten/CCGL-emscripten.h"
            #include "platform/emscripten/CCStdC-emscripten.h"
        #endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
  (4) base/allocator/CCAllocatorMutex.h : append
        || CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
      to the pthread-mutex platform list.

NOT touched on purpose (controller group: CCController.h/.cpp,
CCEventDispatcher.cpp, CCController-linux-win32.cpp): they must be switched
together with the build list, and CCController-linux-win32.cpp has not been read yet.

Default is DRY-RUN. Options: --apply, --root DIR (default
~/PGMMV-src/Player/cocos2d/cocos), --no-git-check.
Latin-1 byte-preserving; CRLF / LF kept per line; all checks before any write.
"""
import sys, os, subprocess, difflib

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

def patch_cocos2d_h(lines):
    if any('platform/emscripten/' in l for l in lines):
        return None
    hits = [i for i, l in enumerate(lines)
            if l.strip() == '#if (CC_TARGET_PLATFORM == CC_PLATFORM_WINRT)']
    if len(hits) != 1:
        raise PatchError("expected exactly one '#if (... CC_PLATFORM_WINRT)' line, found %d" % len(hits))
    i = hits[0]
    if i < 2 or lines[i - 1].strip() != '' or \
       lines[i - 2].strip() != '#endif // CC_TARGET_PLATFORM == CC_PLATFORM_LINUX':
        raise PatchError("WINRT block is not directly preceded by '#endif // ... LINUX' + blank line")
    e = eol(lines[i]) or '\n'
    block = ['#if (CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN)',
             '    #include "platform/emscripten/CCApplication-emscripten.h"',
             '    #include "platform/desktop/CCGLViewImpl-desktop.h"',
             '    #include "platform/emscripten/CCGL-emscripten.h"',
             '    #include "platform/emscripten/CCStdC-emscripten.h"',
             '#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN',
             '']
    return lines[:i] + [b + e for b in block] + lines[i:]

MUTEX_OLD = ('#if CC_TARGET_PLATFORM == CC_PLATFORM_TIZEN || CC_TARGET_PLATFORM == CC_PLATFORM_IOS || '
             'CC_TARGET_PLATFORM == CC_PLATFORM_MAC || CC_TARGET_PLATFORM == CC_PLATFORM_ANDROID || '
             'CC_TARGET_PLATFORM == CC_PLATFORM_LINUX || CC_TARGET_PLATFORM == CC_PLATFORM_NX')
MUTEX_NEW = MUTEX_OLD + ' || CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN'

def patch_mutex_h(lines):
    done = [i for i, l in enumerate(lines) if l.strip() == MUTEX_NEW]
    hits = [i for i, l in enumerate(lines) if l.strip() == MUTEX_OLD]
    if done and not hits:
        return None
    if len(hits) != 1:
        raise PatchError("expected exactly one pthread platform-list '#if' line, found %d" % len(hits))
    i = hits[0]
    new = list(lines)
    new[i] = MUTEX_NEW + eol(lines[i])
    return new

PLAN = [
    ('cocos2d.h', patch_cocos2d_h),
    ('base/allocator/CCAllocatorMutex.h', patch_mutex_h),
]

def git_ok(path):
    d = os.path.dirname(path)
    b = os.path.basename(path)
    r = subprocess.run(['git', '-C', d, 'ls-files', '--error-unmatch', b],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        return 'not tracked by git'
    r = subprocess.run(['git', '-C', d, 'status', '--porcelain', '--', b],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.stdout.strip():
        return 'has uncommitted changes: ' + r.stdout.decode().strip()
    return None

results, errors = [], []
for name, fn in PLAN:
    path = os.path.join(ROOT, name)
    if not os.path.isfile(path):
        errors.append('%s: file not found' % name)
        continue
    if GITCHECK:
        why = git_ok(path)
        if why:
            errors.append('%s: %s' % (name, why))
            continue
    with open(path, 'rb') as f:
        old = f.read().decode('latin-1')
    lines = old.splitlines(True)
    try:
        nl = fn(lines)
    except PatchError as ex:
        errors.append('%s: %s' % (name, ex))
        continue
    results.append((path, name, old, None if nl is None else ''.join(nl)))

if errors:
    print('ABORT - nothing was written. Problems:')
    for e in errors:
        print('  -', e)
    sys.exit(1)

for path, name, old, new in results:
    if new is None:
        print('== %s: already patched, no change' % name)
        continue
    print('== %s' % name)
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                'a/' + name, 'b/' + name, n=2)
    sys.stdout.write(''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', ''))

if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.')
    sys.exit(0)

for path, name, old, new in results:
    if new is not None:
        with open(path, 'wb') as f:
            f.write(new.encode('latin-1'))
        print('written:', path)
print('\nDone.')
