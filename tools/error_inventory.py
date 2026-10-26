#!/usr/bin/env python3
"""
Syntax-only compile of EVERY Classes translation unit with the build's exact flags (build/compile_commands.json),
then a de-duplicated inventory of the distinct errors (same file:line:message in many TUs = one entry, with a TU count).
Header errors repeat in every TU that includes the header, so this turns tens of thousands of lines into a short list.

  error_inventory.py [--jobs N] [--limit N] [--only SUBSTR] [--top N] [--out FILE] [--json FILE]

  --jobs N     parallel compiles (default 3)
  --limit N    -ferror-limit per TU (default 40)
  --only S     only TUs whose path contains S (e.g. Classes/Lib/)
  --top N      print the N most widespread distinct errors (default 60)
  --out FILE   write the full inventory there (default ~/pgmmv-wasm/inventory.txt)
"""
import json, sys, os, re, shlex, subprocess, collections
from concurrent.futures import ThreadPoolExecutor

a = sys.argv[1:]
def opt(name, default):
    return a[a.index(name) + 1] if name in a else default
JOBS = int(opt('--jobs', 3)); LIMIT = int(opt('--limit', 40)); TOP = int(opt('--top', 60))
ONLY = opt('--only', '')
OUT = os.path.expanduser(opt('--out', '~/pgmmv-wasm/inventory.txt'))
JSON = os.path.expanduser(opt('--json', '~/pgmmv-wasm/build/compile_commands.json'))
entries = [e for e in json.load(open(JSON)) if '/Classes/' in e['file'].replace('\\', '/') and e['file'].endswith(('.cpp', '.cc'))
           and ONLY in e['file']]
if not entries:
    print('no matching translation units'); sys.exit(1)

def run(e):
    toks, out, skip = shlex.split(e['command']), [], False
    for t in toks:
        if skip:
            skip = False; continue
        if t == '-o':
            skip = True; continue
        if t == '-c' or t.startswith('-ferror-limit='):
            continue
        out.append(t)
    out += ['-fsyntax-only', '-ferror-limit=%d' % LIMIT]
    r = subprocess.run(out, cwd=e['directory'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return e['file'], r.stdout.decode('utf-8', 'replace')

ERR = re.compile(r'^(/[^:]+):(\d+):(\d+): (?:fatal )?error: (.*)$')
seen = collections.defaultdict(set)   # key -> set of TUs
tu_err = 0
done = 0
print('compiling %d translation units with %d jobs (syntax-only) ...' % (len(entries), JOBS), flush=True)
with ThreadPoolExecutor(max_workers=JOBS) as ex:
    for tu, text in ex.map(run, entries):
        done += 1
        keys = set()
        for l in text.split('\n'):
            m = ERR.match(l)
            if m:
                path = m.group(1)
                path = path.split('/Player/', 1)[-1] if '/Player/' in path else path
                keys.add((path, int(m.group(2)), re.sub(r"'[^']*'", "'X'", m.group(4))[:120], m.group(4)[:160]))
        if keys:
            tu_err += 1
        for k in keys:
            seen[k].add(tu)
        if done % 10 == 0:
            print('  ... %d/%d done' % (done, len(entries)), flush=True)

items = sorted(seen.items(), key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1]))
with open(OUT, 'w') as f:
    for k, tus in items:
        f.write('%4d TUs  %s:%d  %s\n' % (len(tus), k[0], k[1], k[3]))
print('\nTUs with errors: %d / %d    distinct (file:line:message) errors: %d    full list: %s' % (tu_err, len(entries), len(items), OUT))
print('\n-- by file (distinct errors per file, top 25) --')
per = collections.Counter(k[0] for k, _ in items)
for p, n in per.most_common(25):
    print('%4d  %s' % (n, p))
print('\n-- most widespread distinct errors (top %d) --' % TOP)
for k, tus in items[:TOP]:
    print('%3d TUs  %s:%d  %s' % (len(tus), k[0], k[1], k[3][:110]))
