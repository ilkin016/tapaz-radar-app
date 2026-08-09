#!/bin/bash
# Dashboard-u GitHub Pages-ə push edir (gündəlik run-dan sonra çağırılır).
# Tək commit saxlayır (amend + force) — repo şişmir.
cd "$(dirname "$0")" || exit 1
cp out/dashboard.html deploy/site/index.html || exit 1
cd deploy/site || exit 1
git add -A
if git rev-parse HEAD >/dev/null 2>&1; then
  git commit --amend -q -m "dashboard update $(date +%Y-%m-%d)" || true
else
  git commit -q -m "dashboard update"
fi
git push --force -q origin main && echo "✓ GitHub Pages yeniləndi: https://ilkin016.github.io/tapaz-radar/"
