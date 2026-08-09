# VPS-də tap.az Radar quraşdırma (Ubuntu/Debian)

Layihə portativdir — Mac-dəki `tapaz-radar/` qovluğunu olduğu kimi VPS-ə köçür.

## 1. Layihəni köçür
```bash
# lokal Mac-də:
rsync -av --exclude out/ --exclude 'logs/*' ~/Desktop/tapaz-radar/ user@VPS_IP:/opt/tapaz-radar/
# (və ya git repo ilə)
```

## 2. Asılılıqlar
```bash
sudo apt update && sudo apt install -y python3 python3-pip nginx
pip3 install openpyxl          # yalnız Excel hesabatı üçün lazımdır
sudo useradd -r -s /usr/sbin/nologin radar 2>/dev/null || true
sudo chown -R radar:radar /opt/tapaz-radar
```

## 3. İlk seed (bir dəfəlik, uzun çəkir)
```bash
cd /opt/tapaz-radar && sudo -u radar python3 run.py
```

## 4. Gündəlik avtomatik skan (systemd timer)
```bash
sudo cp deploy/vps/tapaz-radar.service /etc/systemd/system/
sudo cp deploy/vps/tapaz-radar.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tapaz-radar.timer
systemctl list-timers | grep tapaz     # yoxla
sudo systemctl start tapaz-radar.service  # əl ilə test
```

## 5. Nginx ilə yayımla
```bash
sudo cp deploy/vps/nginx-tapaz-radar.conf /etc/nginx/sites-available/tapaz-radar
sudo ln -s /etc/nginx/sites-available/tapaz-radar /etc/nginx/sites-enabled/
# conf-da server_name-i öz domeninə/IP-yə dəyiş
sudo nginx -t && sudo systemctl reload nginx
```
Dashboard: `http://VPS_IP/` (və ya domenin).

## 6. Opsional — şifrə ilə qoru (telefon nömrələri var)
`nginx-tapaz-radar.conf` içindəki `auth_basic` sətirlərini aç:
```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd ilkin
sudo systemctl reload nginx
```

## 7. HTTPS (Let's Encrypt, pulsuz)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d radar.senin-domenin.az
```

---
**Qeyd:** GitHub Pages onsuz da lokal `run_daily.sh`-dən avtomatik yenilənir. VPS müstəqil işləyir — istəsən hər ikisini paralel saxlaya bilərsən (VPS 7/24 işlədiyi üçün daha etibarlıdır).
