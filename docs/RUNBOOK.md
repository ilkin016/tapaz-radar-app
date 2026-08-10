# tap.az Radar — RUNBOOK (əməliyyat + rollback)

## Gündəlik komandalar

```bash
cd ~/tapaz-radar
python3 run.py                 # tam skan (bütün 5 kateqoriya) + Excel + HTML
python3 run.py --report-only   # DB-dən yalnız dashboard-u yenidən qur (skreyp yox)
python3 run.py --only noutbuklar --cap 50   # tək kateqoriya, ilk 50 (test)
python3 run.py --add <tapaz_kateqoriya_url> # yeni kateqoriya id-si əlavə et
```

## Deploy (əl ilə)

```bash
cd ~/tapaz-radar
# 1) VPS-ə (servis 8090)
scp -i ~/.ssh/tapaz_radar_deploy out/dashboard.html out/tapaz_radar.xlsx \
    root@187.127.91.112:/opt/tapaz-radar/out/
# 2) GitHub Pages-ə
./deploy_github.sh
# (run_daily.sh hər ikisini avtomatik edir)
```

## Status yoxlama

```bash
launchctl list | grep tapaz                    # planlayıcı (status 0 = son run OK)
launchctl list com.tapaz.radar | grep -A3 ProgramArguments   # yüklü yol düzdür?
tail -20 ~/tapaz-radar/logs/*.log              # son run logu
curl -s http://187.127.91.112:8090/ | grep -o '<title>[^<]*</title>'   # VPS canlı?
python3 -c "import sqlite3;print(sqlite3.connect('data/radar.db').execute('select count(*) from listings where active=1').fetchone())"
```

## 🔙 ROLLBACK

### Dashboard geri qaytar (pis deploy)
`out/dashboard.html` regenerasiya olunandır (kod + DB-dən). Geri qaytarmaq üçün:
```bash
cd ~/tapaz-radar
git -C . log --oneline -5 radar/report_html.py   # kod repo (code remote)
git checkout <əvvəlki_commit> -- radar/report_html.py
python3 run.py --report-only     # dashboard yenidən qurulur
./deploy_github.sh && scp -i ~/.ssh/tapaz_radar_deploy out/dashboard.html root@187.127.91.112:/opt/tapaz-radar/out/
```
GitHub Pages tək-commit force-push olduğu üçün Pages tarixçəsindən rollback YOXDUR — mənbə kod repo-dan (github.com/ilkin016/tapaz-radar-app) bərpa et, yenidən qur, yenidən deploy et.

### VPS servis çökübsə
```bash
ssh -i ~/.ssh/tapaz_radar_deploy root@187.127.91.112
systemctl restart tapaz-radar-web.service    # python http.server 8090
systemctl status  tapaz-radar-web.service
ls -la /opt/tapaz-radar/out/index.html       # → dashboard.html symlink olmalıdır
```
⚠️ Port 80 (Caddy) və digər PM2/node xidmətlərinə TOXUNMA. Yalnız 8090.

### Planlayıcı işləmir
```bash
launchctl unload ~/Library/LaunchAgents/com.tapaz.radar.plist
launchctl load   ~/Library/LaunchAgents/com.tapaz.radar.plist   # tərifi yenilə
launchctl start  com.tapaz.radar    # dərhal işə sal (test)
```
Yol dəyişmisənsə plist-i mütləq unload+load et (yüklü tərif fayldan avtomatik yenilənmir).

### DB korlanıbsa
`data/radar.db` `.gitignore`-dadır (backup git-də yox). `seen` cədvəli itsə "yeni" tarixçəsi sıfırlanır (növbəti run hər şeyi "yeni" sayar — bir dəfəlik). Kritik data deyil, yenidən qurula bilər.

## Cloudflare 403 alsan
- **Mac-də** 403 → müvəqqəti Cloudflare challenge, backoff artıq var; bir azdan yenidən cəhd et.
- **VPS-də** 403 → NORMALDIR, VPS scrape etməməlidir (datacenter IP bloklu). VPS yalnız servis edir.
