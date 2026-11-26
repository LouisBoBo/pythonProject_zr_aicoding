#!/usr/bin/env bash
# 本机稳定启动前后端：清除代理干扰，固定 5175 / 8009
# 使用 screen 守护，避免 Cursor/终端会话结束导致进程被回收。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.dev-logs"
mkdir -p "$LOG_DIR" "$HOME/.local/bin"

NODE_BIN="$(command -v node || true)"
if [[ -z "$NODE_BIN" && -x "$HOME/.nvm/versions/node/v22.23.1/bin/node" ]]; then
  NODE_BIN="$HOME/.nvm/versions/node/v22.23.1/bin/node"
fi
PY="$ROOT/backend/.venv/bin/python3.12"
if [[ ! -x "$PY" ]]; then
  PY="$ROOT/backend/.venv/bin/python"
fi

# Cursor / 系统代理常导致 Vite 卡住或浏览器访问异常
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy \
  SOCKS_PROXY SOCKS5_PROXY socks_proxy socks5_proxy GIT_HTTP_PROXY GIT_HTTPS_PROXY || true
export NO_PROXY='*'
export no_proxy='*'

echo "==> 停止旧进程 (8009 / 5175 / screen)"
lsof -tiTCP:8009 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -tiTCP:5175 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
pkill -9 -f "$ROOT/frontend/node_modules/.bin/vite" 2>/dev/null || true
screen -S zr-backend -X quit 2>/dev/null || true
screen -S zr-frontend -X quit 2>/dev/null || true
sleep 1

: >"$LOG_DIR/backend.log"
: >"$LOG_DIR/frontend.log"

cat > "$HOME/.local/bin/zr-aicoding-backend.sh" <<EOF
#!/bin/bash
cd "$ROOT/backend" || exit 1
export PATH="$ROOT/backend/.venv/bin:/usr/local/bin:/usr/bin:/bin"
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8009
EOF
cat > "$HOME/.local/bin/zr-aicoding-frontend.sh" <<EOF
#!/bin/bash
cd "$ROOT/frontend" || exit 1
export PATH="$(dirname "$NODE_BIN"):/usr/local/bin:/usr/bin:/bin"
export NO_PROXY='*'
export no_proxy='*'
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
exec "$NODE_BIN" ./node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5175 --strictPort
EOF
chmod +x "$HOME/.local/bin/zr-aicoding-backend.sh" "$HOME/.local/bin/zr-aicoding-frontend.sh"

echo "==> 启动后端 http://127.0.0.1:8009 (screen: zr-backend)"
screen -dmS zr-backend bash -lc "$HOME/.local/bin/zr-aicoding-backend.sh >>'$LOG_DIR/backend.log' 2>&1"
echo "screen:zr-backend" >"$LOG_DIR/backend.pid"

echo "==> 启动前端 http://127.0.0.1:5175 (screen: zr-frontend)"
screen -dmS zr-frontend bash -lc "$HOME/.local/bin/zr-aicoding-frontend.sh >>'$LOG_DIR/frontend.log' 2>&1"
echo "screen:zr-frontend" >"$LOG_DIR/frontend.pid"

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
  screen -ls || true
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
echo "守护会话: screen -ls   （zr-backend / zr-frontend）"
