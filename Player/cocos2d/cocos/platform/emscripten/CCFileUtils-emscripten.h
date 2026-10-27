// Derived from cocos2d-x platform/linux/CCFileUtils-linux.h (MIT license).
#ifndef __CC_FILEUTILS_EMSCRIPTEN_H__
#define __CC_FILEUTILS_EMSCRIPTEN_H__

#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#include "platform/CCFileUtils.h"
#include "platform/CCPlatformMacros.h"
#include "base/ccTypes.h"
#include <string>
#include <vector>

NS_CC_BEGIN

//! @brief  File operations on the Emscripten virtual file system
class CC_DLL FileUtilsEmscripten : public FileUtils
{
    friend class FileUtils;
protected:
    FileUtilsEmscripten();
private:
    std::string _writablePath;
public:
    /* override functions */
    bool init() override;
    virtual std::string getWritablePath() const override;
#ifdef USE_AGTK
    virtual std::string getApplicationPath() override;
    virtual std::vector<std::string> getDirContents(std::string dirname) override;
#endif
#ifdef USE_AGTK_MEMORY_FILE
    virtual FILE* memFopen(const char* ptr, size_t sz, int p[2]) override;
    virtual void memFclose(FILE* fp, int p[2]) override;
#endif
private:
    virtual bool isFileExistInternal(const std::string& strFilePath) const override;
};

NS_CC_END

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
#endif // __CC_FILEUTILS_EMSCRIPTEN_H__
