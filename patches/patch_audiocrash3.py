import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/audio/win32/AudioEngine-win32.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_AUDIO_CRASH_FIX' in b:
    print('already patched'); sys.exit(0)

nl = b'\r\n' if b'\r\n' in b else b'\n'
lines = b.split(nl)
out_lines = []
current_func = b''

patch_count = 0
for line in lines:
    out_lines.append(line)
    
    # 记录当前的函数签名（找包含 AudioEngineImpl:: 且包含 '(' 的行）
    if b'AudioEngineImpl::' in line and b'(' in line:
        current_func = line.strip()

    # 匹配到 auto player
    if b'auto player = _audioPlayers[audioID];' in line:
        # 根据函数签名决定返回类型
        if b'float AudioEngineImpl::' in current_func:
            out_lines.append(b'    if (!player) return 0.0f; // WASM_AUDIO_CRASH_FIX')
            patch_count += 1
        elif b'bool AudioEngineImpl::' in current_func:
            out_lines.append(b'    if (!player) return false; // WASM_AUDIO_CRASH_FIX')
            patch_count += 1
        elif b'void AudioEngineImpl::' in current_func:
            out_lines.append(b'    if (!player) return; // WASM_AUDIO_CRASH_FIX')
            patch_count += 1
        else:
            print(f'ABORT: unknown return type for {current_func.decode("utf-8", "replace")}')
            sys.exit(1)

if patch_count != 9:
    print(f'ABORT: expected 9 patches, applied {patch_count}')
    sys.exit(1)

b2 = nl.join(out_lines)

for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_AUDIO_CRASH_FIX' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_audiocrash')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: AudioEngine-win32.cpp.bak_audiocrash)')
else:
    print('DRY-RUN only; add --apply to write')
