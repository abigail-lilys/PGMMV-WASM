import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/test/pgmmv_main.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_TICKER_V3' in b:
    print('already patched'); sys.exit(0)
old = b'if (!n || depth > 2) return; /* WASM_TICKER_V2 */'
n = b.count(old)
if n != 1:
    print('ABORT: expected exactly 1 match for V2 marker, found', n); sys.exit(1)
b2 = b.replace(old, b'if (!n || depth > 4) return; /* WASM_TICKER_V3 */')
for l in b2.split(b'\n'):
    if b'depth >' in l:
        print(l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_ticker3')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: pgmmv_main.cpp.bak_ticker3)')
else:
    print('DRY-RUN only; add --apply to write')
