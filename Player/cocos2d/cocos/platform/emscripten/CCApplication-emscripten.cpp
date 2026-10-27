// Derived from cocos2d-x platform/linux/CCApplication-linux.cpp (MIT license).
#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#include "platform/emscripten/CCApplication-emscripten.h"
#include <emscripten/emscripten.h>
#include <string>
#include <vector>
#include "base/CCDirector.h"
#include "base/CCConsole.h"
#include "base/ccUtils.h"
#include "platform/CCFileUtils.h"

NS_CC_BEGIN

// sharedApplication pointer
Application * Application::sm_pSharedApplication = nullptr;

#ifdef USE_AGTK
void (*Application::_dropFileCallback)(const char *filename) = nullptr;

void Application::setDropFileCallback(void(*callback)(const char *filename))
{
    _dropFileCallback = callback;
}
#endif

// rAF can fire a little early/late relative to the requested interval.
static const double kFrameTolerance = 1.5; // ms

// navigator.language, e.g. "ja-JP". Returns "en" when unavailable.
static std::string getBrowserLanguage()
{
    const char* s = emscripten_run_script_string("(navigator.language || 'en')");
    if (s == nullptr || s[0] == '\0')
        return "en";
    return s;
}

Application::Application()
: _animationInterval(1.0 / 60.0 * 1000.0)
, _lastFrameTime(0.0)
{
    CC_ASSERT(! sm_pSharedApplication);
    sm_pSharedApplication = this;
}

Application::~Application()
{
    CC_ASSERT(this == sm_pSharedApplication);
    sm_pSharedApplication = nullptr;
}

int Application::run()
{
    initGLContextAttrs();
    // Initialize instance and cocos2d.
    if (! applicationDidFinishLaunching())
    {
        return 1;
    }

    auto director = Director::getInstance();
    auto glview = director->getOpenGLView();
    if (glview == nullptr)
    {
        log("Application::run: no GLView was created by applicationDidFinishLaunching");
        return 1;
    }

    // Retain glview to avoid glview being released inside the loop
    glview->retain();

    _lastFrameTime = emscripten_get_now();

    // fps = 0 -> use requestAnimationFrame. simulate_infinite_loop = 0 ->
    // return immediately (the browser keeps calling the callback).
    emscripten_set_main_loop_arg(&Application::emscriptenMainLoop, this, 0, 0);
    return 0;
}

void Application::emscriptenMainLoop(void* arg)
{
    Application* app = static_cast<Application*>(arg);

    double now = emscripten_get_now();
    if (now - app->_lastFrameTime + kFrameTolerance < app->_animationInterval)
    {
        return; // not time for the next frame yet
    }
    app->_lastFrameTime = now;

    auto director = Director::getInstance();
    auto glview = director->getOpenGLView();

    if (glview != nullptr && glview->windowShouldClose())
    {
        emscripten_cancel_main_loop();
        // Same cleanup as the desktop run() loop.
        if (glview->isOpenGLReady())
        {
            director->end();
            director->mainLoop();
            director = nullptr;
        }
        glview->release();
        return;
    }

    director->mainLoop();
    if (glview != nullptr)
    {
        glview->pollEvents();
    }
}

void Application::setAnimationInterval(float interval)
{
    _animationInterval = interval * 1000.0;
}

void Application::setAnimationInterval(float interval, SetIntervalReason reason)
{
    setAnimationInterval(interval);
}

void Application::setResourceRootPath(const std::string& rootResDir)
{
    _resourceRootPath = rootResDir;
    if (_resourceRootPath[_resourceRootPath.length() - 1] != '/')
    {
        _resourceRootPath += '/';
    }
    FileUtils* pFileUtils = FileUtils::getInstance();
    std::vector<std::string> searchPaths = pFileUtils->getSearchPaths();
    searchPaths.insert(searchPaths.begin(), _resourceRootPath);
    pFileUtils->setSearchPaths(searchPaths);
}

const std::string& Application::getResourceRootPath(void)
{
    return _resourceRootPath;
}

Application::Platform Application::getTargetPlatform()
{
    return Platform::OS_EMSCRIPTEN;
}

std::string Application::getVersion()
{
    return "";
}

bool Application::openURL(const std::string &url)
{
    EM_ASM({ window.open(UTF8ToString($0), '_blank'); }, url.c_str());
    return true;
}

//////////////////////////////////////////////////////////////////////////
// static member function
//////////////////////////////////////////////////////////////////////////
Application* Application::getInstance()
{
    CC_ASSERT(sm_pSharedApplication);
    return sm_pSharedApplication;
}

// @deprecated Use getInstance() instead
Application* Application::sharedApplication()
{
    return Application::getInstance();
}

const char * Application::getCurrentLanguageCode()
{
    static char code[3] = {0};
    std::string lang = getBrowserLanguage();
    code[0] = lang.size() > 0 ? lang[0] : 'e';
    code[1] = lang.size() > 1 ? lang[1] : 'n';
    code[2] = '\0';
    return code;
}

LanguageType Application::getCurrentLanguage()
{
    return utils::getLanguageTypeByISO2(getCurrentLanguageCode());
}

#ifdef USE_AGTK
// Windows version returns e.g. "ja_JP" (locale name, '-' replaced by '_').
std::string Application::getCurrentLanguageShortName() const
{
    std::string lang = getBrowserLanguage().substr(0, 5);
    size_t pos = lang.find('-');
    if (pos != std::string::npos)
    {
        lang.replace(pos, 1, "_");
    }
    return lang;
}
#endif

NS_CC_END

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
