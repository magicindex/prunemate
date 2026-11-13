#!/bin/bash
# 构建「纯本机版」安装包：先从主源码生成精简源码，再打包
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/lite-fpk"
TOOL="$ROOT/.tools/fnpack"

echo "==> 生成纯本机版源码"
python3 "$ROOT/scripts/make-lite.py"

rm -rf "$PKG/app/docker/zh/__pycache__"

echo "==> README 随包分发"
cp -f "$PKG/README.md" "$PKG/app/docker/README.md"

echo "==> 校验 fnpack"
[ -x "$TOOL" ] || { echo "缺少 fnpack，先跑 build-fpk.sh"; exit 1; }
"$TOOL" 2>&1 | head -2 || true

echo "==> 打包"
cd "$PKG"
"$TOOL" build

echo
if [ ! -f "$PKG/prunemate-lite.fpk" ]; then
  echo "打包失败：未生成 prunemate-lite.fpk（看上面 fnpack 的输出）" >&2
  exit 1
fi
echo "完成：$PKG/prunemate-lite.fpk"
ls -lh "$PKG/prunemate-lite.fpk"
