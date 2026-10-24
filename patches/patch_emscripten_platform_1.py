#!/usr/bin/env python3
"""
B71 (1)+(2): enable CC_PLATFORM_EMSCRIPTEN detection and platform dispatch.

  (1) CCPlatformConfig.h : '#if defined(EMSCRIPTEN)'  ->  '#if defined(EMSCRIPTEN) || defined(__EMSCRIPTEN__)'
  (2) CCApplication.h, CCGL.h, CCPlatformDefine.h, CCStdC.h:
      insert, right before the '#elif ... CC_PLATFORM_TIZEN' line,
          #elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
          #include "platform/emscripten/<Name>-emscripten.h"

Default is DRY-RUN (prints unified diffs, writes nothing).
  --apply          write the files
  --root DIR       platform directory (default ~/PGMMV-src/Player/cocos2d/cocos/platform)
  --no-git-check   skip the 'file is tracked and clean' check (only for tests)

Files are handled as latin-1 so unknown encodings (e.g. cp932 comments) and
CRLF / LF line endings are preserved byte for byte.
Every precondition is checked for ALL files before anything is written.
"""
import sys, os, subprocess, difflib

ROOT = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/platform')
args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])

class PatchError(Exception):
    pass

def eol(line):
    return line[len(line.rstrip('\r\n')):]

def patch_config(lines):
    hits = [i for i, l in enumerate(lines) if l.strip() == '#if defined(EMSCRIPTEN)']
    done = [i for i, l in enumerate(lines)
            if l.strip() == '#if defined(EMSCRIPTEN) || defined(__EMSCRIPTEN__)']
    if done and not hits:
        return None  # already patched
    if len(hits) != 1:
        raise PatchError("expected exactly one '#if defined(EMSCRIPTEN)' line, found %d" % len(hits))
    i = hits[0]
    if not any('CC_PLATFORM_EMSCRIPTEN' in lines[j] for j in range(i + 1, min(i + 4, len(lines)))):
        raise PatchError("line after '#if defined(EMSCRIPTEN)' does not set CC_PLATFORM_EMSCRIPTEN")
    new = list(lines)
    new[i] = '#if defined(EMSCRIPTEN) || defined(__EMSCRIPTEN__)' + eol(lines[i])
    return new

def make_dispatch_patch(include_name):
    def patch(lines):
        if any('platform/emscripten/' in l for l in lines):
            return None  # already patched
        hits = [i for i, l in enumerate(lines)
                if l.strip() == '#elif CC_TARGET_PLATFORM == CC_PLATFORM_TIZEN']
        if len(hits) != 1:
            raise PatchError("expected exactly one '#elif ... CC_PLATFORM_TIZEN' line, found %d" % len(hits))
        i = hits[0]
        if i == 0 or 'platform/linux/' not in lines[i - 1]:
            raise PatchError("line before the TIZEN branch is not the linux include: %r" % (lines[i - 1] if i else None))
        e = eol(lines[i]) or '\n'
        ins = ['#elif CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN' + e,
               '#include "platform/emscripten/%s"' % include_name + e]
        return lines[:i] + ins + lines[i:]
    return patch

PLAN = [
    ('CCPlatformConfig.h',   patch_config),
    ('CCApplication.h',      make_dispatch_patch('CCApplication-emscripten.h')),
    ('CCGL.h',               make_dispatch_patch('CCGL-emscripten.h')),
    ('CCPlatformDefine.h',   make_dispatch_patch('CCPlatformDefine-emscripten.h')),
    ('CCStdC.h',             make_dispatch_patch('CCStdC-emscripten.h')),
]

def git_ok(path):
    d = os.path.dirname(path)
    r = subprocess.run(['git', '-C', d, 'ls-files', '--error-unmatch', os.path.basename(path)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        return 'not tracked by git'
    r = subprocess.run(['git', '-C', d, 'status', '--porcelain', '--', os.path.basename(path)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.stdout.strip():
        return 'has uncommitted changes: ' + r.stdout.decode().strip()
    return None

results = []   # (path, old_text, new_text or None)
errors = []
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
        new_lines = fn(lines)
    except PatchError as ex:
        errors.append('%s: %s' % (name, ex))
        continue
    results.append((path, old, None if new_lines is None else ''.join(new_lines)))

if errors:
    print('ABORT - nothing was written. Problems:')
    for e in errors:
        print('  -', e)
    sys.exit(1)

for path, old, new in results:
    nm = os.path.basename(path)
    if new is None:
        print('== %s: already patched, no change' % nm)
        continue
    print('== %s' % nm)
    diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                'a/' + nm, 'b/' + nm, n=2)
    sys.stdout.write(''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', ''))

if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.')
    sys.exit(0)

for path, old, new in results:
    if new is not None:
        with open(path, 'wb') as f:
            f.write(new.encode('latin-1'))
        print('written:', path)
print('\nDone.')
