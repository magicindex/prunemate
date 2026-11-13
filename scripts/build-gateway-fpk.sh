#!/bin/bash
# 构建 PruneMate 网关的飞牛 fpk 安装包（与 prunemate.fpk 相互独立）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FNPACK_VERSION="1.2.3"
FNPACK_URL="https://static2.fnnas.com/fnpack/fnpack-${FNPACK_VERSION}-linux-amd64"
TOOL="$ROOT/.tools/fnpack"
PKG="$ROOT/gateway-fpk"

if [ ! -x "$TOOL" ]; then
  echo "==> 下载 fnpack $FNPACK_VERSION"
  mkdir -p "$ROOT/.tools"
  curl -fsSL -o "$TOOL" "$FNPACK_URL"
  chmod +x "$TOOL"
fi

echo "==> 校验 fnpack"
"$TOOL" 2>&1 | head -2 || true

echo "==> README 随包分发"
cp -f "$PKG/README.md" "$PKG/app/gateway/README.md"

echo "==> 打包网关"
cd "$PKG"
"$TOOL" build

echo
echo "完成：$PKG/prunemate-gateway.fpk"
ls -lh "$PKG/prunemate-gateway.fpk"
