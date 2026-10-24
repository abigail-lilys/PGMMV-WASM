# PGMMV Player -> WebAssembly. Stage B, first target: libcocos2d.a (engine core only).
# Uses the engine's own per-module CMakeLists.txt purely as source lists.
cmake_minimum_required(VERSION 3.13)
project(pgmmv_wasm LANGUAGES C CXX)

if(NOT EMSCRIPTEN)
    message(FATAL_ERROR "Configure with: emcmake cmake -S ~/pgmmv-wasm -B ~/pgmmv-wasm/build")
endif()

set(PGMMV_SRC "$ENV{HOME}/PGMMV-src" CACHE PATH "PGMMV checkout (branch wasm-port)")
set(COCOS2DX_ROOT_PATH "${PGMMV_SRC}/Player/cocos2d")
set(COCOS_DIR "${COCOS2DX_ROOT_PATH}/cocos")
set(EXT_DIR   "${COCOS2DX_ROOT_PATH}/external")

option(PGMMV_WITH_GLVIEW "Compile platform/desktop/CCGLViewImpl-desktop.cpp (GLEW must be removed first)" OFF)
option(PGMMV_QUIET "Suppress compiler warnings (-w)" ON)
set(PGMMV_EXTRA_INCLUDES "" CACHE STRING "Extra include dirs, semicolon separated")
set(PGMMV_PORT_FLAGS "-sUSE_ZLIB=1;-sUSE_LIBPNG=1;-sUSE_LIBJPEG=1;-sUSE_FREETYPE=1;-sUSE_SQLITE3=1"
    CACHE STRING "Emscripten ports (verified with a syntax-only compile)")

# The engine module files test these variables; make sure none of them is on.
foreach(_v ANDROID WINDOWS APPLE LINUX MACOSX IOS)
    set(${_v} OFF)
endforeach()

# Source lists (variables COCOS_<MODULE>_SRC, paths relative to cocos/)
foreach(_m 2d platform physics math renderer base deprecated storage)
    include("${COCOS_DIR}/${_m}/CMakeLists.txt")
endforeach()

set(PGMMV_PLATFORM_EMSCRIPTEN_SRC
    platform/emscripten/CCStdC-emscripten.cpp
    platform/emscripten/CCFileUtils-emscripten.cpp
    platform/emscripten/CCCommon-emscripten.cpp
    platform/emscripten/CCApplication-emscripten.cpp
    platform/emscripten/CCDevice-emscripten.cpp
)
if(PGMMV_WITH_GLVIEW)
    list(APPEND PGMMV_PLATFORM_EMSCRIPTEN_SRC platform/desktop/CCGLViewImpl-desktop.cpp)
endif()

set(PGMMV_ENGINE_SRC
    cocos2d.cpp
    ${COCOS_2D_SRC}
    ${COCOS_PLATFORM_SRC}
    ${PGMMV_PLATFORM_EMSCRIPTEN_SRC}
    ${COCOS_PHYSICS_SRC}
    ${COCOS_MATH_SRC}
    ${COCOS_RENDERER_SRC}
    ${COCOS_BASE_SRC}
    ${COCOS_DEPRECATED_SRC}
    ${COCOS_STORAGE_SRC}
)
list(TRANSFORM PGMMV_ENGINE_SRC PREPEND "${COCOS_DIR}/")
list(LENGTH PGMMV_ENGINE_SRC _n)
message(STATUS "pgmmv: ${_n} engine sources")

add_library(cocos2d STATIC ${PGMMV_ENGINE_SRC})
target_compile_features(cocos2d PUBLIC cxx_std_14)

target_compile_definitions(cocos2d PUBLIC
    USE_AGTK AGTK_RUNTIME AGTK_RELEASE NDEBUG AGTK_PLAYER _USRJSDLL
    CC_ENABLE_CHIPMUNK_INTEGRATION=1
    GL_GLEXT_PROTOTYPES
    CC_USE_TIFF=0 CC_USE_WEBP=0
)

target_compile_options(cocos2d PUBLIC -pthread ${PGMMV_PORT_FLAGS})
if(PGMMV_QUIET)
    target_compile_options(cocos2d PRIVATE -w)
endif()

target_include_directories(cocos2d PUBLIC
    ${COCOS2DX_ROOT_PATH}
    ${COCOS_DIR}
    ${COCOS_DIR}/platform
    ${COCOS_DIR}/base
    ${EXT_DIR}
    ${EXT_DIR}/tinyxml2
    ${EXT_DIR}/unzip
    ${EXT_DIR}/chipmunk/include
    ${PGMMV_EXTRA_INCLUDES}
)
if(PGMMV_WITH_GLVIEW AND EMSCRIPTEN_SYSROOT)
    # CCGLViewImpl-desktop.cpp includes "glfw3.h" without the GLFW/ prefix
    target_include_directories(cocos2d PUBLIC ${EMSCRIPTEN_SYSROOT}/include/GLFW)
