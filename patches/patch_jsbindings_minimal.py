import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/scripting/js-bindings/manual/js_module_register.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_JSBINDINGS_MINIMAL' in b:
    print('already patched'); sys.exit(0)

nl = b'\r\n' if b'\r\n' in b else b'\n'

# 需要注释掉的注册函数
targets = [
    b'register_all_cocos2dx_extension',
    b'register_all_cocos2dx_extension_manual',
    b'jsb_register_chipmunk',
    b'JSB_register_opengl',
    b'register_all_cocos2dx_builder',
    b'register_CCBuilderReader',
    b'register_all_cocos2dx_ui',
    b'register_all_cocos2dx_ui_manual',
    b'register_all_cocos2dx_studio',
    b'register_all_cocos2dx_studio_manual',
    b'MinXmlHttpRequest::_js_register',
    b'register_jsb_websocket',
    b'register_jsb_socketio',
    b'register_all_cocos2dx_network',
    b'register_all_cocos2dx_3d',
    b'register_all_cocos2dx_3d_manual',
    b'register_all_cocos2dx_3d_extension'
]

lines = b.split(nl)
out_lines = []
patched = 0
for line in lines:
    # 如果是 register 的行，且包含我们要注释的目标
    if b'sc->addRegisterCallback(' in line:
        if any(t in line for t in targets):
            out_lines.append(b'    // ' + line.strip() + b' // WASM_JSBINDINGS_MINIMAL')
            patched += 1
            continue
    out_lines.append(line)

if patched == 0:
    print('ABORT: no matches found'); sys.exit(1)

b2 = nl.join(out_lines)
for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_JSBINDINGS_MINIMAL' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_jsbindings_minimal')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: js_module_register.cpp.bak_jsbindings_minimal)')
else:
    print('DRY-RUN only; add --apply to write')
