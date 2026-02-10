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
    Process a single transaction file and extract date, number, name, and balance.
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
        
        # Extract Name Logic
        name = "Unknown"
        # Check where the number appears to get the correct name
        from_field = first_row.get('From', '')
        to_field = first_row.get('To', '')
        
        if number in from_field:
            name = first_row.get('From name', 'Unknown')
        elif number in to_field:
            name = first_row.get('To name', 'Unknown')
        else:
            # Fallback: sometimes format might differ, try generic match or just take From name
            # But let's try to be safe. If neither, maybe it's just 'From Name' typically.
            name = first_row.get('From name', 'Unknown')

        # If headers are different, might need adjustment
        if date is None or balance is None:
             print(f"Skipping {filename}: 'Date' or 'Balance' column missing. Headers found: {list(first_row.keys())}")
             return

        write_to_summary(date, number, name, balance)
        print(f"Processed {filename}: Date={date}, Number={number}, Name={name}, Balance={balance}")

    except Exception as e:
        print(f"Error processing {filename}: {e}")

def write_to_summary(date, number, name, balance):
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
            ws.append(['Date', 'Number', 'Name', 'Balance'])
        
        # Ensure header is correct if file existed but old format
        if ws.cell(row=1, column=3).value != 'Name':
             # If logic changes, might want to recreate. 
             # For now, let's assume we are rebuilding if we run this.
             if ws.max_row == 1: # Only header
                 ws.cell(row=1, column=3).value = 'Name'
                 ws.cell(row=1, column=4).value = 'Balance'

        ws.append([date, number, name, float(balance) if balance else 0])
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
    
    # Always start fresh when running main processing to ensure consistency
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
            print("Cleared existing summary file to rebuild from data folder.")
        except PermissionError:
            print("Warning: Could not clear summary file. Is it open? Appending instead.")

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
