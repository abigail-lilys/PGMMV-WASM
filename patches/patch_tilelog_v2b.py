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

def ins_before_line(b, anchor, text):
    i = b.find(anchor)
    if i < 0: return None
    k = b.rfind(nl, 0, i)
    head = 0 if k < 0 else k + len(nl)
    return b[:head] + text + b[head:]

# ---- 1. 在 if (strstr(...)) 之前打印 isFileExist/fullPath（每个 filename 一次）
a1 = b'if (strstr(imgData->getFilename(), ".gif") != nullptr'
uniq(a1)
t1 = (b'    // WASM_TILE_LOG_V2' + nl +
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
b2 = ins_before_line(b, a1, t1)
if b2 is None: print('ABORT: insert #1 failed'); sys.exit(1)
b = b2

# ---- 2. initWithFile 之前
a2 = b'if (!cocos2d::SpriteBatchNode::initWithFile(imgData->getFilename())) {'
uniq(a2)
t2 = (b'    // WASM_TILE_LOG_V2' + nl +
      b'    if (_wasmFirst) { printf("[WASM-TILE-V2] initWithFile begin\\n"); fflush(stdout); }' + nl)
b2 = ins_before_line(b, a2, t2)
if b2 is None: print('ABORT: insert #2 failed'); sys.exit(1)
b = b2

# ---- 3. initWithFile 失败分支的 return false 之前
i3 = b.find(a2)
j3 = b.find(b'return false;', i3)
if j3 < 0: print('ABORT: return false not found'); sys.exit(1)
k3 = b.rfind(nl, 0, j3)
h3 = 0 if k3 < 0 else k3 + len(nl)
t3 = (b'        // WASM_TILE_LOG_V2' + nl +
      b'        if (_wasmFirst) { printf("[WASM-TILE-V2] initWithFile FAILED\\n"); fflush(stdout); }' + nl)
b = b[:h3] + t3 + b[h3:]

# ---- 4. setTilesetData 之前
a4 = b'this->setTilesetData(tilesetData);'
uniq(a4)
t4 = (b'    // WASM_TILE_LOG_V2' + nl +
      b'    if (_wasmFirst) { printf("[WASM-TILE-V2] initWithFile OK\\n"); fflush(stdout); }' + nl)
b2 = ins_before_line(b, a4, t4)
if b2 is None: print('ABORT: insert #4 failed'); sys.exit(1)
b = b2

for k, l in enumerate(b.split(b'\n'), 1):
    if b'WASM_TILE_LOG_V2' in l or b'_wasmFirst' in l or b'_wasmLastFile' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_tilelog_v2')
    open(p, 'wb').write(b)
    print('APPLIED (backup: Tile.cpp.bak_tilelog_v2)')
else:
    print('DRY-RUN only; add --apply to write')
