// [wasm-port] jsb_cocos2dx_auto.cpp registers CocosDenshion::SimpleAudioEngine for JS. The win32
// implementation uses MCI (Windows-only) and is excluded; audio playback goes through
// cocos2d::experimental::AudioEngine (ext_audio) instead. Provide no-op implementations so the
// JS registration compiles and links; scripts that call cc.SimpleAudioEngine simply hear nothing.
#include "audio/include/SimpleAudioEngine.h"

namespace CocosDenshion {

static SimpleAudioEngine* s_pSimpleAudioEngine = nullptr;

SimpleAudioEngine* SimpleAudioEngine::getInstance() {
    if (!s_pSimpleAudioEngine) s_pSimpleAudioEngine = new SimpleAudioEngine();
    return s_pSimpleAudioEngine;
}

void SimpleAudioEngine::end() {}

SimpleAudioEngine::SimpleAudioEngine() {}
SimpleAudioEngine::~SimpleAudioEngine() {}

void SimpleAudioEngine::preloadBackgroundMusic(const char*) {}
void SimpleAudioEngine::playBackgroundMusic(const char*, bool) {}
void SimpleAudioEngine::stopBackgroundMusic(bool) {}
void SimpleAudioEngine::pauseBackgroundMusic() {}
void SimpleAudioEngine::resumeBackgroundMusic() {}
void SimpleAudioEngine::rewindBackgroundMusic() {}
bool SimpleAudioEngine::willPlayBackgroundMusic() { return false; }
bool SimpleAudioEngine::isBackgroundMusicPlaying() { return false; }
float SimpleAudioEngine::getBackgroundMusicVolume() { return 0.0f; }
void SimpleAudioEngine::setBackgroundMusicVolume(float) {}
float SimpleAudioEngine::getEffectsVolume() { return 0.0f; }
void SimpleAudioEngine::setEffectsVolume(float) {}
unsigned int SimpleAudioEngine::playEffect(const char*, bool, float, float, float) { return 0; }
void SimpleAudioEngine::pauseEffect(unsigned int) {}
void SimpleAudioEngine::pauseAllEffects() {}
void SimpleAudioEngine::resumeEffect(unsigned int) {}
void SimpleAudioEngine::resumeAllEffects() {}
void SimpleAudioEngine::stopEffect(unsigned int) {}
void SimpleAudioEngine::stopAllEffects() {}
void SimpleAudioEngine::preloadEffect(const char*) {}
void SimpleAudioEngine::unloadEffect(const char*) {}

} // namespace CocosDenshion
