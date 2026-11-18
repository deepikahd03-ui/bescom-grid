#!/usr/bin/env bash
# ============================================================
#  BESCOM Fault-to-Recovery - Mac/Linux one-click starter
#  Run:  ./start.sh    (or double-click in a file manager that
#                       supports it; otherwise run from Terminal)
# ============================================================
set -e
cd "$(dirname "$0")"

echo
echo " [1/4] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo " ERROR: python3 is not installed."
  echo "   Mac:     brew install python3   (or install from python.org)"
  echo "   Ubuntu:  sudo apt install python3 python3-venv"
  echo
  exit 1
fi

echo
echo " [2/4] Setting up virtual environment (first run only)..."
[ -d venv ] || python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

echo
echo " [3/4] Installing dependencies (first run only)..."
pip install -q -r requirements.txt

echo
echo " [4/4] Starting BESCOM dashboard..."
echo " --------------------------------------------------------"
echo "  Open in browser:  http://localhost:5000"
echo "  Login:            admin@bescom.sim  /  demo123"
echo "  (any email + 3+ char password works)"
echo " --------------------------------------------------------"
echo "  Press Ctrl+C in this window to stop the server."
echo

python3 app.py
