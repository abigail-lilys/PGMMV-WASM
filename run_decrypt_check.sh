#!/data/data/com.termux/files/usr/bin/bash

set -o pipefail

LOG="/storage/emulated/0/Download/PGMMV-解密验证.txt"
VENV="$HOME/pgmmv-wasm/.venv-pgmm-decrypt"

{
    set -e

    echo "===== 1. 安装编译依赖 ====="
    pkg install -y git clang make python

    echo
    echo "===== 2. 创建独立 Python 环境 ====="
    python -m venv "$VENV"

    echo
    echo "===== 3. 安装 PGMMV 解密库 ====="
    "$VENV/bin/python" -m pip install \
        git+https://github.com/blluv/pgmm_decrypt.git

    echo
    echo "===== 4. 检查 API 导入 ====="
    "$VENV/bin/python" -c \
      'from pgmm_decrypt import decrypt_pgmm_key, decrypt_pgmm_resource; print("DECRYPT_API_IMPORT_OK")'

    echo
    echo "===== 5. 检查并尝试解密 project.json ====="
    "$VENV/bin/python" "$HOME/pgmmv-wasm/decrypt_project.py"

    echo
    echo "===== 6. 检查最终文件 ====="
    head -c 16 "$HOME/pgmmv-wasm/test_game/Resources/data/project.json"
    echo
    echo "===== 执行结束 ====="

} 2>&1 | tee "$LOG"

RESULT=${PIPESTATUS[0]}
echo "诊断结果：$RESULT"
echo "完整日志：$LOG"
exit "$RESULT"
