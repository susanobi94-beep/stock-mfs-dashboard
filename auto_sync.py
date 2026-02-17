import sys
import time
import os
import shutil
import subprocess
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Import modules from current directory
try:
    from transaction_processor import process_file
    from reconcile_data import reconcile_data
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from transaction_processor import process_file
    from reconcile_data import reconcile_data

# --- CONFIGURATION EMAIL (VIA SECRETS) ---
try:
    import secrets_mfs
    SMTP_SERVER = secrets_mfs.SMTP_SERVER
    SMTP_PORT = secrets_mfs.SMTP_PORT
    EMAIL_ADDRESS = secrets_mfs.EMAIL_ADDRESS
    EMAIL_PASSWORD = secrets_mfs.EMAIL_PASSWORD
    EMAIL_CONFIGURED = True
except ImportError:
    print("[ATTENTION] Fichier secrets_mfs.py introuvable. Les emails ne seront pas envoyes.")
    EMAIL_CONFIGURED = False

# --- CONFIGURATION DOSSIERS ---
SOURCE_DIRECTORY = r"E:\MFS DATA\2025\Float Rebalancing Act\Listing_Test_MFS"
DEST_DIRECTORY = r"c:\Users\user\Downloads\r2b\data"
SUMMARY_FILE = r'c:\Users\user\Downloads\r2b\summary.xlsx'
BATCH_SIZE = 100 # Mise a jour en ligne tous les X fichiers
IDLE_TIMEOUT = 180 # 3 minutes sans fichier

def send_email_notification(subject, body):
    """Envoie un email via Gmail"""
    if not EMAIL_CONFIGURED:
        print(f"   [EMAIL SKIP] Pas de configuration : {subject}")
        return

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS

        print(f"   [EMAIL] Tentative d'envoi : {subject}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        print("   [EMAIL] Envoye avec succes !")
    except Exception as e:
        print(f"   [EMAIL] Erreur d'envoi : {e}")

def git_push_updates(count):
    print(f"\n[SAUVEGARDE] Envoi du lot {count} vers Internet...")
    try:
        subprocess.run(["git", "add", "data/*.csv"], check=False)
        subprocess.run(["git", "add", "summary.xlsx"], check=False)
        subprocess.run(["git", "add", "reconciliation.xlsx"], check=False)
        subprocess.run(["git", "add", "history.csv"], check=False)
        subprocess.run(["git", "commit", "-m", f"Auto-sync batch {count}"], check=False)
        subprocess.run(["git", "push", "origin", "master"], check=False)
        subprocess.run(["git", "push", "--force", "hf", "master:main"], check=False)
        print("[SUCCES] Sauvegarde en ligne terminee !")
        
        # Envoi Email
        send_email_notification(
            f"Mise a jour Dashboard MFS - Lot {count}",
            f"Le script a traite {count} fichiers avec succes.\nLes donnees sont a jour sur le Dashboard.\n\nHeure : {datetime.now()}"
        )
        
    except Exception as e:
        print(f"[ERREUR] Echec de l'envoi Git : {e}")
        send_email_notification(
            f"ERREUR Dashboard MFS - Lot {count}",
            f"Echec de la sauvegarde Git.\nErreur : {e}\n\nHeure : {datetime.now()}"
        )

def main():
    print("=== SYNCHRONISATION INTELLIGENTE (CYCLE CONTINU + EMAIL SECURISE) ===")
    print(f"Surveillance de : {SOURCE_DIRECTORY}")
    print(f"Destination : {DEST_DIRECTORY}")
    if EMAIL_CONFIGURED:
        print(f"Email configure : {EMAIL_ADDRESS} (via secrets_mfs.py)")
    else:
        print("Email NON configure (secrets_mfs.py absent)")
    print("------------------------------------------------")

    processed_count = 0
    pending_push = False
    last_activity_time = time.time()

    # 1. Nettoyage initial
    if os.path.exists(DEST_DIRECTORY):
        print("Nettoyage du dossier 'data' local...")
        for f in os.listdir(DEST_DIRECTORY):
            fp = os.path.join(DEST_DIRECTORY, f)
            if os.path.isfile(fp) and fp.endswith('.csv'):
                try:
                    os.remove(fp)
                except Exception:
                    pass
        if os.path.exists(SUMMARY_FILE):
             try:
                 os.remove(SUMMARY_FILE)
             except Exception:
                 pass
        if os.path.exists("reconciliation.xlsx"):
             try:
                 os.remove("reconciliation.xlsx")
                 print("Dashboard remis a zero.")
             except Exception:
                 pass
    else:
        os.makedirs(DEST_DIRECTORY)

    # 2. Boucle de surveillance
    print(f"En attente de fichiers... (Mode Cycle Infini)")
    
    while True:
        try:
            current_time = time.time()
            
            if not os.path.exists(SOURCE_DIRECTORY):
                time.sleep(2)
                continue

            files = [f for f in os.listdir(SOURCE_DIRECTORY) if f.lower().endswith('.csv')]
            
            if files:
                last_activity_time = current_time 
                
                for filename in files:
                    source_path = os.path.join(SOURCE_DIRECTORY, filename)
                    dest_path = os.path.join(DEST_DIRECTORY, filename)
                    
                    try:
                        # Force overwrite
                        if os.path.exists(dest_path):
                            try:
                                os.remove(dest_path)
                            except PermissionError:
                                continue
                        
                        shutil.move(source_path, dest_path)
                        processed_count += 1
                        pending_push = True
                        
                        print(f"\n[{processed_count}] {filename} recu -> Mise a jour...")
                        
                        # Traitement Local
                        process_file(dest_path)
                        reconcile_data() 
                        print("   [LOCAL] Dashboard mis a jour avec nouvelles valeurs.")

                        # Traitement En Ligne (Batch)
                        if processed_count % BATCH_SIZE == 0:
                            print(f"   >>> LOT DE {BATCH_SIZE} ATTEINT ! Push Internet...")
                            git_push_updates(processed_count)
                            pending_push = False
                        
                    except PermissionError:
                        pass
                    except Exception as e:
                        print(f"Erreur sur {filename}: {e}")
            
            else:
                if pending_push and (current_time - last_activity_time > IDLE_TIMEOUT):
                    print(f"\n[AUTO-FIN] Plus de fichiers depuis {IDLE_TIMEOUT}s. Sauvegarde finale...")
                    git_push_updates("FINAL (AUTO-TIMEOUT)")
                    pending_push = False
                    print("--> Vous pouvez fermer ou attendre le cycle suivant.")

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nArret manuel (Ctrl+C). Sauvegarde finale...")
            if pending_push:
                git_push_updates("FINAL (MANUEL)")
            break
        except Exception as global_e:
            print(f"Erreur generale: {global_e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
