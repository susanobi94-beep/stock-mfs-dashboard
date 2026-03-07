@echo off
echo --- MISE A JOUR DES DONNES MFS ---

cd /d "%~dp0"

echo 1. Execution de la reconciliation...
python reconcile_data.py

echo 2. Preparation de l'envoi Git...
git add history.csv
git add reconciliation.csv
git add dashboard.py
git add transaction_processor.py
git add reconciliation_global.py

echo 3. Enregistrement des modifications...
git commit -m "Auto-update data and history on %date% %time%"

echo 4. Envoi vers GitHub...
git push origin master

echo 5. Envoi vers Hugging Face (si configure)...
git push --force hf master:main

echo --- TERMINE ! ---
pause
