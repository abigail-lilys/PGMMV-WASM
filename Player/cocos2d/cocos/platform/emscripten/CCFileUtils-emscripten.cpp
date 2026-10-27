// Derived from cocos2d-x platform/linux/CCFileUtils-linux.cpp (MIT license).
#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#include "platform/emscripten/CCFileUtils-emscripten.h"
#include "platform/emscripten/CCApplication-emscripten.h"
#include "platform/CCCommon.h"
#include "base/ccMacros.h"
#include "base/ccUTF8.h"
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <dirent.h>
#include <stdio.h>
#include <errno.h>
#include <algorithm>

// There is no executable path in WASM: use fixed virtual paths.
// Override at compile time with -DCC_EMSCRIPTEN_APP_DIR=\"/xxx/\" if needed.
// Must start and end with '/'.
#ifndef CC_EMSCRIPTEN_APP_DIR
#define CC_EMSCRIPTEN_APP_DIR "/app/"
#endif
#ifndef CC_EMSCRIPTEN_WRITABLE_DIR
#define CC_EMSCRIPTEN_WRITABLE_DIR "/save/"
#endif
#ifndef CC_RESOURCE_FOLDER_EMSCRIPTEN
#define CC_RESOURCE_FOLDER_EMSCRIPTEN "Resources/"
#endif

using namespace std;

#define DECLARE_GUARD std::lock_guard<std::recursive_mutex> mutexGuard(_mutex)

NS_CC_BEGIN

FileUtils* FileUtils::getInstance()
{
    if (s_sharedFileUtils == nullptr)
    {
        s_sharedFileUtils = new FileUtilsEmscripten();
        if(!s_sharedFileUtils->init())
        {
          delete s_sharedFileUtils;
          s_sharedFileUtils = nullptr;
          CCLOG("ERROR: Could not init CCFileUtilsEmscripten");
        }
    }
    return s_sharedFileUtils;
}

FileUtilsEmscripten::FileUtilsEmscripten()
{}

bool FileUtilsEmscripten::init()
{
    DECLARE_GUARD;
    _defaultResRootPath = CC_EMSCRIPTEN_APP_DIR CC_RESOURCE_FOLDER_EMSCRIPTEN;
    _writablePath = CC_EMSCRIPTEN_WRITABLE_DIR;
    return FileUtils::init();
}

string FileUtilsEmscripten::getWritablePath() const
{
    DECLARE_GUARD;
    struct stat st;
    if (stat(_writablePath.c_str(), &st) != 0 || !S_ISDIR(st.st_mode)) {
        mkdir(_writablePath.c_str(), 0744);
    }

    return _writablePath;
}

bool FileUtilsEmscripten::isFileExistInternal(const std::string& strFilePath) const
{
    DECLARE_GUARD;
    if (strFilePath.empty())
    {
        return false;
    }

    std::string strPath = strFilePath;
    if (!isAbsolutePath(strPath))
    { // Not absolute path, add the default root path at the beginning.
        strPath.insert(0, _defaultResRootPath);
    }

    struct stat sts;
    return (stat(strPath.c_str(), &sts) == 0) && S_ISREG(sts.st_mode);
}

#ifdef USE_AGTK
// Unix style, ends with '/'.
std::string FileUtilsEmscripten::getApplicationPath()
{
    return CC_EMSCRIPTEN_APP_DIR;
}

// Regular file names only (no directories, no path prefix); empty when
// the directory cannot be opened. Sorted for a deterministic order.
std::vector<std::string> FileUtilsEmscripten::getDirContents(std::string dirname)
{
    std::vector<std::string> list;
    DIR* dir = opendir(dirname.c_str());
    if (dir == nullptr)
    {
        return list;
    }

    std::string base = dirname;
    if (!base.empty() && base[base.size() - 1] != '/')
    {
        base += '/';
    }

    struct dirent* ent = nullptr;
    while ((ent = readdir(dir)) != nullptr)
    {
        std::string name = ent->d_name;
        if (name == "." || name == "..")
        {
            continue;
        }
        struct stat sts;
        if (stat((base + name).c_str(), &sts) == 0 && S_ISREG(sts.st_mode))
        {
            list.push_back(name);
        }
    }
    closedir(dir);

    std::sort(list.begin(), list.end());
    return list;
}
#endif

#ifdef USE_AGTK_MEMORY_FILE
// Same as the non-Windows branch of FileUtilsWin32.
// UNVERIFIED: fmemopen availability in Emscripten's libc (link/compile will tell).
FILE* FileUtilsEmscripten::memFopen(const char* ptr, size_t sz, int p[2])
{
    return fmemopen((void*)ptr, sz, "rb");
}

void FileUtilsEmscripten::memFclose(FILE* fp, int p[2])
{
    fclose(fp);
}
#endif

NS_CC_END

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
