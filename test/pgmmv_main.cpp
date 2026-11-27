#include "AppDelegate.h"
#include "cocos2d.h"
#include <exception>
#include <emscripten.h>
#include <string>

void my_terminate() {
    std::string msg = "Unhandled C++ Exception (std::terminate called)!";
    auto eptr = std::current_exception();
    if (eptr) {
        try {
            std::rethrow_exception(eptr);
        } catch (const std::exception& e) {
            msg += "\nWhat: ";
            msg += e.what();
        } catch (...) {
            msg += "\nUnknown exception type.";
        }
    }
    EM_ASM({
        var msg = UTF8ToString($0);
        console.error(msg);
        document.body.innerHTML = '<div style="color:red;font-size:20px;padding:20px;white-space:pre-wrap;">' + msg + '</div>';
    }, msg.c_str());
    abort();
}

int main(int argc, char** argv) {
    std::set_terminate(my_terminate);
    try {
        auto app = new AppDelegate();
        cocos2d::Application::getInstance()->run();
    } catch (const std::exception& e) {
        EM_ASM({
            var msg = "C++ Exception in main: " + UTF8ToString($0);
            console.error(msg);
            document.body.innerHTML = '<div style="color:red;font-size:20px;padding:20px;">' + msg + '</div>';
        }, e.what());
    } catch (...) {
        EM_ASM({
            document.body.innerHTML = '<div style="color:red;font-size:20px;padding:20px;">Unknown C++ Exception in main()</div>';
        });
    }
    return 0;
}
