// Derived from cocos2d-x platform/linux/CCApplication-linux.h (MIT license).
#ifndef __CCAPPLICATION_EMSCRIPTEN_H__
#define __CCAPPLICATION_EMSCRIPTEN_H__

#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#include "platform/CCCommon.h"
#include "platform/CCApplicationProtocol.h"
#include <string>

NS_CC_BEGIN
class Rect;

class Application : public ApplicationProtocol
{
public:
    Application();
    virtual ~Application();

    virtual void setAnimationInterval(float interval) override;
    virtual void setAnimationInterval(float interval, SetIntervalReason reason) override;

    /**
     @brief Start the main loop. NON-BLOCKING on Emscripten: this registers a
            browser main loop and returns immediately. The Application (and the
            AppDelegate) must therefore stay alive after run() returns.
     */
    int run();

    static Application* getInstance();

    /** @deprecated Use getInstance() instead */
    CC_DEPRECATED_ATTRIBUTE static Application* sharedApplication();

    /* override functions */
    virtual LanguageType getCurrentLanguage() override;
    virtual const char * getCurrentLanguageCode() override;
#ifdef USE_AGTK
    virtual std::string getCurrentLanguageShortName() const override;
#endif
    virtual std::string getVersion() override;
    virtual bool openURL(const std::string &url) override;

    CC_DEPRECATED_ATTRIBUTE void setResourceRootPath(const std::string& rootResDir);
    CC_DEPRECATED_ATTRIBUTE const std::string& getResourceRootPath(void);

    virtual Platform getTargetPlatform() override;

#ifdef USE_AGTK
    // Kept for source compatibility with the Windows implementation (preview only).
    static void setDropFileCallback(void(*callback)(const char *filename));
#endif

protected:
    static void emscriptenMainLoop(void* arg);

    double      _animationInterval;  // milliseconds
    double      _lastFrameTime;      // milliseconds (emscripten_get_now)
    std::string _resourceRootPath;

#ifdef USE_AGTK
    static void (*_dropFileCallback)(const char *filename);
#endif
    static Application * sm_pSharedApplication;
};

NS_CC_END

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
#endif // __CCAPPLICATION_EMSCRIPTEN_H__
