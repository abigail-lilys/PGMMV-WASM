#!/usr/bin/env python3
"""
Compile ONE translation unit syntax-only with the exact flags of the CMake build (build/compile_commands.json),
so iterating on a single file takes seconds instead of a full build.

  compile_one.py <path-suffix> [--lines N] [--limit N] [--warnings] [--flags] [--dry] [--json FILE]

  <path-suffix>  e.g. Classes/Data/AssetData.cpp  (matched against the end of the file path)
  --lines N      print at most N lines of compiler output (default 60)
  --limit N      -ferror-limit=N (default 15)
  --warnings     keep the build's -w out so warnings show too
  --flags        print the build's flags (everything except -I / -isystem paths) and stop
  --dry          print the final command line and do not run it
"""
import json, sys, os, shlex, subprocess

a = sys.argv[1:]
if not a or a[0].startswith('--'):
    print(__doc__); sys.exit(2)
suffix = a[0].replace('\\', '/')
def opt(name, default):
    return a[a.index(name) + 1] if name in a else default
LINES = int(opt('--lines', 60)); LIMIT = int(opt('--limit', 15))
JSON = os.path.expanduser(opt('--json', '~/pgmmv-wasm/build/compile_commands.json'))
if not os.path.isfile(JSON):
    print('missing %s - configure with -DCMAKE_EXPORT_COMPILE_COMMANDS=ON' % JSON); sys.exit(1)

entries = [e for e in json.load(open(JSON)) if e['file'].replace('\\', '/').endswith(suffix)]
if not entries:
    print('no compile command ends with "%s"' % suffix); sys.exit(1)
if len(entries) > 1:
    print('ambiguous suffix, matches:'); [print('  ' + e['file']) for e in entries[:10]]; sys.exit(1)
e = entries[0]
toks = shlex.split(e['command'])
out, skip = [], False
for t in toks:
    if skip:
        skip = False; continue
    if t == '-o':
        skip = True; continue
    if t == '-c' or t.startswith('-ferror-limit='):
        continue
    if t == '-w' and '--warnings' in a:
        continue
    out.append(t)
out += ['-fsyntax-only', '-ferror-limit=%d' % LIMIT]

if '--flags' in a:
    skip = False
    for t in out:
        if skip:
            skip = False; continue
        if t in ('-I', '-isystem', '-include'):
            if t == '-include':
                print('-include', end=' ')
            else:
                skip = True
            continue
        if t.startswith('-I') or t.startswith('-isystem'):
            continue
        print(t)
    sys.exit(0)
if '--dry' in a:
    print(' '.join(shlex.quote(t) for t in out)); sys.exit(0)

r = subprocess.run(out, cwd=e['directory'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
text = r.stdout.decode('utf-8', 'replace').split('\n')
n_err = sum(1 for l in text if 'error:' in l)
for l in text[:LINES]:
    print(l[:300])
if len(text) > LINES:
    print('... (%d more output lines not shown)' % (len(text) - LINES))
print('== exit %d, %d error line(s) in the output' % (r.returncode, n_err))
