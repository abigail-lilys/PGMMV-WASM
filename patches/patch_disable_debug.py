import os, sys, shutil
do_apply = '--apply' in sys.argv

def patch(p, marks_to_remove):
    if not os.path.exists(p):
        print('missing:', p); return 0
    b = open(p, 'rb').read()
    if b'WASM_DISABLE_DEBUG_V1' in b:
        print('already patched:', p); return 0
    n = 0
    for old, new in marks_to_remove:
        c = b.count(old)
        if c > 0:
            b = b.replace(old, new)
            n += c
    if n > 0:
        if do_apply:
            shutil.copy2(p, p + '.bak_disable_debug')
            open(p, 'wb').write(b)
            print(f'APPLIED {p} ({n} replacements)')
        else:
            print(f'DRY-RUN {p} ({n} replacements)')
    else:
        print(f'NO MATCH {p}')
    return n

# 1. pgmmv_main.cpp: 注释掉 ticker 安装
patch(os.path.expanduser('~/pgmmv-wasm/test/pgmmv_main.cpp'), [
    (b'if (ret == 0) { wasmInstallTicker(); }', b'// WASM_DISABLE_DEBUG_V1: if (ret == 0) { wasmInstallTicker(); }'),
])

# 2. Tile.cpp: 替换 WASM-TILE-V2 的 printf + fflush
# 需要匹配完整的 printf 行和 fflush 行
tile_text = r'''
    // WASM_TILE_LOG_V2
    static std::string _wasmLastFile;
    bool _wasmFirst = (_wasmLastFile != imgData->getFilename());
    if (_wasmFirst) {
        _wasmLastFile = imgData->getFilename();
        auto _fu = cocos2d::FileUtils::getInstance();
        bool _ex = _fu->isFileExist(imgData->getFilename());
        auto _fp = _fu->fullPathForFilename(imgData->getFilename());
        printf("[WASM-TILE-V2] isFileExist(%s)=%d fullPath=%s\n", imgData->getFilename(), (int)_ex, _fp.c_str());
        fflush(stdout);
    }
'''.strip()
# 直接整个块替换为 // 太难，因为行尾可能是 \r\n。
# 替代方案：保留 _wasmFirst 但把 printf 注释掉。
# 实际上我们可以直接把所有 `printf("[WASM-TILE-V2]...` 替换为 `// printf(...` 但这样 fflush 会孤立。
# 干脆整个 V2 块用 #if 0 包起来。
# 为了不搞乱代码，在 Tide.cpp 找 `static std::string _wasmLastFile;` 和后面的 `}`
# 我们把 printf 行和 fflush 行注释掉就行。
# 但因为行尾不同，用 bytes 替换比较麻烦。用正则或者按行处理更好。
