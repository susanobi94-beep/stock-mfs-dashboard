@echo off
setlocal

:: --- 1. CONFIGURATION DU DOSSIER SOURCE (A modifier selon le mois) ---
set "SOURCE_DIR=E:\MFS DATA\2025\Float Rebalancing Act\Listing_Test_MFS"

:: --- 2. CONFIGURATION DU DOSSIER DE DESTINATION (r2b/data) ---
set "DEST_DIR=%~dp0data"

echo ========================================================
echo   AUTOMATISATION COMPLETE : IMPORT + CALCUL + MISE A JOUR
echo ========================================================
echo.

:: --- ETAPE A : VERIFICATION DU DOSSIER SOURCE ---
if not exist "%SOURCE_DIR%" (
    echo [ERREUR] Le dossier source "%SOURCE_DIR%" n'existe pas !
    echo Verifiez que le script de telechargement a bien termine.
    pause
    exit /b
)

:: --- ETAPE B : NETTOYAGE DU DOSSIER LOCAL (r2b/data) ---
echo [1/5] Nettoyage du dossier local r2b/data...
if exist "%DEST_DIR%" (
    del /q "%DEST_DIR%\*.csv"
) else (
    mkdir "%DEST_DIR%"
)

:: --- ETAPE C : DEPLACEMENT DES FICHIERS ---
echo [2/5] Importation des nouveaux fichiers depuis le disque D:...
move /y "%SOURCE_DIR%\*.csv" "%DEST_DIR%\"
if %errorlevel% neq 0 (
    echo [ERREUR] Aucun fichier CSV trouve ou erreur de deplacement.
    pause
    exit /b
)

:: --- ETAPE D : TRAITEMENT ET RECONCILIATION ---
echo.
echo [3/5] Traitement des transactions (Extraction des Noms)...
python transaction_processor.py

echo.
echo [4/5] Reconciliation des donnees (Mise a jour Dashboard)...
python reconcile_data.py

:: --- ETAPE E : SAUVEGARDE ET ENVOI SUR INTERNET ---
echo.
echo [5/5] Envoi vers GitHub et Hugging Face...
git add data/*.csv
git add summary.xlsx
git add reconciliation.xlsx
git add history.csv
git commit -m "Auto-import %date% %time%"
git push origin master
git push hf master:main

echo.
echo ========================================================
echo            TOUT EST TERMINE AVEC SUCCES !  
echo ========================================================
pause
