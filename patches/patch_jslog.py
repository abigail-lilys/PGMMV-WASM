import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/scripting/js-bindings/manual/ScriptingCore.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
MARK = b'WASM_PORT_JSLOG'
if MARK in b:
    print('already patched'); sys.exit(0)
old = b'CCLOG("JS: %s", _js_log_buf)'
new = b'cocos2d::log("JS: %s", _js_log_buf) /* WASM_PORT_JSLOG */'
n = b.count(old)
if n != 1:
    print('ABORT: expected exactly 1 match, found', n); sys.exit(1)
i = b.index(old)
ln = b[:i].count(b'\n')
lines = b.split(b'\n')
print('--- context (line numbers) ---')
for k in range(max(0, ln - 8), min(len(lines), ln + 9)):
    print(k + 1, lines[k].decode('utf-8', 'replace').rstrip('\r'))
b2 = b.replace(old, new)
if do_apply:
    shutil.copy2(p, p + '.bak_jslog')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: ScriptingCore.cpp.bak_jslog)')
else:
    print('DRY-RUN only; add --apply to write')
