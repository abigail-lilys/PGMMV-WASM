// [wasm-port] Provide the vtable/typeinfo for cocos2d::Controller on Emscripten.
// The ctor/dtor live in CCController-android.cpp / CCController-linux-win32.cpp, which need Android JNI
// and Linux input.h / DirectInput respectively. jsb_cocos2dx_auto.cpp only needs typeid(Controller);
// other Controller members are already implemented in CCController.cpp.
#include "base/CCController.h"

namespace cocos2d {
Controller::Controller() : _impl(nullptr) {}
Controller::~Controller() {}
}
