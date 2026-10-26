// MSVC-only constructs used by the Windows project. Force-included (before stdafx.h) into every Classes C++ source.
#pragma once
#define __declspec(x)

// --- Windows GUID (type only; Common.h declares GuidToString/StringToGuid with it) ---------------------------
#ifdef __cplusplus
#include <stdint.h>
#ifndef GUID_DEFINED
#define GUID_DEFINED
typedef struct _GUID { uint32_t Data1; uint16_t Data2; uint16_t Data3; uint8_t Data4[8]; } GUID;
#endif
#endif

// --- ARRAYSIZE (Windows macro used by Classes/Data/ObjectCommandData.cpp) -----------------------------------
#ifndef ARRAYSIZE
#define ARRAYSIZE(a) (sizeof(a) / sizeof((a)[0]))
#endif

// --- stricmp (Windows; JavascriptManager.cpp / FontManager.cpp use it) --------------------------------------
#include <strings.h>
#ifndef stricmp
#define stricmp strcasecmp
#endif
