import unittest
import os
import csv
import shutil
import openpyxl
from transaction_processor import process_file, write_to_summary

class TestTransactionProcessor(unittest.TestCase):

    def setUp(self):
        self.test_dir = r'c:\Users\user\Downloads\r2b'
        self.test_file = os.path.join(self.test_dir, 'Transactions_999999999.csv')
        self.output_file = os.path.join(self.test_dir, 'summary.xlsx')
        
        # Remove output file if it exists to start fresh
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

        # Create a dummy transaction file
        headers = [
            'Id', 'External id', 'Date', 'Status', 'Type', 'Provider category', 'From', 'From name', 
            'From handler name', 'To', 'To name', 'To handler name', 'To message', 'Initiated by', 
            'Initiated by', 'On behalf of', 'On behalf of', 'Approved by', 'From / Fee', 'Currency', 
            'From / External fee', 'Currency', 'To / Fee', 'Currency', 'To / External fee', 'Currency', 
            'From / Refunded fee', 'Currency', 'To / Refunded fee', 'Currency', 'From / Taxes', 'Currency', 
            'To / Taxes', 'Currency', 'From / Refunded taxes', 'Currency', 'To / Refunded taxes', 'Currency', 
            'Discount', 'Currency', 'From / Promotion', 'Currency', 'To / Promotion', 'Currency', 'Coupon', 
            'Currency', 'Amount', 'Currency', 'Balance', 'Currency', 'External amount', 'Currency', 
            'External FX rate', 'External service provider'
        ]
        
        with open(self.test_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            row = {
                'Id': '12345',
                'Date': '2026-01-01 12:00:00',
                'Status': 'Successful',
                'Amount': '100',
                'Balance': '50000',
                'Currency': 'XAF'
            }
            writer.writerow(row)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        # We might want to keep the summary file for inspection
        pass

    def test_process_file(self):
        # Run the processing function
        process_file(self.test_file)

        # Check if the output file exists
        self.assertTrue(os.path.exists(self.output_file))

        # Check if the data was written correctly using openpyxl
        found = False
        wb = openpyxl.load_workbook(self.output_file)
        ws = wb.active
        
        for row in ws.iter_rows(values_only=True):
            # Check for the data row (Date, Number, Balance)
            # Balance should be a float/int, not string, so we cast to check
            if row[0] == '2026-01-01 12:00:00' and str(row[1]) == '999999999' and row[2] == 50000:
                found = True
                break
        
        self.assertTrue(found, "The expected data was not found in the summary Excel file.")

if __name__ == '__main__':
    unittest.main()
