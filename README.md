# PGMMV WASM 构建工具与运行环境 (Master 分支)

本仓库是 PGMMV Player WebAssembly 移植工程的构建配置、补丁工具与前端运行环境。
> 游戏引擎与业务源码请查看主仓库的 main 分支。

## 📁 核心目录结构

- `CMakeLists.txt`：核心构建配置，包含 Emscripten 链接选项（预加载资源、强制导出文件系统 API、扩容多线程 Worker 池等）。
- `patches/`：纯 Python 编写的补丁脚本，记录了解决死锁、越界、JS 绑定报错等所有底层问题的修复方案。
- `shim/`：平台兼容垫片，如 `getrusage_stub.c`、`msvc_compat.h`，填补 Emscripten 与 Windows 之间的 API 差异。
- `decrypt_project.py` / `decrypt_resources.py`：PGMMV 专属的 `enc` 加密资源解密工具。
- `test/pgmmv_main.cpp`：WASM 应用启动入口。
- `build/web/virtual_keyboard.js`：前端移动端虚拟键盘与调试日志重定向模块。

## 🛠️ 构建与运行

```bash
# 1. 初始化 CMake
cmake -S . -B build -DPGMMV_WITH_GLVIEW=ON -DPGMMV_WITH_CLASSES=ON

# 2. 编译为 WebAssembly
cmake --build build --target pgmmv -j3

# 3. 启动本地服务器（需支持跨源隔离）
cd build/web && python3 ../../serve.py
```

## 🚀 帧率 (FPS) 优化指南 (Master 侧)

游戏帧率低通常由主线程阻塞或低效编译引起。本仓库包含以下关键优化：

1. **前端日志拦截 (`build/web/virtual_keyboard.js`)**
   - **问题**：游戏内的 `console.log`（如满屏的音频报错）会导致浏览器 DOM 疯狂重排，主线程严重卡顿。
   - **优化**：在虚拟键盘脚本顶部直接重写 `console.log = function() {};`，彻底丢弃前端日志输出。
2. **分模块编译优化 (`CMakeLists.txt`)**
   - **问题**：开启全局 `-O2` 虽然能提升 C++ 代码速度，但会导致旧版 SpiderMonkey (mozjs-34) 在初始化时发生死锁。
   - **优化**：在 `CMakeLists.txt` 末尾追加 `WASM_MODULAR_O1` 补丁，**仅对 `pgmmv_classes` 和 `cocos2d` 开启 `-O1` 优化**，让 JS 引擎保持 `-O0` 稳定运行。
3. **同步日志剥离**
   - 正式发布时，必须移除 `<script src="dbg_hook6.js">` 等依赖同步 XHR 的调试脚本，避免主线程等待网络。
