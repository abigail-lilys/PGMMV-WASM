import os, sys, shutil
p = os.path.expanduser('~/pgmmv-wasm/test/pgmmv_main.cpp')
do_apply = '--apply' in sys.argv
b = open(p, 'rb').read()
MARK = b'WASM_TICKER_V1'
if MARK in b:
    print('already patched'); sys.exit(0)
nl = b'\r\n' if b'\r\n' in b else b'\n'
a1 = b'int main(int argc, char** argv)'
a2 = b'printf("=== [WASM] run() returned %d ===\\n", ret); fflush(stdout);'
n1, n2 = b.count(a1), b.count(a2)
if n1 != 1 or n2 != 1:
    print('ABORT: expected exactly 1 match each, found', n1, n2); sys.exit(1)
TICKER = r'''// WASM_TICKER_V1: debug ticker, prints scene info every 3 seconds
#include "base/CCDirector.h"
#include "base/CCScheduler.h"
#include "2d/CCNode.h"
#include "2d/CCScene.h"
#include "renderer/CCTextureCache.h"
#include <typeinfo>
#include <string>

static void wasmDumpNode(cocos2d::Node* n, int depth)
{
    if (!n || depth > 1) return;
    printf("[WASM-TICK] %*s%s children=%d visible=%d\n", depth * 2, "", typeid(*n).name(), (int)n->getChildrenCount(), (int)n->isVisible());
    int shown = 0;
    for (auto* c : n->getChildren())
    {
        if (shown++ >= 6) break;
        wasmDumpNode(c, depth + 1);
    }
}

static void wasmTick(float)
{
    auto* d = cocos2d::Director::getInstance();
    auto* sc = d->getRunningScene();
    printf("[WASM-TICK] frames=%d paused=%d scene=%s\n", (int)d->getTotalFrames(), (int)d->isPaused(), sc ? typeid(*sc).name() : "null");
    wasmDumpNode(sc, 0);
    std::string info = d->getTextureCache()->getCachedTextureInfo();
    while (!info.empty() && info.back() == '\n') info.pop_back();
    size_t pos = info.rfind('\n');
    if (pos != std::string::npos) info = info.substr(pos + 1);
    printf("[WASM-TICK] tex: %s\n", info.c_str());
    fflush(stdout);
}

static void wasmInstallTicker()
{
    cocos2d::Director::getInstance()->getScheduler()->schedule(wasmTick, (void*)&wasmInstallTicker, 3.0f, false, "wasm_tick");
}

'''
t = TICKER.replace('\n', nl.decode()).encode('utf-8')
b2 = b.replace(a1, t + a1)
b2 = b2.replace(a2, a2 + nl + b'    if (ret == 0) { wasmInstallTicker(); }')
i = b2.index(a1)
print('--- patched file from main() ---')
for k, l in enumerate(b2[i:].split(b'\n'), 1):
    print(k, l.decode('utf-8', 'replace').rstrip('\r'))
if do_apply:
    shutil.copy2(p, p + '.bak_ticker')
    open(p, 'wb').write(b2)
    print('APPLIED (backup: pgmmv_main.cpp.bak_ticker)')
else:
    print('DRY-RUN only; add --apply to write')
