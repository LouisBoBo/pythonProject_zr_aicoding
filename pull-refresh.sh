#!/usr/bin/env bash
# 一键：拉取最新代码并重启前后端
# 用法：./pull-refresh.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

BRANCH="${BRANCH:-hebo}"
BACKEND_PORT="${BACKEND_PORT:-8009}"
FRONTEND_PORT="${FRONTEND_PORT:-5175}"
PORT_FILES=(backend/app/main.py frontend/vite.config.js)

# 规避本机代理 / HTTP2 导致的 GitHub 拉取失败
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy || true
GIT=(git -c http.version=HTTP/1.1)

echo "==> 当前分支: $(git branch --show-current)"
echo "==> 目标远程: origin/$BRANCH"

# 暂存本地端口改动，避免 pull 冲突
STASHED=0
if ! git diff --quiet -- "${PORT_FILES[@]}" 2>/dev/null; then
  git stash push -m "pull-refresh: local ports ${BACKEND_PORT}/${FRONTEND_PORT}" -- "${PORT_FILES[@]}"
  STASHED=1
fi

echo "==> 拉取代码..."
if ! "${GIT[@]}" fetch origin "$BRANCH"; then
  echo "首次 fetch 失败，重试一次..."
  sleep 2
  if ! "${GIT[@]}" fetch origin "$BRANCH"; then
    echo "拉取失败，恢复本地端口改动后退出"
    if [[ "$STASHED" -eq 1 ]]; then
      git stash pop || true
    fi
    exit 1
  fi
fi
"${GIT[@]}" merge --ff-only "origin/$BRANCH"

if [[ "$STASHED" -eq 1 ]]; then
  git stash pop || {
    echo "警告: stash pop 有冲突，请手动处理端口配置"
  }
fi

# 恢复本地端口（若远程覆盖了配置）
if [[ -f frontend/vite.config.js ]]; then
  sed -i '' "s|port: [0-9]*|port: ${FRONTEND_PORT}|" frontend/vite.config.js
  sed -i '' "s|target: 'http://127.0.0.1:[0-9]*'|target: 'http://127.0.0.1:${BACKEND_PORT}'|" frontend/vite.config.js
fi
if [[ -f backend/app/main.py ]]; then
  sed -i '' \
    "s|allow_origins=\[.*\]|allow_origins=[\"http://localhost:${FRONTEND_PORT}\", \"http://127.0.0.1:${FRONTEND_PORT}\"]|" \
    backend/app/main.py
fi

# package.json 有变更时安装依赖
changed_files="$(git diff --name-only "HEAD@{1}" HEAD 2>/dev/null || true)"
if echo "$changed_files" | grep -q 'frontend/package.json'; then
  echo "==> 安装前端依赖..."
  (cd frontend && npm install)
fi
if echo "$changed_files" | grep -q 'backend/requirements.txt'; then
  echo "==> 安装后端依赖..."
  (
    # shellcheck disable=SC1091
    source backend/.venv/bin/activate
    pip install -r backend/requirements.txt -q
  )
fi

echo "==> 重启服务 (${BACKEND_PORT} / ${FRONTEND_PORT})..."
lsof -tiTCP:"$BACKEND_PORT" -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -tiTCP:"$FRONTEND_PORT" -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

LOG_DIR="$ROOT/.dev-logs"
mkdir -p "$LOG_DIR"

(
  cd backend
  # shellcheck disable=SC1091
  source .venv/bin/activate
  nohup uvicorn app.main:app --reload --port "$BACKEND_PORT" --host 127.0.0.1 \
    >"$LOG_DIR/backend.log" 2>&1 &
  echo $! >"$LOG_DIR/backend.pid"
)

(
  cd frontend
  nohup npm run dev >"$LOG_DIR/frontend.log" 2>&1 &
  echo $! >"$LOG_DIR/frontend.pid"
)

# 等待就绪
for i in {1..30}; do
  if curl -sf "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1 \
    && curl -sf "http://localhost:${FRONTEND_PORT}/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo
echo "完成: $(git log -1 --oneline)"
echo "后端: http://127.0.0.1:${BACKEND_PORT}"
echo "前端: http://localhost:${FRONTEND_PORT}"
echo "日志: $LOG_DIR/"
curl -s "http://127.0.0.1:${BACKEND_PORT}/api/health" && echo
curl -s -o /dev/null -w "frontend HTTP %{http_code}\n" "http://localhost:${FRONTEND_PORT}/"
