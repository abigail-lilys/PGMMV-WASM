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
