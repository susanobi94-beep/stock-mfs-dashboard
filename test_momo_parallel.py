import os
import time
import math
import pandas as pd
from playwright.sync_api import sync_playwright
import concurrent.futures

# ================= CONFIGURATION =================
LOGIN_URL = "https://momocare.mtncameroon.net/"
USERNAME_REAL = "Nkoung_R"
PASSWORD_REAL = "Susanoo1994@@Rich20261470"
AUTH_STATE_FILE = "auth.json"
NUM_WORKERS = 3

# FILE PATHS
INPUT_FILE = r"E:/MFS DATA/2025/Float Rebalancing Act/OOS1.xlsx"
OUTPUT_DIR = r"E:/MFS DATA/2025/Float Rebalancing Act/Listing_Test_MFS/"
DEBUG_DIR = os.path.join(OUTPUT_DIR, "debug_screenshots")

# DATE SETTINGS
TARGET_MONTH_OFFSET = 0
START_DAY = "1"
END_DAY = "28"

# =================================================

def ensure_dirs():
    for d in [OUTPUT_DIR, DEBUG_DIR]:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            print(f"Created directory: {d}")

def wait_for_overlays(page, timeout_ms=5000):
    start_time = time.time()
    while (time.time() - start_time) * 1000 < timeout_ms:
        try:
            ok_selectors = [
                "[data-test='information-modal-ok']",
                "button:has-text('OK')",
                "button:has-text('Ok')",
                ".programmatic-eds-dialog button"
            ]
            found_any = False
            for selector in ok_selectors:
                btn = page.locator(selector).first
                if btn.is_visible():
                    btn.click(timeout=1000)
                    found_any = True
                    time.sleep(0.5)
            loader = page.locator(".progress-indicator").first
            if loader.is_visible():
                found_any = True
                time.sleep(0.5)
            else:
                if not found_any:
                    break
        except:
            pass
        time.sleep(0.5)

def read_numbers(file_path):
    print(f"Reading numbers from: {file_path}")
    if not os.path.exists(file_path):
        print(f"Error: Input file '{file_path}' not found.")
        return []
    try:
        df = pd.read_excel(file_path)
        if 'Numero' in df.columns:
            nums = df['Numero'].astype(str).str.strip().tolist()
            # Nettoyage des '.0' pour les nombres lus comme floats
            nums = [n.replace(".0", "") for n in nums if n != 'nan']
            print(f"Found {len(nums)} numbers.")
            return nums
        else:
            print(f"Error: Column 'Numero' not found. Available: {df.columns.tolist()}")
            return []
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return []

def authenticate_and_save_state():
    print("\n--- ETAPE 1: GESTION DE SESSION ---")
    with sync_playwright() as p:
        has_state = os.path.exists(AUTH_STATE_FILE)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=AUTH_STATE_FILE if has_state else None)
        page = context.new_page()
        
        if has_state:
            print("Vérification de la session existante...")
            try:
                page.goto("https://momocare.mtncameroon.net/home", timeout=20000)
                page.wait_for_load_state("networkidle")
                if page.get_by_role("textbox", name="Search for account holder").is_visible():
                    print("✅ Session valide trouvée ! Pas besoin de SMS.")
                    return True
            except Exception as e:
                print("Session expirée. Reconnexion requise.")
        
        print(f"Navigation vers {LOGIN_URL}...")
        page.goto(LOGIN_URL)
        print("Saisie des identifiants...")
        page.locator("[data-test=\"username-input\"]").fill(USERNAME_REAL)
        page.locator("[data-test=\"password-input\"]").fill(PASSWORD_REAL)
        page.locator("[data-test=\"login-button\"]").click()
        
        print("\n⏳ ACTION REQUISE : Veuillez entrer le code SMS (OTP) dans la fenêtre du navigateur.")
        print("⏳ Vous avez 35 secondes...")
        try:
            page.get_by_role("textbox", name="Search for account holder").wait_for(timeout=35000)
            print("✅ Connexion réussie et validée !")
            context.storage_state(path=AUTH_STATE_FILE)
            print(f"🔒 Session sauvegardée dans {AUTH_STATE_FILE}")
            return True
        except Exception as e:
            print("❌ Échec : Tableau de bord non détecté après 35s. Lancez à nouveau le script.")
            return False

