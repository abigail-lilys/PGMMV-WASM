import os, sys, shutil
p = os.path.expanduser('~/PGMMV-src/Player/cocos2d/cocos/audio/AudioEngine.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
if b'WASM_AUDIO_SILENCE' in b:
    print('already patched'); sys.exit(0)

nl = b'\r\n' if b'\r\n' in b else b'\n'
lines = b.split(nl)
out_lines = []
patched = 0
for line in lines:
    if b'The audio instance %d is non-existent' in line:
        out_lines.append(b'    // ' + line.strip() + b' // WASM_AUDIO_SILENCE')
        patched += 1
    else:
        out_lines.append(line)

if patched == 0:
    print('ABORT: no matches found'); sys.exit(1)

b2 = nl.join(out_lines)
for k, l in enumerate(b2.split(nl), 1):
    if b'WASM_AUDIO_SILENCE' in l:
        print(k, l.decode('utf-8', 'replace').strip())

if do_apply:
    shutil.copy2(p, p + '.bak_audiosilence')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: AudioEngine.cpp.bak_audiosilence)')
else:
    print('DRY-RUN only; add --apply to write')
