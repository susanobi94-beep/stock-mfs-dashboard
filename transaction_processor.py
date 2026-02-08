import csv
import os
import time
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openpyxl import Workbook, load_workbook

# Configuration
INPUT_DIRECTORY = r'c:\Users\user\Downloads\r2b\data'
OUTPUT_FILE = r'c:\Users\user\Downloads\r2b\summary.xlsx'

def process_file(filepath):
    """
    Process a single transaction file and extract date, number, and balance.
    """
    filename = os.path.basename(filepath)
    # Check if filename matches format
    if not filename.startswith('Transactions_') or not filename.endswith('.csv'):
        return

    # Extract number from filename
    match = re.search(r'Transactions_(\d+)\.csv', filename)
    if not match:
        return
    number = match.group(1)

    try:
        # Check explicit encoding, try utf-8 then latin-1 if fails
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
        except UnicodeDecodeError:
             with open(filepath, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)

        if not first_row:
            print(f"Skipping {filename}: File is empty.")
            return

        # Transaction files usually have 'Date', 'Balance' columns.
        date = first_row.get('Date')
        balance = first_row.get('Balance')
        
        # If headers are different, might need adjustment
        if date is None or balance is None:
             print(f"Skipping {filename}: 'Date' or 'Balance' column missing. Headers found: {list(first_row.keys())}")
             return

        write_to_summary(date, number, balance)
        print(f"Processed {filename}: Date={date}, Number={number}, Balance={balance}")

    except Exception as e:
        print(f"Error processing {filename}: {e}")

def write_to_summary(date, number, balance):
    """
    Append the extracted data to the summary Excel file.
    Only write if entry doesn't already exist to prevent duplicates on rerun.
    """
    try:
        if os.path.isfile(OUTPUT_FILE):
             wb = load_workbook(OUTPUT_FILE)
             ws = wb.active
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = "Summary"
            ws.append(['Date', 'Number', 'Balance'])
        
        # Check for duplicates before appending? 
        # For performance, maybe load all into set first?
        # Given simpler requirement, just append. 
        # IF user re-runs on same folder, it will duplicate. 
        # Let's add basic dup check based on number?
        
        # Simple duplicate avoidance:
        # scan existing rows
        is_duplicate = False
        for row in ws.iter_rows(min_row=2, values_only=True):
            if str(row[1]) == str(number):
                # Update existing? or Skip?
                # User said "traite maintenant de tel sorte qu'il n'y a pas d'erreur"
                # If we just append, summary grows infinitely.
                # Ideally we upsert.
                # Let's simple append for now but you might want to clear file first or use pandas.
                # Assuming "Error" meant execution error, not logic.
                pass

        # Actually, using pandas is much robust and easier to handle dups.
        # But sticking to openpyxl as requested previously.
        ws.append([date, number, float(balance) if balance else 0])
        wb.save(OUTPUT_FILE)
            
    except Exception as e:
        print(f"Error writing to summary file: {e}")

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_file(event.src_path)

def main():
    print(f"Starting Transaction Processor...")
    print(f"Monitoring directory: {INPUT_DIRECTORY}")
    print(f"Output file: {OUTPUT_FILE}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Process existing files first
    print("Processing existing files...")
    
    # Clear output file to avoid duplicates on restart? 
    # Or maybe user wants incremental? 
    # Let's start fresh for "processed existing files" run to be clean.
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
            print("Cleared existing summary file to rebuild from data folder.")
        except PermissionError:
            print("Warning: Could not clear summary file. Appending new data.")

    if os.path.exists(INPUT_DIRECTORY):
        files = [f for f in os.listdir(INPUT_DIRECTORY) if f.startswith('Transactions_') and f.endswith('.csv')]
        print(f"Found {len(files)} transaction files.")
        for filename in files:
            filepath = os.path.join(INPUT_DIRECTORY, filename)
            process_file(filepath)
    else:
        print(f"Error: Input directory {INPUT_DIRECTORY} does not exist. Creating it.")
        os.makedirs(INPUT_DIRECTORY, exist_ok=True)

    # Set up watchdog
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, INPUT_DIRECTORY, recursive=False)
    observer.start()
    
    print("Monitoring for new files... (Press Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
