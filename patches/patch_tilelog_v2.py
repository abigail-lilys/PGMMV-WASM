import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/Classes/Lib/Tile.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_TILE_LOG_V2' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

def uniq(s):
    n = b.count(s)
    if n != 1:
        print('ABORT: expected 1 match, found', n, 'for', s[:60].decode('utf-8','replace'))
        sys.exit(1)
    return b.find(s)

# 1. imgData 赋值后，加 isFileExist 打印（每个 filename 只打印一次）
a1 = b'auto imgData = project->getImageData(tilesetData->getImageId());'
i1 = uniq(a1)
end1 = b.find(nl, i1) + len(nl)
t1 = (nl + b'    // WASM_TILE_LOG_V2' + nl +
      b'    static std::string _wasmLastFile;' + nl +
      b'    bool _wasmFirst = (_wasmLastFile != imgData->getFilename());' + nl +
      b'    if (_wasmFirst) {' + nl +
      b'        _wasmLastFile = imgData->getFilename();' + nl +
      b'        auto _fu = cocos2d::FileUtils::getInstance();' + nl +
      b'        bool _ex = _fu->isFileExist(imgData->getFilename());' + nl +
      b'        auto _fp = _fu->fullPathForFilename(imgData->getFilename());' + nl +
      b'        printf("[WASM-TILE-V2] isFileExist(%s)=%d fullPath=%s\\n", imgData->getFilename(), (int)_ex, _fp.c_str());' + nl +
      b'        fflush(stdout);' + nl +
      b'    }' + nl)
b2 = b[:end1] + t1 + b[end1:]

# 2. initWithFile 之前加 begin 打印
a2 = b'if (!cocos2d::SpriteBatchNode::initWithFile(imgData->getFilename())) {'
i2 = uniq(a2)
t2 = (b'    // WASM_TILE_LOG_V2' + nl +
      b'    if (_wasmFirst) { printf("[WASM-TILE-V2] initWithFile begin\\n"); fflush(stdout); }' + nl)
b2 = b2[:i2] + t2 + b2[i2:]

# 3. initWithFile 失败分支加打印（找 a2 之后第一个 return false;）
i3 = b2.find(a2)
j3 = b2.find(b'return false;', i3)
if j3 < 0: print('ABORT: return false not found'); sys.exit(1)
t3 = (b'        // WASM_TILE_LOG_V2' + nl +
      b'        if (_wasmFirst) { printf("[WASM-TILE-V2] initWithFile FAILED\\n"); fflush(stdout); }' + nl)
b2 = b2[:j3] + t3 + b2[j3:]

# 4. setTilesetData 之前加 OK 打印
a4 = b'this->setTilesetData(tilesetData);'
i4 = uniq(a4)
t4 = (b'    // WASM_TILE_LOG_V2' + nl +
      b'    if (_wasmFirst) { printf("[WASM-TILE-V2] initWithFile OK\\n"); fflush(stdout); }' + nl)
b2 = b2[:i4] + t4 + b2[i4:]

for k, l in enumerate(b2.split(b'\n'), 1):
    if b'WASM_TILE_LOG_V2' in l or b'_wasmFirst' in l or b'_wasmLastFile' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_tilelog_v2')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: Tile.cpp.bak_tilelog_v2)')
else:
    print('DRY-RUN only; add --apply to write')
