#include "AppDelegate.h"
#include "cocos2d.h"

int main(int argc, char** argv) {
    auto app = new AppDelegate();
    cocos2d::Application::getInstance()->run();
    return 0;
}
