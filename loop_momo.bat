@echo off
:StartLoop
echo ==========================================================
echo   LANCEMENT DU CYCLE DE TELECHARGEMENT MOMO
echo   (Pour arreter, faites Ctrl+C)
echo ==========================================================
echo.
python test_momo.py

echo.
echo [ATTENTE] Pause de 5 secondes avant le prochain cycle...
timeout /t 5

goto StartLoop
