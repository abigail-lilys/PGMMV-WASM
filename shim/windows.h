// [wasm-port] Minimal stand-ins for the few Windows API bits the win32 audio sources use.
// Everything else in those files is OpenAL + mpg123/vorbis, which work on Emscripten.
#ifndef _WINDOWS_
#define _WINDOWS_

#ifdef __cplusplus
typedef wchar_t WCHAR;
typedef unsigned int UINT;
typedef unsigned long DWORD;
typedef int BOOL;
typedef unsigned char BYTE;

#define CP_UTF8 65001
#define CP_ACP 0

// _winLog in AudioEngine-win32.cpp converts UTF-8 to wide chars only to feed OutputDebugStringW,
// which is a no-op here -- both conversions can do nothing.
static inline int MultiByteToWideChar(UINT, DWORD, const char*, int, WCHAR*, int) { return 0; }
static inline int WideCharToMultiByte(UINT, DWORD, const WCHAR*, int, char*, int, const char*, BOOL*) { return 0; }
static inline void OutputDebugStringA(const char*) {}
static inline void OutputDebugStringW(const WCHAR*) {}

// Device enumeration: waveOut only exists on Windows. The browser has one default output device.
static inline UINT waveOutGetNumDevs() { return 1; }
#endif

#endif
