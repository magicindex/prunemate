#!/bin/bash
# 构建飞牛 fpk 安装包
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FNPACK_VERSION="1.2.3"
FNPACK_URL="https://static2.fnnas.com/fnpack/fnpack-${FNPACK_VERSION}-linux-amd64"
TOOL="$ROOT/.tools/fnpack"

echo "==> 清理历史构建残留（配套已拆分为独立安装包）"
rm -rf "$ROOT/fpk/app/docker/companion"

echo "==> 把 README 放进载荷，随包分发"
mkdir -p "$ROOT/fpk/app/docker"
cp -f "$ROOT/README.md" "$ROOT/fpk/app/docker/README.md"

echo "==> 同步汉化文件到打包工程"
mkdir -p "$ROOT/fpk/app/docker/zh"
cp -f "$ROOT/src/index.html" "$ROOT/src/login.html" "$ROOT/src/prunemate.py" "$ROOT/fpk/app/docker/zh/"

if [ ! -x "$TOOL" ]; then
  echo "==> 下载 fnpack $FNPACK_VERSION"
  mkdir -p "$ROOT/.tools"
  curl -fsSL -o "$TOOL" "$FNPACK_URL"
  chmod +x "$TOOL"
fi

echo "==> 校验 fnpack"
"$TOOL" 2>&1 | head -2 || true   # head 提前关闭管道会让 fnpack 收到 SIGPIPE，配合 pipefail 会中断脚本

echo "==> 打包"
cd "$ROOT/fpk"
"$TOOL" build

echo
echo "完成：$ROOT/fpk/prunemate.fpk"
ls -lh "$ROOT/fpk/prunemate.fpk"
