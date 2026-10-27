import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/test/pgmmv_main.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_TICKER_V2' in b:
    print('already patched'); sys.exit(0)
a = b'if (!n || depth > 1) return;'
c = b'if (shown++ >= 6) break;'
na, nc = b.count(a), b.count(c)
if na != 1 or nc != 1:
    print('ABORT: expected exactly 1 match each, found', na, nc); sys.exit(1)
b2 = b.replace(a, b'if (!n || depth > 2) return; /* WASM_TICKER_V2 */').replace(c, b'if (shown++ >= 14) break;')
for l in b2.split(b'\n'):
    if b'depth >' in l or b'shown++' in l:
        print(l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_ticker2')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: pgmmv_main.cpp.bak_ticker2)')
else:
    print('DRY-RUN only; add --apply to write')
