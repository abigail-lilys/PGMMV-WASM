import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_GETRUSAGE_STUB' in b:
    print('already patched'); sys.exit(0)
old = b'foreach(_need netdb_stubs.c sysv_sem_stubs.c)'
n = b.count(old)
if n != 1:
    print('ABORT: expected exactly 1 match, found', n); sys.exit(1)
new = b'foreach(_need netdb_stubs.c sysv_sem_stubs.c getrusage_stub.c) # WASM_GETRUSAGE_STUB'
b2 = b.replace(old, new)
for k, l in enumerate(b2.split(b'\n'), 1):
    if b'WASM_GETRUSAGE_STUB' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_getrusage')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_getrusage)')
else:
    print('DRY-RUN only; add --apply to write')
