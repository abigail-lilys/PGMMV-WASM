#ifndef __CCGL_EMSCRIPTEN_H__
#define __CCGL_EMSCRIPTEN_H__

#include "platform/CCPlatformConfig.h"
#if CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN

#ifndef GL_GLEXT_PROTOTYPES
#define GL_GLEXT_PROTOTYPES 1
#endif

#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>

// The engine is written against desktop-GL names. Map them to what the
// GLES2 headers provide. (Same idea as the Android CCGL header.)
#ifndef GL_DEPTH24_STENCIL8
#define GL_DEPTH24_STENCIL8         GL_DEPTH24_STENCIL8_OES
#endif
#define CC_GL_DEPTH24_STENCIL8      GL_DEPTH24_STENCIL8

#ifndef GL_BGRA
#define GL_BGRA                     GL_BGRA_EXT
#endif

#define glClearDepth                glClearDepthf
#define glGenVertexArrays           glGenVertexArraysOES
#define glDeleteVertexArrays        glDeleteVertexArraysOES
#define glBindVertexArray           glBindVertexArrayOES

// WebGL has no map-buffer. The engine only calls these when
// Configuration::supportsMapBuffer() is true (GL_OES_mapbuffer), which WebGL
// does not report -> UNVERIFIED assumption; the stubs fail safe by returning null.
#ifndef GL_WRITE_ONLY
#define GL_WRITE_ONLY               GL_WRITE_ONLY_OES
#endif
static inline void*     cc_emscripten_glMapBuffer(GLenum, GLenum) { return 0; }
static inline GLboolean cc_emscripten_glUnmapBuffer(GLenum)       { return GL_FALSE; }
#define glMapBuffer                 cc_emscripten_glMapBuffer
#define glUnmapBuffer               cc_emscripten_glUnmapBuffer

// NOTE (GL stage): DEPTH24_STENCIL8 renderbuffers need a WebGL2 context.
// Decide -sMIN_WEBGL_VERSION / -sMAX_WEBGL_VERSION when linking the player.

#endif // CC_TARGET_PLATFORM == CC_PLATFORM_EMSCRIPTEN
#endif // __CCGL_EMSCRIPTEN_H__
