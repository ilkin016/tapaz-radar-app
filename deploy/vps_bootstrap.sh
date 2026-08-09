#!/bin/bash
# tap.az Radar — VPS bootstrap (Ubuntu 24.04). Root ilə: curl -fsSL <raw> | bash
set -e
echo "=== tapaz-radar bootstrap $(date) ==="

# 1) SSH açarı (izləmə üçün)
mkdir -p /root/.ssh && chmod 700 /root/.ssh
curl -fsSL "https://gist.githubusercontent.com/ilkin016/7c322fad108eef2e89a298a2fdcf4563/raw/tapaz_radar_deploy.pub" >> /root/.ssh/authorized_keys || true
sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
echo "[1/5] SSH açarı əlavə olundu"

# 2) Paketlər
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -q
apt-get install -y -q python3 python3-openpyxl nginx git
echo "[2/5] paketlər quraşdırıldı"

# 3) Kod
rm -rf /opt/tapaz-radar
git clone -q https://github.com/ilkin016/tapaz-radar-app /opt/tapaz-radar
cd /opt/tapaz-radar
mkdir -p out logs data
printf '<!doctype html><meta charset=utf-8><body style="font-family:sans-serif;padding:40px"><h2>tap.az Radar</h2><p>İlk skan gedir — dashboard hazırlanır (~30-40 dəq). Bu səhifəni sonra yenilə.</p></body>' > out/dashboard.html
echo "[3/5] kod hazır: /opt/tapaz-radar"

# 4) nginx
cp deploy/vps/nginx-tapaz-radar.conf /etc/nginx/sites-available/tapaz-radar
sed -i 's/server_name .*/server_name _;/' /etc/nginx/sites-available/tapaz-radar
ln -sf /etc/nginx/sites-available/tapaz-radar /etc/nginx/sites-enabled/tapaz-radar
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "[4/5] nginx yayımlayır (port 80)"

# 5) systemd timer (gündəlik) + ilk seed (fonda)
sed -i 's/^User=radar/#User=radar/' deploy/vps/tapaz-radar.service
cp deploy/vps/tapaz-radar.service /etc/systemd/system/
cp deploy/vps/tapaz-radar.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now tapaz-radar.timer
nohup python3 run.py > logs/seed.log 2>&1 &
echo "[5/5] gündəlik timer aktiv · ilk seed başladı (PID $!)"
echo "=== BOOTSTRAP DONE — http://SERVER_IP/ (seed bitəndə dashboard hazır olar) ==="
