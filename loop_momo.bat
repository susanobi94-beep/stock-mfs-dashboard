@echo off
cd /d "%~dp0"
:StartLoop
echo ==========================================================
echo   LANCEMENT DU CYCLE DE TELECHARGEMENT MOMO (Mode Parallèle)
echo   (Pour arreter, faites Ctrl+C)
echo ==========================================================
echo.
python test_momo_parallel.py

echo.
echo [ATTENTE] Pause de 5 secondes avant le prochain cycle...
timeout /t 5

goto StartLoop