endif()

set_target_properties(cocos2d PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

include(${CMAKE_CURRENT_LIST_DIR}/external.cmake)

# --- round-2 fixes -----------------------------------------------------------
# MSVC's STL headers pull in <list> etc. transitively; clang's do not.
target_compile_options(cocos2d PRIVATE "$<$<COMPILE_LANGUAGE:CXX>:SHELL:-include list>")
# Controller group is disabled on Emscripten for now (Controller is an incomplete type).
set_source_files_properties("${COCOS_DIR}/base/CCEventListenerController.cpp" PROPERTIES HEADER_FILE_ONLY TRUE)

# --- round-3: GLView (the desktop GLFW implementation on top of Emscripten's GLFW) ---------------
# GLFW_INCLUDE_NONE: glfw3.h must not pull in the desktop <GL/gl.h> (conflicts with our GLES2 + macros).
target_compile_definitions(cocos2d PUBLIC GLFW_INCLUDE_NONE)
if(PGMMV_WITH_GLVIEW)
    # CCGLViewImpl-desktop.h does #include "glfw3.h" (no GLFW/ prefix)
    find_path(PGMMV_GLFW_INCLUDE glfw3.h
        HINTS "${EMSCRIPTEN_SYSROOT}/include/GLFW" "${EMSCRIPTEN_ROOT_PATH}/cache/sysroot/include/GLFW"
        NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
    message(STATUS "pgmmv: glfw include dir = ${PGMMV_GLFW_INCLUDE}")
    target_include_directories(cocos2d PUBLIC ${PGMMV_GLFW_INCLUDE})
endif()

# --- round-4: pieces of 3d / ui that 2d code needs at link time ---------------------------------
# NavMesh: PGMMV does not use it; ccConfig.h has #ifndef CC_USE_NAVMESH. PUBLIC because Scene's layout depends on it.
target_compile_definitions(cocos2d PUBLIC CC_USE_NAVMESH=0)
# ui module (CCActionProgressTimer.cpp uses ui::LoadingBar). No platform EditBox impl on Emscripten -> drop UIEditBox.
include("${COCOS_DIR}/ui/CMakeLists.txt")
set(_ui_src ${COCOS_UI_SRC})
list(FILTER _ui_src EXCLUDE REGEX "UIEditBox")
# 3d: only what CCCamera.cpp needs (frustum culling)
set(_3d_src 3d/CCPlane.cpp 3d/CCFrustum.cpp 3d/CCAABB.cpp 3d/CCOBB.cpp)
set(_extra ${_ui_src} ${_3d_src})
list(TRANSFORM _extra PREPEND "${COCOS_DIR}/")
list(LENGTH _extra _extra_n)
message(STATUS "pgmmv: round-4 extra sources = ${_extra_n}")
target_sources(cocos2d PRIVATE ${_extra})

# --- round-5: runtime smoke test (no game assets, no scripting) ---------------------------------
# Consumers of cocos2d need the thread + port + GLFW link options too.
target_link_options(cocos2d INTERFACE -pthread -sUSE_GLFW=3 ${PGMMV_PORT_FLAGS})
add_executable(hello_app test/hello_app.cpp)
target_link_libraries(hello_app PRIVATE cocos2d)
# default stack is only 64 KB; the scene-graph recursion needs more
target_link_options(hello_app PRIVATE -sSTACK_SIZE=5242880 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=134217728 -sASSERTIONS=1)
set_target_properties(hello_app PROPERTIES SUFFIX ".html" RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/web")

# --- round-5b: debug aid - log the GL call that raises an error (test/gl_trace.js) ----------------
target_link_options(hello_app PRIVATE "SHELL:--pre-js ${CMAKE_SOURCE_DIR}/test/gl_trace.js")
set_property(TARGET hello_app APPEND PROPERTY LINK_DEPENDS "${CMAKE_SOURCE_DIR}/test/gl_trace.js")

# --- round-5c: client-side vertex arrays (LayerColor etc.) are illegal in WebGL; Emscripten can emulate them ---
target_link_options(hello_app PRIVATE -sFULL_ES2=1 "SHELL:--pre-js ${CMAKE_SOURCE_DIR}/test/js_errors.js")

# --- round-6: A/B test - same program WITHOUT -sFULL_ES2 (FULL_ES2 stays on hello_app only) --------------------
add_executable(hello_nofull test/hello_app.cpp)
target_link_libraries(hello_nofull PRIVATE cocos2d)
target_link_options(hello_nofull PRIVATE -sSTACK_SIZE=5242880 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=134217728 -sASSERTIONS=1
                    "SHELL:--pre-js ${CMAKE_SOURCE_DIR}/test/js_errors.js")
set_target_properties(hello_nofull PROPERTIES SUFFIX ".html" RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/web")
