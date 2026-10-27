import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/Classes/Manager/JavascriptManager.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_FORCEGC_STUB' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

# 找 void JavascriptManager::forceGC()
anchor = b'void JavascriptManager::forceGC()'
if anchor not in b:
    print('ABORT: anchor not found'); sys.exit(1)

i = b.find(anchor)
j = b.find(b'{', i)
if j < 0:
    print('ABORT: brace not found'); sys.exit(1)
end = j + 1
insert = nl + b'    return; // WASM_FORCEGC_STUB'

b2 = b[:end] + insert + b[end:]

for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_FORCEGC_STUB' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_forcegc')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: JavascriptManager.cpp.bak_forcegc)')
else:
    print('DRY-RUN only; add --apply to write')
