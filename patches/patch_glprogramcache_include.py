#!/usr/bin/env python3
"""
Fix: renderer/CCGLProgramCache.h uses cocos2d::EventListenerCustom through
CC_SYNTHESIZE_RETAIN (USE_AGTK block) but only includes base/CCRef.h.
MSVC gets the type from earlier includes; clang reports an incomplete type.
Add '#include "base/CCEventListenerCustom.h"' right after '#include "base/CCRef.h"'.

DRY-RUN by default.  --apply writes.  --root DIR (default ~/PGMMV-src/Player/cocos2d/cocos)
--no-git-check for tests.  CRLF/LF preserved; latin-1 byte-preserving.
"""
import sys, os, subprocess, difflib

ROOT = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos')
args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])

REL = 'renderer/CCGLProgramCache.h'
ANCHOR = '#include "base/CCRef.h"'
NEW = '#include "base/CCEventListenerCustom.h"'

def eol(line):
    return line[len(line.rstrip('\r\n')):]

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
if any('CCEventListenerCustom.h' in l for l in lines):
    print('already patched, no change'); sys.exit(0)
hits = [i for i, l in enumerate(lines) if l.strip() == ANCHOR]
if len(hits) != 1:
    print("ABORT - expected exactly one '%s' line, found %d" % (ANCHOR, len(hits))); sys.exit(1)
i = hits[0]
new_lines = lines[:i + 1] + [NEW + (eol(lines[i]) or '\n')] + lines[i + 1:]
new = ''.join(new_lines)

print('== ' + REL)
diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + REL, 'b/' + REL, n=2)
sys.stdout.write(''.join(l if l.endswith('\n') else l + '\n' for l in diff).replace('\r', ''))
if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to write.'); sys.exit(0)
open(path, 'wb').write(new.encode('latin-1'))
print('written:', path)
