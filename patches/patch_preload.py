import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_PRELOAD_V1' in b:
    print('already patched'); sys.exit(0)
old_data = b'target_link_options(pgmmv PRIVATE "--preload-file=${CMAKE_SOURCE_DIR}/test_game/Resources/data@/app/Resources/data")'
old_script = b'target_link_options(pgmmv PRIVATE "--preload-file=${CMAKE_SOURCE_DIR}/test_game/Resources/script@/app/Resources/script")'
new_data = b'target_link_options(pgmmv PRIVATE "--preload-file=${CMAKE_SOURCE_DIR}/test_game/Resources@/app/Resources") # WASM_PRELOAD_V1'
new_script = b'# WASM_PRELOAD_V1: script now covered by the full Resources preload above'
n1 = b.count(old_data)
n2 = b.count(old_script)
if n1 != 1 or n2 != 1:
    print('ABORT: expected exactly 1 match each, found', n1, n2); sys.exit(1)
b2 = b.replace(old_data, new_data).replace(old_script, new_script)
for l in b2.split(b'\n'):
    if b'WASM_PRELOAD_V1' in l:
        print(l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_preload')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_preload)')
else:
    print('DRY-RUN only; add --apply to write')
