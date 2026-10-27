# PGMMV Player - WebAssembly 引擎源码 (Main 分支)

本分支包含移植到 WebAssembly 的 PGMMV 引擎与业务层核心源码（基于 cocos2d-x 3.17 + 旧版 SpiderMonkey）。

> 构建配置、CMakeLists、解密脚本及虚拟键盘请查看 `master` 分支。

## 🚀 分阶段移植与避坑指南

### 阶段一：JS 引擎与平台层编译
- **关键点**：SpiderMonkey 34 交叉编译为 wasm32，关闭 JIT；新增 `CC_PLATFORM_EMSCRIPTEN` 平台层。
- **易错点**：
  - 现代浏览器必须开启跨源隔离 (COOP/COEP) 才能使用 `SharedArrayBuffer` 支持 pthread。
  - 必须开启 `-sFULL_ES2=1`，否则 WebGL1 下客户端数组会导致所有 `drawArrays` 报错。
  - 顶点与片段着色器必须统一 `highp` 精度，否则公共 uniform 会导致所有着色器链接失败（黑屏）。

### 阶段二：业务代码兼容性适配
- **关键点**：使用 `-fdelayed-template-parsing` 和 `-fms-extensions` 兼容 MSVC 语法，提供 `msvc_compat.h`。
- **易错点**：
  - `Slope.h:59` 中非 const 左值引用绑定临时对象会导致 clang 报错，需改为 `const Vec2&`。
  - Windows 特有宏 `ARRAYSIZE`、`__declspec` 等需在 shim 头文件中补齐。
  - 注意 `#if 0` 包裹的代码在编译时会被剔除，调试时极易误判。

### 阶段三：运行时稳定性与多线程
- **关键点**：扩容 Worker 池至 40；修复 `AudioEngine` 悬空指针；桩掉 `JavascriptManager::forceGC()`；增加 `getrusage` 桩。
- **易错点**：
  - 场景切换时 `SceneLayer` 并发极高，24 个 Worker 容易耗尽导致死锁。
  - 音频实例销毁后，`std::map::operator[]` 会误插入空指针，必须在所有相关函数中判空。
  - 缺少 JS 绑定时，SpiderMonkey 的强制 GC 会因遍历缺失对象而越界崩溃。

### 阶段四：JS 绑定与输入
- **关键点**：恢复最小化 JS 绑定（`register_all_cocos2dx` 等）；注入前端虚拟键盘。
- **易错点**：
  - 在 C++ 中注册全套 JS 绑定会导致链接缺少大量 UI/3D 符号，应仅保留核心模块。
  - 虚拟键盘派发的 `KeyboardEvent` 中，`keyCode` 是只读的，必须用 `Object.defineProperty` 覆写。

## 🛠️ 编译说明
```bash
# 需先在 master 分支配置好环境
mkdir build && cd build
emcmake cmake ..
emmake make pgmmv_classes -j3
emmake make pgmmv -j3

