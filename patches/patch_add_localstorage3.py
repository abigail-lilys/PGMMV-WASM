import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_ADD_LOCALSTORAGE3' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

# 锚点用之前加的注释
anchor = b'# WASM_ADD_LOCALSTORAGE'
if anchor not in b:
    print('ABORT: anchor not found'); sys.exit(1)

insert = (
    b'target_sources(ext_jsb PRIVATE ${COCOS_DIR}/scripting/js-bindings/manual/localstorage/js_bindings_system_functions.cpp) # WASM_ADD_LOCALSTORAGE3' + nl
)

b2 = b.replace(anchor, insert + anchor, 1)

for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_ADD_LOCALSTORAGE3' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_localstorage3')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_localstorage3)')
else:
    print('DRY-RUN only; add --apply to write')
