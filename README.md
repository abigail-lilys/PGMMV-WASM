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


## 输出游戏（Termux 使用指令）

把加密的 PGMMV 游戏包导出成可在浏览器里运行的目录：解密资源、生成 manifest、复制运行时。仅用于你自己合法拥有的游戏。

### 前提（只需一次）

    cd ~/pgmmv-wasm
    source .venv-pgmm-decrypt/bin/activate
    chmod +x pgmmv-output.sh

- `decrypt_project.py`：接受 argv[1] 作为 Resources 路径。
- `decrypt_resources.py`：接受 argv[1] 路径和 `--apply`，递归处理整个 Resources，跳过 `*.before-decrypt*` 和 `*.tmp`。
- `pgmmv-output.sh`：先解密 project.json，再解密资源，manifest 排除备份文件。

### 一条命令输出

    ~/pgmmv-wasm/pgmmv-output.sh <源 Resources 目录> <输出目录> [游戏名]

- 第 1 个参数：源资源目录（要包含 `data/info.json`）。
- 第 2 个参数：输出目录，不存在会自动创建。
- 第 3 个参数（可选）：游戏名，默认取源目录上一级目录名。

脚本依次执行：

1. 复制 Resources 到输出目录。
2. 解密 `data/project.json`。
3. 递归解密所有 `.enc` 文件。
4. 生成 `Resources/manifest.json`，排除 `.bak` 和 `.tmp`。
5. 复制 `index.html`、`build/runtime/pgmmv.js` 和 `pgmmv.wasm`。

### 输出后检查

    OUT=<输出目录>
    find "$OUT/Resources" -name "*.enc" | wc -l
    python3 -c "import json;d=json.load(open('$OUT/Resources/manifest.json'));print('files=',len(d['files']),'total=',d['total'])"
    ls "$OUT"

`.enc` 残留应为 0；输出目录应包含 `index.html`、`Resources`、`runtime`。

### 备份处理（建议）

解密时生成的 `*.before-decrypt*` 不在 manifest 里，但仍占空间，可移到独立目录保留：

    mkdir -p "$OUT/_decrypt_backup"
    find "$OUT/Resources" -name "*.before-decrypt*" -exec mv {} "$OUT/_decrypt_backup/" \;

源目录里的加密原包不会被修改，可随时重跑。

### 启动游戏

    cd <输出目录>
    python3 ~/pgmmv-wasm/serve.py 8000

浏览器打开 `http://127.0.0.1:8000/`。必须通过 `serve.py`：页面要 `fetch('Resources/manifest.json')`，SharedArrayBuffer 需要 COOP/COEP 响应头，用 `file://` 打开会失败，这是浏览器限制。跨设备访问可把 `serve.py` 里的 `("127.0.0.1", PORT)` 改成 `("0.0.0.0", PORT)`。

### 换游戏包

只需更换源路径和输出路径。新包必须有 `data/info.json` 且含 `key` 字段；解密后若仍有 `.enc` 残留，说明 key 不匹配或文件格式有变体。`data/project.json` 如果本来就不是加密的，会被跳过，属正常。

### 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| Permission denied | 脚本没有执行权限 | `chmod +x pgmmv-output.sh` |
| info.json not found | 传入的目录不对 | 传 `.../Resources`，不是游戏根目录 |
| info.json has no 'key' | 该包未加密或格式不同 | 检查 `data/info.json` |
| 启动页卡住 / SharedArrayBuffer is not defined | 没有通过 `serve.py` 启动 | 用 `serve.py` 启动 |
| manifest load failed | 手动去掉了 URL 里的 `?game=` | 直接访问 `http://127.0.0.1:8000/` |
| 进度条不动 | 浏览器阻止 IDBFS | 换 Chrome 或 WebView，看左下角诊断日志 |
