#!/bin/bash
# tap.az Radar — gündəlik avtomatik skan (launchd/cron tərəfindən çağırılır).
# Bütün aktiv kateqoriyaları skan edir, yalnız yeni elanları əlavə edir, dashboard-u yeniləyir.
cd "$(dirname "$0")" || exit 1
mkdir -p logs
TS="$(date +%Y-%m-%d_%H%M%S)"
PY="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
echo "=== RUN $TS ===" >> logs/daily.log
"$PY" run.py >> "logs/run_$TS.log" 2>&1
code=$?
echo "run bitdi (exit $code) → logs/run_$TS.log" >> logs/daily.log
# GitHub Pages-ə deploy (uğurlu run-dan sonra)
if [ $code -eq 0 ] && [ -x ./deploy_github.sh ]; then
  ./deploy_github.sh >> logs/daily.log 2>&1
fi
# köhnə logları təmizlə (30 gündən köhnə)
find logs -name 'run_*.log' -mtime +30 -delete 2>/dev/null
exit $code
