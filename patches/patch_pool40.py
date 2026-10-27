import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_POOL40_V1' in b:
    print('already patched'); sys.exit(0)
old = b'-sPTHREAD_POOL_SIZE=24'
n = b.count(old)
if n != 1:
    print('ABORT: expected exactly 1 match, found', n); sys.exit(1)
i = b.find(old)
j = b.find(b'\n', i)
if j < 0:
    print('ABORT: no newline after anchor'); sys.exit(1)
nl = b'\r\n' if b[j-1:j] == b'\r' else b'\n'
b2 = b.replace(old, b'-sPTHREAD_POOL_SIZE=40', 1)
for k, l in enumerate(b2.split(b'\n'), 1):
    if b'PTHREAD_POOL_SIZE' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_pool40')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_pool40)')
else:
    print('DRY-RUN only; add --apply to write')
