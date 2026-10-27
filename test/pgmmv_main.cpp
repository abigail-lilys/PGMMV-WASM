#include "AppDelegate.h"
#include "platform/CCApplication.h"
#include <cstdio>
#include <emscripten.h>

// WASM_TICKER_V1: debug ticker, prints scene info every 3 seconds
#include "base/CCDirector.h"
#include "base/CCScheduler.h"
#include "2d/CCNode.h"
#include "2d/CCScene.h"
#include "renderer/CCTextureCache.h"
#include <typeinfo>
#include <string>

static void wasmDumpNode(cocos2d::Node* n, int depth)
{
    if (!n || depth > 4) return; /* WASM_TICKER_V3 */
    printf("[WASM-TICK] %*s%s children=%d visible=%d\n", depth * 2, "", typeid(*n).name(), (int)n->getChildrenCount(), (int)n->isVisible());
    int shown = 0;
    for (auto* c : n->getChildren())
    {
        if (shown++ >= 14) break;
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

int main(int argc, char** argv)
{
    printf("\n=== [WASM] main() started ===\n"); fflush(stdout);

    auto* app = new AppDelegate();
    (void)app;

    printf("=== [WASM] calling run() ===\n"); fflush(stdout);
    int ret = cocos2d::Application::getInstance()->run();
    
    printf("=== [WASM] run() returned %d ===\n", ret); fflush(stdout);
    if (ret == 0) { wasmInstallTicker(); }
    return ret;
}
