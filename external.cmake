# Third-party libraries that have SOURCE in cocos2d/external (compiled here).
# Libraries that are only prebuilt there (png, jpeg, freetype, zlib, sqlite3) come
# from Emscripten ports (PGMMV_PORT_FLAGS). Chipmunk: see the decision record.
function(pgmmv_ext_lib name)
    cmake_parse_arguments(A "" "" "SRC;INC" ${ARGN})
    list(TRANSFORM A_SRC PREPEND "${EXT_DIR}/")
    add_library(ext_${name} STATIC ${A_SRC})
    target_compile_features(ext_${name} PUBLIC cxx_std_14)
    target_compile_options(ext_${name} PRIVATE -pthread ${PGMMV_PORT_FLAGS})
    if(PGMMV_QUIET)
        target_compile_options(ext_${name} PRIVATE -w)
    endif()
    foreach(_d ${A_INC})
        target_include_directories(ext_${name} PUBLIC "${EXT_DIR}/${_d}")
    endforeach()
    target_link_libraries(cocos2d PUBLIC ext_${name})
endfunction()

pgmmv_ext_lib(tinyxml2   SRC tinyxml2/tinyxml2.cpp INC tinyxml2)
pgmmv_ext_lib(unzip      SRC unzip/ioapi.cpp unzip/unzip.cpp unzip/ioapi_mem.cpp INC unzip)
pgmmv_ext_lib(xxhash     SRC xxhash/xxhash.c INC xxhash)
pgmmv_ext_lib(clipper    SRC clipper/clipper.cpp INC clipper)
pgmmv_ext_lib(edtaa3func SRC edtaa3func/edtaa3func.cpp INC edtaa3func)
pgmmv_ext_lib(convertUTF SRC ConvertUTF/ConvertUTF.c ConvertUTF/ConvertUTFWrapper.cpp INC ConvertUTF)
pgmmv_ext_lib(poly2tri   SRC poly2tri/common/shapes.cc poly2tri/sweep/sweep.cc poly2tri/sweep/sweep_context.cc poly2tri/sweep/cdt.cc poly2tri/sweep/advancing_front.cc INC .)
pgmmv_ext_lib(md5        SRC md5/md5.c INC .)

# unzip.cpp tests CC_TARGET_PLATFORM (#AGTK-NX) but includes no config header:
# both macros are undefined -> 0 == 0 -> the empty NX branch is taken. Force the config header.
target_include_directories(ext_unzip PRIVATE ${COCOS_DIR})
target_compile_options(ext_unzip PRIVATE "SHELL:-include platform/CCPlatformConfig.h")

# Chipmunk 7.0.3: cocos ships only headers + native prebuilt libs, so build the upstream sources
# (git clone --branch Chipmunk-7.0.3 https://github.com/slembcke/Chipmunk2D.git ~/ext-src/Chipmunk2D)
# against cocos's own headers (they differ from upstream only by CP_PRIVATE and a cpHastySpace.h include).
set(PGMMV_CHIPMUNK_SRC "$ENV{HOME}/ext-src/Chipmunk2D" CACHE PATH "Chipmunk2D checkout (tag Chipmunk-7.0.3)")
file(GLOB _cp_src "${PGMMV_CHIPMUNK_SRC}/src/*.c")
# cpHastySpace.c needs <sys/sysctl.h> (absent in Emscripten); the multithreaded space
# is excluded for now - revisit only if the link stage asks for cpHastySpace*.
list(FILTER _cp_src EXCLUDE REGEX "cpHastySpace[.]c$")
list(LENGTH _cp_src _cp_n)
message(STATUS "pgmmv: chipmunk ${_cp_n} sources")
add_library(ext_chipmunk STATIC ${_cp_src})
set_target_properties(ext_chipmunk PROPERTIES C_STANDARD 99)
target_include_directories(ext_chipmunk PUBLIC ${EXT_DIR}/chipmunk/include)
target_compile_options(ext_chipmunk PRIVATE -pthread)
if(PGMMV_QUIET)
    target_compile_options(ext_chipmunk PRIVATE -w)
endif()
target_link_libraries(cocos2d PUBLIC ext_chipmunk)
