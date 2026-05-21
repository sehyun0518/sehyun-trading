#!/usr/bin/env bash
# EC2 초기 설정 스크립트 (Amazon Linux 2023 기준)
# 사용법: sudo bash deploy/setup_ec2.sh
set -euo pipefail

REPO_URL="https://github.com/sehyun0518/sehyun-trading.git"
APP_DIR="/opt/sehyun-trading"
APP_USER="trading"

# ── 1. 시스템 패키지 ──────────────────────────────────────────────────────────
echo "[1/9] 시스템 패키지 업데이트"
dnf update -y
dnf install -y git nginx postgresql15-server python3.12 python3.12-pip

# ── 2. PostgreSQL 초기화 ─────────────────────────────────────────────────────
echo "[2/9] PostgreSQL 초기화"
# AL2023은 설치 후 initdb 필요
if [ ! -f /var/lib/pgsql/data/PG_VERSION ]; then
    postgresql-setup --initdb
fi
systemctl enable --now postgresql

# pg_hba.conf — trust → md5 (로컬 패스워드 인증)
PG_HBA=$(find /var/lib/pgsql -name pg_hba.conf 2>/dev/null | head -1)
if grep -q "ident" "$PG_HBA"; then
    sed -i 's/ident/md5/g' "$PG_HBA"
    systemctl restart postgresql
fi

sudo -u postgres psql -c "CREATE USER trading WITH PASSWORD 'trading_pw';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE trading_db OWNER trading;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading;" 2>/dev/null || true

# ── 3. uv 설치 ───────────────────────────────────────────────────────────────
echo "[3/9] uv 설치"
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"
cp /root/.local/bin/uv /usr/local/bin/uv
chmod 755 /usr/local/bin/uv

# ── 4. 앱 유저 생성 ──────────────────────────────────────────────────────────
echo "[4/9] 앱 유저 생성"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/bash -m "$APP_USER"
else
    mkdir -p /home/"$APP_USER" && chown "$APP_USER":"$APP_USER" /home/"$APP_USER"
fi

# ── 5. 소스 클론 ─────────────────────────────────────────────────────────────
echo "[5/9] 소스 클론"
git config --global --add safe.directory "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# ── 6. Python 의존성 설치 ────────────────────────────────────────────────────
echo "[6/9] Python 의존성 설치"
cd "$APP_DIR"
sudo -u "$APP_USER" /usr/local/bin/uv sync --no-dev --python 3.12

# ── 7. .env 파일 ─────────────────────────────────────────────────────────────
echo "[7/9] .env 파일 확인"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "⚠️  $APP_DIR/.env 를 직접 편집하여 실제 값을 채워주세요."
fi
if ! grep -q "^DATABASE_URL" "$APP_DIR/.env"; then
    echo "DATABASE_URL=postgresql://trading:trading_pw@localhost:5432/trading_db" >> "$APP_DIR/.env"
fi
chown "$APP_USER":"$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# ── 8. DB 스키마 초기화 ──────────────────────────────────────────────────────
echo "[8/9] DB 스키마 초기화"
cd "$APP_DIR"
sudo -u "$APP_USER" /usr/local/bin/uv run python scripts/setup_db.py

# ── 9. systemd + nginx ───────────────────────────────────────────────────────
echo "[9/9] systemd + nginx 설정"

# systemd 서비스
cp "$APP_DIR/deploy/sehyun-trading.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sehyun-trading

# nginx — AL2023은 conf.d/ 디렉토리 사용
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/conf.d/sehyun-trading.conf
# 기본 server 블록 비활성화
sed -i 's/^    server {/    #server {/' /etc/nginx/nginx.conf 2>/dev/null || true
nginx -t && systemctl enable --now nginx && systemctl reload nginx

# ── cron 등록 ────────────────────────────────────────────────────────────────
UV="/usr/local/bin/uv"
CRON_CMD="cd $APP_DIR && $UV run python scripts/daily_collect.py >> $APP_DIR/data/cron.log 2>&1"
WEEKLY_CMD="cd $APP_DIR && $UV run python scripts/weekly_report.py >> $APP_DIR/data/cron.log 2>&1"

(crontab -u "$APP_USER" -l 2>/dev/null || true; echo "0 18 * * 1-5 $CRON_CMD") | sort -u | crontab -u "$APP_USER" -
(crontab -u "$APP_USER" -l 2>/dev/null; echo "0 7 * * 1 $WEEKLY_CMD") | sort -u | crontab -u "$APP_USER" -

echo ""
echo "✅ 설정 완료!"
echo "   FastAPI: systemctl status sehyun-trading"
echo "   nginx:   systemctl status nginx"
echo "   로그:    journalctl -u sehyun-trading -f"
echo ""
echo "다음 단계:"
echo "  1. sudo nano $APP_DIR/.env  (API 키 등 실제 값 입력)"
echo "  2. EC2 보안그룹에서 80 포트 오픈"
echo "  3. KIS Developers에서 EC2 공인 IP(3.34.46.20) 등록 (모의투자 앱)"
echo "  4. Vercel 환경변수: VITE_API_URL=http://3.34.46.20/api"
