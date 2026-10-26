// [wasm-port] WASM has no native DLL plugins. Classes/Manager/DllPluginManager.cpp (compiled as part of
// pgmmv_classes) already defines the ctor, dtor, _dllPluginManager and purge(). Only getInstance() is
// missing, because it lives in DllPluginManager-win32.cpp, which is excluded from the build.
// Pure-JS plugins go through JavascriptManager and are unaffected.
#include "Manager/DllPluginManager.h"

class DllPluginManagerStub : public DllPluginManager {
public:
    DllPluginManagerStub() {}
    virtual ~DllPluginManagerStub() {}
    virtual bool loadPlugins() override { return true; }
    virtual void unloadPlugins() override {}
    virtual void updatePlugins(float) override {}
};

DllPluginManager* DllPluginManager::getInstance() {
    if (!_dllPluginManager) {
        _dllPluginManager = new DllPluginManagerStub();
    }
    return _dllPluginManager;
}
