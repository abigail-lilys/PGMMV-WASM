import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/scripting/js-bindings/manual/js_module_register.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_ENABLE_JSBINDINGS' in b:
    print('already patched'); sys.exit(0)

old = b'#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN // [wasm-port] js modules'
if old not in b:
    print('ABORT: anchor not found'); sys.exit(1)

# 替换为 #if 0
new = b'#if 0 // WASM_ENABLE_JSBINDINGS: ' + old[3:]
b2 = b.replace(old, new)

for k, l in enumerate(b2.split(b'\n'), 1):
    if b'WASM_ENABLE_JSBINDINGS' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))

if do_apply:
    shutil.copy2(p, p + '.bak_enable_jsbindings')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: js_module_register.cpp.bak_enable_jsbindings)')
else:
    print('DRY-RUN only; add --apply to write')
