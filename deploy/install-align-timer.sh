#!/usr/bin/env bash
# 在服务器上安装「每天 08:00 对齐今日业务数据」的 systemd timer。
# 用法（在仓库根或任意目录）：
#   sudo bash deploy/install-align-timer.sh
#   sudo bash deploy/install-align-timer.sh /www/wwwroot/zr-aicoding
set -euo pipefail

APP_ROOT="${1:-/www/wwwroot/zr-aicoding}"
UNIT_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/systemd"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请使用 root 执行：sudo bash $0 ${APP_ROOT}"
  exit 1
fi

if [[ ! -d "$APP_ROOT/backend" ]]; then
  echo "未找到 $APP_ROOT/backend，请确认部署路径"
  exit 1
fi

if [[ ! -f "$APP_ROOT/backend/scripts/align_today_business_data.py" ]]; then
  echo "未找到对齐脚本，请先把最新 backend 同步到服务器"
  exit 1
fi

mkdir -p /var/log/zr-aicoding
install -m 644 "$SRC_DIR/zr-aicoding-align-today.service" "$UNIT_DIR/zr-aicoding-align-today.service"
install -m 644 "$SRC_DIR/zr-aicoding-align-today.timer" "$UNIT_DIR/zr-aicoding-align-today.timer"

# 若 APP_ROOT 不是默认路径，替换 unit 中的路径
if [[ "$APP_ROOT" != "/www/wwwroot/zr-aicoding" ]]; then
  sed -i "s|/www/wwwroot/zr-aicoding|${APP_ROOT}|g" \
    "$UNIT_DIR/zr-aicoding-align-today.service"
fi

systemctl daemon-reload
systemctl enable --now zr-aicoding-align-today.timer

echo
echo "已安装并启用 timer："
systemctl list-timers --all | grep -E 'zr-aicoding-align-today|NEXT' || true
echo
echo "立即试跑一次："
echo "  systemctl start zr-aicoding-align-today.service"
echo "  journalctl -u zr-aicoding-align-today.service -n 50 --no-pager"
echo
echo "查看下次触发："
echo "  systemctl list-timers zr-aicoding-align-today.timer"
