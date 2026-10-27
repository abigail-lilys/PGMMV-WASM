import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_FORCE_FS_V1' in b:
    print('already patched'); sys.exit(0)
anchor = b'test_game/Resources@/app/Resources")'
n = b.count(anchor)
if n != 1:
    print('ABORT: expected exactly 1 match, found', n); sys.exit(1)
j = b.find(b'\n', b.find(anchor))
if j < 0:
    print('ABORT: no newline after anchor'); sys.exit(1)
nl = b'\r\n' if b[j-1:j] == b'\r' else b'\n'
end = j + len(nl)
insert = b'target_link_options(pgmmv PRIVATE -sFORCE_FILESYSTEM=1) # WASM_FORCE_FS_V1' + nl
b2 = b[:end] + insert + b[end:]
for k, l in enumerate(b2.split(b'\n'), 1):
    if b'WASM_FORCE_FS_V1' in l or b'test_game/Resources@/app/Resources' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_forcefs')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_forcefs)')
else:
    print('DRY-RUN only; add --apply to write')
