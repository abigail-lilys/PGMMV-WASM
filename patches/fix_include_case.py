#!/usr/bin/env python3
"""
Windows -> Linux/Emscripten include fixer for the PGMMV player sources (Classes/).

The Windows project is case-insensitive and accepts backslashes in #include paths; clang on Linux is not.
This script scans  #include "..."  lines (angle-bracket includes are ignored) in Classes/ (vendor dir Classes/External/vlc
is skipped) and, for every quoted include that does NOT resolve exactly, tries
   1. replacing '\\' by '/'
   2. a case-insensitive match of every path component
against the same lookup the compiler does: the including file's directory first, then the include directories.
Only UNIQUE resolutions are rewritten (only the path text inside the quotes changes; line endings and encoding are kept).
Includes that resolve in no known directory are only listed (they may come from system / engine dirs this script does not know).

DRY-RUN by default: prints a report. --apply rewrites the files (Classes/ must be git-clean, so `git diff` shows exactly
what changed). --root DIR = the Player directory (default ~/PGMMV-src/Player).  --no-git-check for tests.
"""
import sys, os, re, subprocess

args = sys.argv[1:]
APPLY = '--apply' in args
GITCHECK = '--no-git-check' not in args
ROOT = os.path.expanduser('~/PGMMV-src/Player')
if '--root' in args:
    ROOT = os.path.expanduser(args[args.index('--root') + 1])
ROOT = os.path.abspath(ROOT)
SCAN = os.path.join(ROOT, 'Classes')

INC_DIRS = [os.path.join(ROOT, p) for p in [
    '', 'Classes', 'Classes/External', 'Classes/Manager', 'Classes/External/vlc/include', 'proj.win32',
    'cocos2d', 'cocos2d/cocos', 'cocos2d/cocos/platform', 'cocos2d/cocos/base', 'cocos2d/cocos/audio/include',
    'cocos2d/extensions', 'cocos2d/external', 'cocos2d/external/chipmunk/include', 'cocos2d/external/chipmunk/include/chipmunk',
    'cocos2d/external/ImGUI', 'cocos2d/external/tinyxml2', 'cocos2d/external/unzip']]
for extra in ['~/pgmmv-wasm/prebuilt/sm34/include', '~/pgmmv-wasm/shim',
              '/data/data/com.termux/files/usr/opt/emscripten/cache/sysroot/include']:
    extra = os.path.expanduser(extra)
    if os.path.isdir(extra):
        INC_DIRS.append(extra)

_ls = {}
def listdir(d):
    if d not in _ls:
        try:
            _ls[d] = os.listdir(d)
        except OSError:
            _ls[d] = []
    return _ls[d]

def walk(base, comps, ci):
    """Resolve comps starting at base; ci = case-insensitive. Returns (real_path, [mapped components]) or None; 'AMBIG' if ambiguous."""
    cur, mapped = base, []
    for i, c in enumerate(comps):
        if c in ('.', ''):
            mapped.append(c)
            continue
        if c == '..':
            cur = os.path.dirname(cur)
            mapped.append(c)
            continue
        names = listdir(cur)
        if c in names:
            hit = c
        elif ci:
            cands = [n for n in names if n.lower() == c.lower()]
            if len(cands) == 1:
                hit = cands[0]
            elif len(cands) > 1:
                return 'AMBIG'
            else:
                return None
        else:
            return None
        mapped.append(hit)
        cur = os.path.join(cur, hit)
    return cur, mapped

def resolve(inc, file_dir):
    """-> ('ok', None) | ('fix', newtext) | ('unresolved', None) | ('ambig', None)"""
    text = inc.replace('\\', '/')
    comps = text.split('/')
    bases = [file_dir] + INC_DIRS
    # exact (after backslash normalisation)
    for b in bases:
        r = walk(b, comps, False)
        if r and r != 'AMBIG' and os.path.isfile(r[0]):
            return ('ok', None) if text == inc else ('fix', text)
    found = set()
    for b in bases:
        r = walk(b, comps, True)
        if r == 'AMBIG':
            return ('ambig', None)
        if r and os.path.isfile(r[0]):
            found.add('/'.join(r[1]))
    if len(found) == 1:
        return ('fix', found.pop())
    if len(found) > 1:
        return ('ambig', None)
    return ('unresolved', None)

INC_RE = re.compile(r'^((?:\xef\xbb\xbf)?\s*#\s*include\s*")([^"]+)(")')   # optional UTF-8 BOM on line 1

files = []
for dp, dn, fn in os.walk(SCAN):
    dn[:] = [d for d in dn if not (dp == os.path.join(SCAN, 'External') and d == 'vlc')]
    for f in fn:
        if f.lower().endswith(('.cpp', '.h', '.hpp', '.c', '.cc', '.inl')):
            files.append(os.path.join(dp, f))
files.sort()

fixes = {}       # path -> list of (lineno, old, new)
unres = {}       # include text -> count
ambig = {}
scanned = 0
for p in files:
    data = open(p, 'rb').read().decode('latin-1')
    fdir = os.path.dirname(p)
    for ln, line in enumerate(data.split('\n'), 1):
        m = INC_RE.match(line)
        if not m:
            continue
        scanned += 1
        inc = m.group(2)
        st, new = resolve(inc, fdir)
        if st == 'fix' and new != inc:
            fixes.setdefault(p, []).append((ln, inc, new))
        elif st == 'unresolved':
            unres[inc] = unres.get(inc, 0) + 1
        elif st == 'ambig':
            ambig[inc] = ambig.get(inc, 0) + 1

nfix = sum(len(v) for v in fixes.values())
bs = sum(1 for v in fixes.values() for (_, o, _) in v if '\\' in o)
print('scanned %d quoted includes in %d files under %s' % (scanned, len(files), os.path.relpath(SCAN, ROOT)))
print('fixable (unique): %d includes in %d files   (of which backslash paths: %d)' % (nfix, len(fixes), bs))
cnt = 0
for p in sorted(fixes):
    for (ln, old, new) in fixes[p]:
        cnt += 1
        if cnt <= 60:
            print('  FIX %s:%d  "%s" -> "%s"' % (os.path.relpath(p, ROOT), ln, old, new))
if nfix > 60:
    print('  ... %d more fixable includes not listed' % (nfix - 60))
print('ambiguous (not touched): %d distinct' % len(ambig))
for k in sorted(ambig)[:15]:
    print('  AMBIG "%s" x%d' % (k, ambig[k]))
print('unresolved in all known dirs (not touched): %d distinct' % len(unres))
for k in sorted(unres, key=lambda x: -unres[x])[:40]:
    print('  UNRES "%s" x%d' % (k, unres[k]))

if not APPLY:
    print('\nDRY-RUN only. Re-run with --apply to rewrite the files.')
    sys.exit(0)

if GITCHECK:
    r = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', '--', 'Classes'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0 or r.stdout.strip():
        print('ABORT - Classes/ is not git-clean (or not a git tree); nothing was written.')
        sys.exit(1)

for p, items in fixes.items():
    data = open(p, 'rb').read().decode('latin-1')
    lines = data.split('\n')
    for (ln, old, new) in items:
        line = lines[ln - 1]
        m = INC_RE.match(line)
        assert m and m.group(2) == old, 'line changed under us: %s:%d' % (p, ln)
        lines[ln - 1] = m.group(1) + new + m.group(3) + line[m.end():]
    open(p, 'wb').write('\n'.join(lines).encode('latin-1'))
print('\nwritten: %d includes in %d files' % (nfix, len(fixes)))
