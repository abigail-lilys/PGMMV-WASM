import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_ADD_LOCALSTORAGE' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

anchor = b'# marker: ext_jsb_specifics'
if anchor not in b:
    print('ABORT: anchor not found'); sys.exit(1)

insert = (
    b'# WASM_ADD_LOCALSTORAGE' + nl +
    b'target_sources(ext_jsb PRIVATE ${COCOS_DIR}/scripting/js-bindings/manual/localstorage/js_bindings_system_registration.cpp)' + nl +
    nl
)

b2 = b.replace(anchor, insert + anchor, 1)

for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_ADD_LOCALSTORAGE' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_localstorage')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_localstorage)')
else:
    print('DRY-RUN only; add --apply to write')
