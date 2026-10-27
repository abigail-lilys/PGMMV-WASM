import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/CMakeLists.txt')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
nl = '\r\n' if b'\r\n' in b else '\n'
s = b.decode('utf-8')
MARK = '# MOUNT_RESOURCES_V41'
if MARK in s:
    print('already patched'); sys.exit(0)
a1 = 'target_link_options(pgmmv PRIVATE "--preload-file=${CMAKE_SOURCE_DIR}/test_game/Resources/data@/app/data")'
a2 = 'target_link_options(pgmmv PRIVATE "--preload-file=${CMAKE_SOURCE_DIR}/test_game/Resources/script@/app/script")'
n1, n2 = s.count(a1), s.count(a2)
if n1 != 1 or n2 != 1:
    print('ABORT: expected lines not found exactly once:', n1, n2); sys.exit(1)
new = MARK + nl + 'target_link_options(pgmmv PRIVATE "--preload-file=${CMAKE_SOURCE_DIR}/test_game/Resources@/app/Resources")'
s2 = s.replace(a1, new)
s2 = s2.replace(a2 + nl, '')
if a2 in s2:
    s2 = s2.replace(a2, '')
print('--- preload lines after patch ---')
for i, l in enumerate(s2.splitlines(), 1):
    if 'preload-file' in l or MARK in l:
        print(i, l)
if do_apply:
    shutil.copy2(p, p + '.bak_mount')
    open(p, 'wb').write(s2.encode('utf-8'))
    print('APPLIED (backup: CMakeLists.txt.bak_mount)')
else:
    print('DRY-RUN only; add --apply to write')
