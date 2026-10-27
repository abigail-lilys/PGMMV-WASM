import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/audio/win32/AudioEngine-win32.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_AUDIO_CRASH_FIX' in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'

def ins_after(b, anchor, text):
    i = b.find(anchor)
    if i < 0:
        print(f'ABORT: anchor not found: {anchor}')
        sys.exit(1)
    j = b.find(nl, i)
    if j < 0: sys.exit(1)
    end = j + len(nl)
    return b[:end] + text + b[end:]

# setVolume
anchor1 = b'auto player = _audioPlayers[audioID];' + nl + b'        player->_volume = volume;'
if anchor1 not in b:
    anchor1 = b'auto player = _audioPlayers[audioID];' + nl + b'    player->_volume = volume;'
if anchor1 in b:
    b = b.replace(anchor1, anchor1[:anchor1.find(nl)+len(nl)] + b'        if (!player) return; // WASM_AUDIO_CRASH_FIX' + nl + anchor1[anchor1.find(nl)+len(nl):])
else:
    print('ABORT: setVolume anchor not found'); sys.exit(1)

# setPitch
anchor2 = b'auto player = _audioPlayers[audioID];' + nl + b'        player->_pitch = pitch;'
if anchor2 in b:
    b = b.replace(anchor2, anchor2[:anchor2.find(nl)+len(nl)] + b'        if (!player) return; // WASM_AUDIO_CRASH_FIX' + nl + anchor2[anchor2.find(nl)+len(nl):])
else:
    print('ABORT: setPitch anchor not found'); sys.exit(1)

# setPan
anchor3 = b'auto player = _audioPlayers[audioID];' + nl + b'        memcpy(player->_pan, pan, sizeof(player->_pan));'
if anchor3 in b:
    b = b.replace(anchor3, anchor3[:anchor3.find(nl)+len(nl)] + b'        if (!player) return; // WASM_AUDIO_CRASH_FIX' + nl + anchor3[anchor3.find(nl)+len(nl):])
else:
    print('ABORT: setPan anchor not found'); sys.exit(1)

for k, l in enumerate(b.split(nl), 1):
    if b'WASM_AUDIO_CRASH_FIX' in l:
        print(k, l.decode('utf-8', 'replace'))

if do_apply:
    shutil.copy2(p, p + '.bak_audiocrash')
    open(p, 'wb').write(b)
    print('APPLIED')
else:
    print('DRY-RUN only')
