@echo off
title AUTO-SYNC DASHBOARD (MFS)
cd /d "%~dp0"

echo ==============================================================
echo   CONTROLEUR AUTOMATIQUE - MODE TEMPS REEL
echo ==============================================================
echo.
echo 1. Ce script surveille le dossier de telechargement.
echo 2. Des qu'un nouveau fichier listing arrive, il est capture.
echo 3. Le dashboard est mis a jour immediatement.
echo.
echo [INFO] En attente de : E:\MFS DATA\2025\Float Rebalancing Act\Listing_Test_MFS
echo.

python auto_sync.py

pause
