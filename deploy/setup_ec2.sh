#!/usr/bin/env bash
# EC2 초기 설정 스크립트 (Ubuntu 22.04 LTS 기준)
# 사용법: sudo bash deploy/setup_ec2.sh
set -euo pipefail

REPO_URL="https://github.com/tew-shkim/sehyun-trading.git"
APP_DIR="/opt/sehyun-trading"
APP_USER="trading"

# ── 1. 시스템 패키지 ──────────────────────────────────────────────────────────
echo "[1/9] 시스템 패키지 업데이트"
apt-get update -y && apt-get upgrade -y
apt-get install -y git curl nginx postgresql postgresql-contrib python3-pip

# ── 2. uv 설치 ───────────────────────────────────────────────────────────────
echo "[2/9] uv 설치"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# ── 3. 앱 유저 생성 ──────────────────────────────────────────────────────────
echo "[3/9] 앱 유저 생성"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$APP_DIR" "$APP_USER"
fi

# ── 4. 소스 클론 ─────────────────────────────────────────────────────────────
echo "[4/9] 소스 클론"
if [ -d "$APP_DIR" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# ── 5. Python 의존성 설치 ────────────────────────────────────────────────────
echo "[5/9] Python 의존성 설치"
cd "$APP_DIR"
sudo -u "$APP_USER" /root/.local/bin/uv sync --no-dev

# ── 6. PostgreSQL 설정 ───────────────────────────────────────────────────────
echo "[6/9] PostgreSQL 설정"
systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE USER trading WITH PASSWORD 'trading_pw';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE trading_db OWNER trading;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading;" 2>/dev/null || true

# ── 7. .env 파일 ─────────────────────────────────────────────────────────────
echo "[7/9] .env 파일 확인"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "⚠️  $APP_DIR/.env 를 직접 편집하여 실제 값을 채워주세요."
fi
# DATABASE_URL이 없으면 추가
if ! grep -q "^DATABASE_URL" "$APP_DIR/.env"; then
    echo "DATABASE_URL=postgresql://trading:trading_pw@localhost:5432/trading_db" >> "$APP_DIR/.env"
fi
chown "$APP_USER":"$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# ── 8. DB 초기화 ─────────────────────────────────────────────────────────────
echo "[8/9] DB 초기화"
cd "$APP_DIR"
sudo -u "$APP_USER" /root/.local/bin/uv run python scripts/setup_db.py

# ── 9. systemd + nginx ───────────────────────────────────────────────────────
echo "[9/9] systemd + nginx 설정"

# systemd 서비스
cp "$APP_DIR/deploy/sehyun-trading.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sehyun-trading

# nginx
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/sehyun-trading
ln -sf /etc/nginx/sites-available/sehyun-trading /etc/nginx/sites-enabled/sehyun-trading
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── cron 등록 ────────────────────────────────────────────────────────────────
CRON_CMD="cd $APP_DIR && /root/.local/bin/uv run python scripts/daily_collect.py >> $APP_DIR/data/cron.log 2>&1"
WEEKLY_CMD="cd $APP_DIR && /root/.local/bin/uv run python scripts/weekly_report.py >> $APP_DIR/data/cron.log 2>&1"

(crontab -u "$APP_USER" -l 2>/dev/null || true; echo "0 18 * * 1-5 $CRON_CMD") | sort -u | crontab -u "$APP_USER" -
(crontab -u "$APP_USER" -l 2>/dev/null; echo "0 7 * * 1 $WEEKLY_CMD") | sort -u | crontab -u "$APP_USER" -

echo ""
echo "✅ 설정 완료!"
echo "   FastAPI: systemctl status sehyun-trading"
echo "   nginx:   systemctl status nginx"
echo "   로그:    journalctl -u sehyun-trading -f"
echo ""
echo "다음 단계:"
echo "  1. $APP_DIR/.env 편집 (API 키 등 실제 값 입력)"
echo "  2. EC2 보안그룹에서 80 포트 오픈"
echo "  3. KIS Developers에서 EC2 공인 IP 등록 (모의투자 앱 설정)"
echo "  4. Vercel에서 VITE_API_URL=http://<EC2-IP>/api 환경변수 설정"
