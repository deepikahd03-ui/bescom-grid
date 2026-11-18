#!/usr/bin/env bash
# ============================================================
#  BESCOM GRID - One-click push to GitHub
#  Run:  ./push-to-github.sh
#  It will ask for your repo URL and your personal access
#  token, then push everything.
# ============================================================
set -e
cd "$(dirname "$0")"

echo
echo "  ========================================================"
echo "   BESCOM GRID - Push to GitHub"
echo "  ========================================================"
echo
echo "  Before you continue, make sure you have:"
echo "   1. Created an EMPTY repo on https://github.com/new"
echo "      (NO README, NO .gitignore, NO license)"
echo "   2. Generated a Personal Access Token at"
echo "      https://github.com/settings/tokens  (scope: repo)"
echo
echo "  --------------------------------------------------------"
echo

read -p "Paste your repo URL (e.g. https://github.com/USER/bescom-grid.git): " REPO_URL
[ -z "$REPO_URL" ] && { echo "ERROR: no URL entered."; exit 1; }

read -p "Paste your Personal Access Token (ghp_xxxxx...): " TOKEN
[ -z "$TOKEN" ] && { echo "ERROR: no token entered."; exit 1; }

# Build authenticated URL: https://x-access-token:TOKEN@github.com/...
AUTH_URL="${REPO_URL/https:\/\/github.com/https:\/\/x-access-token:${TOKEN}@github.com}"

echo
echo "  --------------------------------------------------------"
echo "   Working..."
echo "  --------------------------------------------------------"

# Initialize git if needed
if [ ! -d .git ]; then
  echo "  [1/5] git init"
  git init -q
fi

echo "  [2/5] git add -A"
git add -A

echo "  [3/5] git commit"
git commit -q -m "BESCOM Fault-to-Recovery dashboard - backend + frontend integration" 2>/dev/null || \
git commit -q --amend -m "BESCOM Fault-to-Recovery dashboard - backend + frontend integration" 2>/dev/null || true

echo "  [4/5] git branch -M main"
git branch -M main

echo "  [5/5] git push"
git remote remove origin 2>/dev/null || true
git remote add origin "$AUTH_URL"
git push -u origin main

echo
echo "  ========================================================"
echo "   SUCCESS! Your code is on GitHub."
echo "   Visit: $REPO_URL"
echo "  ========================================================"
echo
echo "  Note: your token is stored in git's remote URL for this"
echo "  repo. To remove it later, run:"
echo "     git remote set-url origin $REPO_URL"
