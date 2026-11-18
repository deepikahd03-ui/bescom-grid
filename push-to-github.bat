@echo off
REM ============================================================
REM  BESCOM GRID - One-click push to GitHub
REM  Double-click this file. It will ask for your repo URL and
REM  your personal access token, then push everything.
REM ============================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo  ========================================================
echo   BESCOM GRID - Push to GitHub
echo  ========================================================
echo.
echo  Before you continue, make sure you have:
echo   1. Created an EMPTY repo on https://github.com/new
echo      (NO README, NO .gitignore, NO license)
echo   2. Generated a Personal Access Token at
echo      https://github.com/settings/tokens  ^(scope: repo^)
echo.
echo  --------------------------------------------------------
echo.

set /p REPO_URL="Paste your repo URL (e.g. https://github.com/USER/bescom-grid.git): "
if "%REPO_URL%"=="" (
  echo  ERROR: no URL entered.
  pause
  exit /b 1
)

set /p TOKEN="Paste your Personal Access Token (ghp_xxxxx...): "
if "%TOKEN%"=="" (
  echo  ERROR: no token entered.
  pause
  exit /b 1
)

REM Build authenticated URL: https://x-access-token:TOKEN@github.com/USER/REPO.git
REM Replace https://github.com with https://x-access-token:TOKEN@github.com
set AUTH_URL=%REPO_URL%
set AUTH_URL=!AUTH_URL:https://github.com=https://x-access-token:%TOKEN%@github.com!

echo.
echo  --------------------------------------------------------
echo   Working...
echo  --------------------------------------------------------

REM Initialize git if needed
if not exist .git (
  echo  [1/5] git init
  git init -q
)

echo  [2/5] git add -A
git add -A

echo  [3/5] git commit
git commit -q -m "BESCOM Fault-to-Recovery dashboard - backend + frontend integration" 2>nul
if errorlevel 1 (
  git commit -q --amend -m "BESCOM Fault-to-Recovery dashboard - backend + frontend integration" 2>nul
)

echo  [4/5] git branch -M main
git branch -M main

echo  [5/5] git push
git remote remove origin 2>nul
git remote add origin "%AUTH_URL%"
git push -u origin main

if errorlevel 1 (
  echo.
  echo  ========================================================
  echo   PUSH FAILED.
  echo   Common causes:
  echo    - Token doesn't have 'repo' scope
  echo    - Repo URL is wrong / repo doesn't exist
  echo    - Repo is not empty (has a README) - delete it on
  echo      GitHub and recreate empty
  echo  ========================================================
  pause
  exit /b 1
)

echo.
echo  ========================================================
echo   SUCCESS! Your code is on GitHub.
echo   Visit: %REPO_URL%
echo  ========================================================
echo.
echo  Note: your token is stored in git's remote URL for this
echo  repo. To remove it later, run:
echo     git remote set-url origin %REPO_URL%
echo.
pause
