import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/Classes/Lib/Tile.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
MARK = b'WASM_TILE_LOG_V1'
if MARK in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

def find_unique(needle):
    i = b.find(needle)
    if i < 0: return None, 'not found'
    j = b.find(needle, i+1)
    if j >= 0: return None, 'ambiguous (>=2)'
    return i, None

def insert_before_line(b, anchor, text):
    i = b.find(anchor)
    if i < 0: return None
    k = b.rfind(nl, 0, i)
    head = 0 if k < 0 else k + len(nl)
    return b[:head] + text + b[head:]

def insert_after_line(b, anchor, text):
    i = b.find(anchor)
    if i < 0: return None
    j = b.find(nl, i)
    if j < 0: return None
    end = j + len(nl)
    return b[:end] + text + b[end:]

def apply_one(anchor, mode, text):
    global b
    idx, err = find_unique(anchor)
    if err:
        print('ABORT:', mode, anchor[:60].decode('utf-8','replace'), err); sys.exit(1)
    b2 = (insert_before_line if mode == 'before' else insert_after_line)(b, anchor, text)
    if b2 is None:
        print('ABORT: insert failed', anchor[:60].decode('utf-8','replace')); sys.exit(1)
    b = b2
    print('OK:', mode, anchor[:60].decode('utf-8','replace'))

A_anchor = b'int layerId = sceneLayer->getLayerId();'
A_text = nl + b'    // WASM_TILE_LOG_V1' + nl + b'    printf("[WASM-TILE] layer=%d tileListCount=%d\\n", layerId, (int)tileList->count()); fflush(stdout);'
apply_one(A_anchor, 'after', A_text)

F_anchor = b'if (strstr(imgData->getFilename(), ".gif") != nullptr'
F_text = b'    // WASM_TILE_LOG_V1' + nl + b'    printf("[WASM-TILE] Tileset::init imgData=%p tilesetId=%d\\n", (void*)imgData, tilesetData->getImageId()); fflush(stdout);' + nl + b'    if (imgData) { printf("[WASM-TILE] filename=%s\\n", imgData->getFilename()); fflush(stdout); }' + nl
apply_one(F_anchor, 'before', F_text)

C_anchor = b'if (!cocos2d::SpriteBatchNode::initWithFile(imgData->getFilename())) {'
C_text = b'    // WASM_TILE_LOG_V1' + nl + b'    printf("[WASM-TILE] initWithFile begin\\n"); fflush(stdout);' + nl
apply_one(C_anchor, 'before', C_text)

D_anchor = b'this->setTilesetData(tilesetData);'
D_text = b'    // WASM_TILE_LOG_V1' + nl + b'    printf("[WASM-TILE] initWithFile OK\\n"); fflush(stdout);' + nl
apply_one(D_anchor, 'before', D_text)

E_anchor = b'spriteBatchNode = Tileset::create(tilesetData, sceneLayer);'
E_text = nl + b'    // WASM_TILE_LOG_V1' + nl + b'    printf("[WASM-TILE] Tileset::create tilesetId=%d result=%p\\n", tilesetId, (void*)spriteBatchNode); fflush(stdout);'
apply_one(E_anchor, 'after', E_text)

if do_apply:
    shutil.copy2(p, p + '.bak_tilelog')
    open(p, 'wb').write(b)
    print('APPLIED (backup: Tile.cpp.bak_tilelog)')
else:
    print('DRY-RUN only; add --apply to write')
