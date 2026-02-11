import csv
import os
import time
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
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
            name = first_row.get('From name', 'Unknown')

        if date is None or balance is None:
             print(f"Skipping {filename}: 'Date' or 'Balance' column missing.")
             return

        update_summary_upsert(date, number, name, balance)
        print(f"Processed {filename}: Date={date}, Number={number}, Balance={balance}")

    except Exception as e:
        print(f"Error processing {filename}: {e}")

def update_summary_upsert(date, number, name, balance):
    """
    Update the summary Excel file by UPSERT (Update if Number exists, Insert if not).
    This allows continuous cycling without duplicate rows for the same Number.
    """
    try:
        columns = ['Date', 'Number', 'Name', 'Balance']
        
        if os.path.isfile(OUTPUT_FILE):
             try:
                 df = pd.read_excel(OUTPUT_FILE)
             except ValueError: # Empty file
                 df = pd.DataFrame(columns=columns)
        else:
            df = pd.DataFrame(columns=columns)
        
        # Ensure Number is string for comparison
        number = str(number).strip()
        if 'Number' in df.columns:
            df['Number'] = df['Number'].astype(str).str.strip()
        
        # Check if number exists
        mask = df['Number'] == number
        
        new_row = {
            'Date': date, 
            'Number': number, 
            'Name': name, 
            'Balance': float(balance) if balance else 0
        }
        
        if mask.any():
            # Update existing row
            # We use the index of the first match
            idx = df[mask].index[0]
            df.loc[idx, 'Date'] = date
            df.loc[idx, 'Balance'] = float(balance) if balance else 0
            # Update name only if it was unknown or strictly better? 
            # Let's assume new file has correct name.
            if name and name != "Unknown":
                df.loc[idx, 'Name'] = name
            # print(f"   -> Updated existing record for {number}")
        else:
            # Append new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            # print(f"   -> Added new record for {number}")
            
        # Save back
        df.to_excel(OUTPUT_FILE, index=False)
            
    except Exception as e:
        print(f"Error updating summary file: {e}")

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_file(event.src_path)

def main():
    print(f"Starting Transaction Processor...")
    print(f"Monitoring directory: {INPUT_DIRECTORY}")
    print(f"Output file: {OUTPUT_FILE}")
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Process existing files first
    print("Processing existing files...")
    # NOTE: In continuous mode, we do NOT clear the file at start of THIS script
    # because auto_sync.py clears it at the very beginning of the session.
    # But if this script is run standalone, it appends/updates.
    
    if os.path.exists(INPUT_DIRECTORY):
        files = [f for f in os.listdir(INPUT_DIRECTORY) if f.startswith('Transactions_') and f.endswith('.csv')]
        print(f"Found {len(files)} transaction files.")
        for filename in files:
            filepath = os.path.join(INPUT_DIRECTORY, filename)
            process_file(filepath)
    else:
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
