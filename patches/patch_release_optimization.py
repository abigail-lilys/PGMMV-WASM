import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_RELEASE_O2' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

# 1. 在文件顶部的 project(...) 之前插入默认的 C/CXX 优化 Flag
anchor1 = b'project(pgmmv'
if anchor1 not in b:
    print('ABORT: project(pgmmv not found'); sys.exit(1)
insert1 = b'set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O2")' + nl + b'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -g0") # WASM_RELEASE_O2' + nl + nl
b2 = b.replace(anchor1, insert1 + anchor1, 1)

# 2. 降低 Emscripten 的断言级别，并移除 profiling-funcs 以提升速度
b2 = b2.replace(b'-sASSERTIONS=2', b'-sASSERTIONS=0')
b2 = b2.replace(b'--profiling-funcs', b'')

for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_RELEASE_O2' in l or b'sASSERTIONS=' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_release_o2')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: CMakeLists.txt.bak_release_o2)')
else:
    print('DRY-RUN only; add --apply to write')
