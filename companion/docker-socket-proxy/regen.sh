#!/bin/sh
# 随时重新生成密钥材料。
#   用法：./regen.sh [certs|token|all]      默认 certs
#   certs —— 换新 CA 与服务端证书（客户端需要重新取 ca.crt）
#   token —— 换新访问令牌（PruneMate 侧要同步更新环境变量）
#   all   —— 两者都换
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
cd "$DIR"

MODE="${1:-certs}"
case "$MODE" in
  token|certs|all) ;;
  *) echo "用法: $0 [certs|token|all]"; exit 1 ;;
esac

if docker compose ps --services --status running 2>/dev/null | grep -qx tls-gateway; then
  echo "==> 在运行中的网关上执行（$MODE）"
  docker compose exec -T tls-gateway python /app/gateway.py "--regen-$MODE"
  echo "==> 重启网关加载新证书/令牌"
  docker compose restart tls-gateway >/dev/null
else
  echo "==> 网关未运行，用一次性容器执行（$MODE）"
  docker compose run --rm tls-gateway python /app/gateway.py "--regen-$MODE"
fi
