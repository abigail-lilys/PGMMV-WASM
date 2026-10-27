import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/platform/CCImage.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_IMG_LOG' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

def uniq(s):
    n = b.count(s)
    if n != 1:
        print('ABORT: expected 1 match, found', n, 'for', s[:70].decode('utf-8','replace'))
        sys.exit(1)
    return b.find(s)

def ins_after_line(b, anchor, text):
    i = b.find(anchor)
    if i < 0: return None
    j = b.find(nl, i)
    if j < 0: return None
    end = j + len(nl)
    return b[:end] + text + b[end:]

# ---- 1. initWithImageFile: Data data = ... 之后
a1 = b'Data data = FileUtils::getInstance()->getDataFromFile(_filePath);'
uniq(a1)
t1 = (b'    { // WASM_IMG_LOG' + nl +
      b'        static int _wasmImgLogN1 = 0;' + nl +
      b'        if (_wasmImgLogN1++ < 20) {' + nl +
      b'            printf("[WASM-IMG] file=%s dataNull=%d size=%ld\\n", _filePath.c_str(), (int)data.isNull(), (long)data.getSize()); fflush(stdout);' + nl +
      b'        }' + nl +
      b'    }' + nl)
b2 = ins_after_line(b, a1, t1)
if b2 is None: print('ABORT: insert #1 failed'); sys.exit(1)
b = b2

# ---- 2. initWithImageData: _fileType = detectFormat(...) 之后
a2 = b'_fileType = detectFormat(unpackedData, unpackedLen);'
uniq(a2)
t2 = (b'        { // WASM_IMG_LOG' + nl +
      b'            static int _wasmImgLogN2 = 0;' + nl +
      b'            if (_wasmImgLogN2++ < 20) {' + nl +
      b'                printf("[WASM-IMG] dataLen=%ld fileType=%d path=%s\\n", (long)dataLen, (int)_fileType, _filePath.c_str()); fflush(stdout);' + nl +
      b'            }' + nl +
      b'        }' + nl)
b2 = ins_after_line(b, a2, t2)
if b2 is None: print('ABORT: insert #2 failed'); sys.exit(1)
b = b2

for k, l in enumerate(b.split(b'\n'), 1):
    if b'WASM_IMG_LOG' in l or b'wasmImgLogN' in l:
        print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_imagelog')
    open(p, 'wb').write(b)
    print('APPLIED (backup: CCImage.cpp.bak_imagelog)')
else:
    print('DRY-RUN only; add --apply to write')
