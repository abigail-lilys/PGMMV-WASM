// First version: no system-font rendering. TTF goes through FreeType elsewhere.
#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#include "platform/CCDevice.h"

NS_CC_BEGIN

int Device::getDPI()
{
    return 96;
}

void Device::setAccelerometerEnabled(bool /*isEnabled*/)
{
}

void Device::setAccelerometerInterval(float /*interval*/)
{
}

void Device::setKeepScreenOn(bool /*value*/)
{
}

void Device::vibrate(float /*duration*/)
{
}

Data Device::getTextureDataForText(const char * /*text*/, const FontDefinition& /*textDefinition*/, TextAlign /*align*/, int &width, int &height, bool& hasPremultipliedAlpha)
{
    width = 0;
    height = 0;
    hasPremultipliedAlpha = false;
    return Data();
}

NS_CC_END

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