def process_chunk(worker_id, numbers_chunk):
    print(f"[Worker {worker_id}] Démarrage avec {len(numbers_chunk)} numéros.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=AUTH_STATE_FILE, accept_downloads=True)
        page = context.new_page()
        
        # Aller à la page d'accueil pour commencer
        page.goto("https://momocare.mtncameroon.net/home")
        
        for index, num in enumerate(numbers_chunk):
            print(f"[Worker {worker_id}] MSISDN {index + 1}/{len(numbers_chunk)} : {num}")
            try:
                wait_for_overlays(page)
                search_box = page.get_by_role("textbox", name="Search for account holder")
                if not search_box.is_visible():
                    page.goto("https://momocare.mtncameroon.net/home")
                    page.wait_for_load_state("networkidle")
                    wait_for_overlays(page)
                    search_box = page.get_by_role("textbox", name="Search for account holder")
                
                search_box.click(force=True)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                search_box.fill(num)
                search_box.press("Enter")
                time.sleep(4)
                
                acc_link = page.locator("[data-test=\"account-link\"]")
                if acc_link.count() > 0:
                    acc_link.first.click()
                elif page.locator("tbody tr").count() > 0:
                    page.locator("tbody tr").first.click()
                else:
                    print(f"[Worker {worker_id}] Aucun résultat pour {num}.")
                    continue
                
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # DATE FILTERS
                try:
                    wait_for_overlays(page)
                    calendars = page.locator(".datepicker .suffix .icon")
                    if calendars.count() >= 2:
                        wait_for_overlays(page)
                        calendars.first.click()
                        time.sleep(1)
                        for _ in range(TARGET_MONTH_OFFSET):
                            wait_for_overlays(page)
                            prev_btn = page.locator(".datepicker:visible .prev")
                            if prev_btn.count() > 0:
                                prev_btn.first.click()
                            else:
                                page.locator(".prev").first.click()
                            time.sleep(0.5)
                        page.get_by_role("cell", name=START_DAY, exact=True).first.click()
                        time.sleep(1)
                        
                        calendars.nth(1).click()
                        time.sleep(1)
                        for _ in range(TARGET_MONTH_OFFSET):
                            wait_for_overlays(page)
                            prev_btn = page.locator(".datepicker:visible .prev")
                            if prev_btn.count() > 0:
                                prev_btn.first.click()
                            else:
                                page.locator(".prev").first.click()
                            time.sleep(0.5)
                        page.get_by_role("cell", name=END_DAY, exact=True).first.click()
                        time.sleep(1)
                        
                        page.get_by_role("button", name="Search").click()
                        time.sleep(6)
                except Exception as de:
                    print(f"[Worker {worker_id}] Erreur date pour {num}: {de}")
                
                # DOWNLOAD
                wait_for_overlays(page)
                export_btn = page.locator("[data-test=\"export-transaction-history-icon\"]")
                try:
                    export_btn.wait_for(state="visible", timeout=8000)
                except:
                    pass
                
                if export_btn.is_visible():
                    try:
                        wait_for_overlays(page)
                        with page.expect_download(timeout=30000) as download_info:
                            export_btn.click()
                        download = download_info.value
                        save_path = os.path.join(OUTPUT_DIR, f"Transactions_{num}.csv")
                        download.save_as(save_path)
                        print(f"[Worker {worker_id}] SUCCESS: {save_path}")
                        
                        try:
                            ok_btn = page.locator("[data-test=\"information-modal-ok\"]")
                            if ok_btn.is_visible(): ok_btn.click(timeout=3000)
                        except:
                            pass
                    except Exception as ednd:
                        print(f"[Worker {worker_id}] Erreur téléchargement pour {num}: {ednd}")
                else:
                    print(f"[Worker {worker_id}] Pas d'export pour {num} (aucune transaction ?).")
            except Exception as outer_e:
                print(f"[Worker {worker_id}] Erreur traitement MSISDN {num}: {outer_e}")
                try:
                    page.goto("https://momocare.mtncameroon.net/home")
                except:
                    pass
        browser.close()
    print(f"[Worker {worker_id}] Travail terminé.")

def run_automation():
    numbers = read_numbers(INPUT_FILE)
    if not numbers: 
        print("Aucun numéro à traiter.")
        return
        
    ensure_dirs()
    
    if not authenticate_and_save_state():
        print("Opération annulée car l'authentification a échoué.")
        return
        
    print("\n--- ETAPE 2: TRAITEMENT PARALLÈLE (3 WORKERS) ---")
    chunk_size = math.ceil(len(numbers) / NUM_WORKERS)
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            if chunk:  # Only submit if chunk is not empty
                futures.append(executor.submit(process_chunk, i + 1, chunk))
        
        concurrent.futures.wait(futures)
        
    print("\n--- PROCESS COMPLETED ---")

if __name__ == "__main__":
    run_automation()
