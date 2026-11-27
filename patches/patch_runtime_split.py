#!/usr/bin/env python3
"""patch_runtime_split.py -- separate runtime and game data in CMakeLists.txt.
 1) drops every --preload-file link option (game data is no longer baked into pgmmv.data)
 2) pgmmv output becomes build/runtime/pgmmv.js (+ .wasm), no emscripten .html shell
 3) links web/loader.js with --pre-js and exports FS/addRunDependency/removeRunDependency
Usage: python3 patch_runtime_split.py [--file CMakeLists.txt] [--apply]   (dry-run by default)
"""
import os, re, shutil, sys
args = sys.argv[1:]
APPLY = '--apply' in args
p = os.path.expanduser(args[args.index('--file') + 1] if '--file' in args else '~/pgmmv-wasm/CMakeLists.txt')
MARK = b'RUNTIME_SPLIT_V1'
b = open(p, 'rb').read()
if MARK in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

out, dropped = [], []
for l in b.split(nl):
    if b'--preload-file=' in l and not l.lstrip().startswith(b'#'):
        dropped.append(l.strip().decode('utf-8', 'replace'))
        out.append(b'# [' + MARK + b'] removed: ' + l.strip().replace(b'--preload-file=', b'preload-file '))
    else:
        out.append(l)
s = nl.join(out)

pat = re.compile(rb'set_target_properties\(pgmmv PROPERTIES(\s+)RUNTIME_OUTPUT_DIRECTORY "\$\{CMAKE_BINARY_DIR\}/web"(\s+)SUFFIX "\.html"(\s*)\)')
if len(pat.findall(s)) != 1:
    print('ABORT: pgmmv set_target_properties(... SUFFIX ".html") block not found exactly once'); sys.exit(1)
s = pat.sub(lambda m: b'set_target_properties(pgmmv PROPERTIES' + m.group(1) +
            b'RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/runtime"' + m.group(2) +
            b'SUFFIX ".js"' + m.group(3) + b')', s, count=1)

block = nl.join([
    b'',
    b'# --- ' + MARK + b': runtime/data split. Game data is fetched at run time (web/loader.js + manifest.json) ---',
    b'target_link_options(pgmmv PRIVATE',
    b'    "SHELL:--pre-js ${CMAKE_SOURCE_DIR}/web/loader.js"',
    b'    "-sEXPORTED_RUNTIME_METHODS=FS,addRunDependency,removeRunDependency,callMain"',
    b'    -sFORCE_FILESYSTEM=1)',
    b'set_property(TARGET pgmmv APPEND PROPERTY LINK_DEPENDS "${CMAKE_SOURCE_DIR}/web/loader.js")',
    b''])
s = s.rstrip(b'\r\n') + nl + block

print('dropped %d --preload-file line(s):' % len(dropped))
for d in dropped: print('   ', d)
print('output -> build/runtime/pgmmv.js ; appended link block')
if APPLY:
    shutil.copy2(p, p + '.bak_runtime_split')
    open(p, 'wb').write(s)
    print('APPLIED (backup: %s.bak_runtime_split)' % os.path.basename(p))
else:
    print('DRY-RUN only; add --apply to write')
