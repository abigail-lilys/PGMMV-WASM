// Derived from cocos2d-x platform/linux/CCCommon-linux.cpp (MIT license).
#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#include "platform/CCCommon.h"
#include "platform/emscripten/CCStdC-emscripten.h"
#include "base/CCConsole.h"

NS_CC_BEGIN

void MessageBox(const char * msg, const char * title)
{
    log("%s: %s", title, msg);
}

void LuaLog(const char * format)
{
    puts(format);
}

NS_CC_END

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
