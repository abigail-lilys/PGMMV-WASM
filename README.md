
# PGMMV WASM

PGMMV Player 的 WebAssembly 移植 —— 构建配置、补丁工具与前端运行环境。

> 引擎与业务源码位于 [PGMMV-src](https://github.com/abigail-lilys/PGMMV-src)（构建请使用 `wasm-mt-fix` 分支）。

## 目录结构

| 路径 | 说明 |
|---|---|
| `CMakeLists.txt` | 核心构建配置：Emscripten 链接选项、资源预加载、文件系统 API 导出、多线程 Worker 池 |
| `patches/` | Python 补丁脚本：死锁、越界、JS 绑定错误等底层修复 |
| `shim/` | 平台兼容垫片：`getrusage_stub.c`、`msvc_compat.h`、`stdafx.h`，填补 Emscripten 与 Windows 的 API 差异 |
| `decrypt_project.py` / `decrypt_resources.py` | PGMMV `.enc` 加密资源解密 |
| `test/pgmmv_main.cpp` | WASM 应用入口 |

## 构建与运行

```bash
# 初始化
cmake -S . -B build -DPGMMV_WITH_GLVIEW=ON -DPGMMV_WITH_CLASSES=ON

# 编译为 WebAssembly
cmake --build build --target pgmmv -j8

# 启动（需支持跨源隔离）
cd build/web && python3 ../../serve.py
```

## 导出游戏

将加密的 PGMMV 游戏包导出为可浏览器运行的目录：解密资源 → 生成 manifest → 复制运行时。

### 一次性准备

```bash
cd ~/pgmmv-wasm
source .venv-pgmm-decrypt/bin/activate
chmod +x pgmmv-output.sh
```

### 一条命令导出

```bash
~/pgmmv-wasm/pgmmv-output.sh <源 Resources 目录> <输出目录> [游戏名]
```

| 参数 | 说明 |
|---|---|
| 第 1 个 | 源资源目录，需包含 `data/info.json` |
| 第 2 个 | 输出目录，不存在会自动创建 |
| 第 3 个（可选） | 游戏名，默认取源目录上一级目录名 |

脚本依次执行：

1. 复制 `Resources` 到输出目录
2. 解密 `data/project.json`
3. 递归解密所有 `.enc` 文件
4. 生成 `Resources/manifest.json`（排除 `.bak` / `.tmp`）
5. 复制 `index.html`、`build/runtime/pgmmv.js`、`pgmmv.wasm`

### 检查输出

```bash
OUT=<输出目录>
find "$OUT/Resources" -name "*.enc" | wc -l          # 应为 0
python3 -c "import json;d=json.load(open('$OUT/Resources/manifest.json'));print('files=',len(d['files']),'total=',d['total'])"
ls "$OUT"                                              # 应包含 index.html、Resources、runtime
```

### 备份清理（可选）

解密产生的 `*.before-decrypt*` 不在 manifest 里，但仍占空间，可统一挪走：

```bash
mkdir -p "$OUT/_decrypt_backup"
find "$OUT/Resources" -name "*.before-decrypt*" -exec mv {} "$OUT/_decrypt_backup/" \;
```

> 源目录的加密原包不会被修改，可随时重跑。

### 启动游戏

```bash
cd <输出目录>
python3 ~/pgmmv-wasm/serve.py 8000
```

浏览器打开 `http://127.0.0.1:8000/`。

> **必须用 `serve.py` 启动**：页面要 `fetch('Resources/manifest.json')`，SharedArrayBuffer 依赖 COOP/COEP 响应头，`file://` 打开会失败。跨设备访问把 `serve.py` 中 `("127.0.0.1", PORT)` 改为 `("0.0.0.0", PORT)`。

### 换游戏包

更换源路径和输出路径即可。要求：

- 新包必须含 `data/info.json` 且带 `key` 字段
- 解密后仍有 `.enc` 残留 → key 不匹配或文件格式有变体
- `data/project.json` 本来未加密 → 会被跳过，属正常

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `Permission denied` | 脚本无执行权限 | `chmod +x pgmmv-output.sh` |
| `info.json not found` | 目录传错 | 传 `.../Resources`，不是游戏根目录 |
| `info.json has no 'key'` | 未加密或格式不同 | 检查 `data/info.json` |
| `SharedArrayBuffer is not defined` | 未通过 `serve.py` 启动 | 用 `serve.py`，不要 `file://` |
| `manifest load failed` | URL 去掉了 `?game=` | 直接访问 `http://127.0.0.1:8000/` |
| 进度条不动 | 浏览器阻止 IDBFS | 换 Chrome / WebView，看左下角诊断日志 |