#pragma once
// wasm shim: 替代 Player/proj.win32/stdafx.h
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

// 标准头
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <cstddef>
#include <cstdarg>
#include <cassert>
#include <cerrno>
#include <cctype>
#include <ctime>
#include <new>

#include <string>
#include <vector>
#include <list>
#include <map>
#include <set>
#include <memory>
#include <algorithm>
#include <functional>
#include <utility>
#include <type_traits>
#include <limits>

// PGMMV Classes 依赖 cocos2d 命名空间全局可见
#include "cocos2d.h"
using namespace cocos2d;
using namespace std;

// PGMMV Classes 在 Windows 下通过 stdafx.h 拿到 ImGui
#include "imgui.h"
