#!/usr/bin/env bash
# 本机稳定启动前后端：清除代理干扰，固定 5175 / 8009
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.dev-logs"
mkdir -p "$LOG_DIR"

# Cursor / 系统代理常导致 Vite 卡住或浏览器访问异常
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy \
  SOCKS_PROXY SOCKS5_PROXY socks_proxy socks5_proxy GIT_HTTP_PROXY GIT_HTTPS_PROXY || true
export NO_PROXY='*'
export no_proxy='*'

echo "==> 停止旧进程 (8009 / 5175)"
lsof -tiTCP:8009 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -tiTCP:5175 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
pkill -9 -f "$ROOT/frontend/node_modules/.bin/vite" 2>/dev/null || true
sleep 1

: >"$LOG_DIR/backend.log"
: >"$LOG_DIR/frontend.log"

echo "==> 启动后端 http://127.0.0.1:8009"
(
  cd "$ROOT/backend"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  # 不用 --reload，避免 WatchFiles 卡死；本机开发改代码后重新跑本脚本即可
  nohup uvicorn app.main:app --host 127.0.0.1 --port 8009 \
    >>"$LOG_DIR/backend.log" 2>&1 &
  echo $! >"$LOG_DIR/backend.pid"
)

echo "==> 启动前端 http://127.0.0.1:5175"
(
  cd "$ROOT/frontend"
  nohup env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
    NO_PROXY='*' no_proxy='*' \
    ./node_modules/.bin/vite --host 0.0.0.0 --port 5175 --strictPort \
    >>"$LOG_DIR/frontend.log" 2>&1 &
  echo $! >"$LOG_DIR/frontend.pid"
)

echo "==> 等待就绪（后端首次种子数据可能较慢）"
ok=0
for _ in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:8009/api/health" >/dev/null 2>&1 \
    && curl -sf "http://127.0.0.1:5175/" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 1
done

echo
if [[ "$ok" -eq 1 ]]; then
  echo "启动成功"
else
  echo "启动超时，请查看日志: $LOG_DIR/"
  tail -n 40 "$LOG_DIR/frontend.log" 2>/dev/null || true
  tail -n 40 "$LOG_DIR/backend.log" 2>/dev/null || true
  exit 1
fi

curl -s "http://127.0.0.1:8009/api/health"; echo
curl -s -o /dev/null -w "frontend HTTP %{http_code}\n" "http://127.0.0.1:5175/"
echo
echo "请用浏览器打开（建议 Chrome 无痕，并关闭对本机的代理）："
echo "  http://127.0.0.1:5175/"
echo "  http://localhost:5175/"
echo "接口文档: http://127.0.0.1:8009/docs"
echo "账号: admin / admin123"
