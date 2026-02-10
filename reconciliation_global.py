import pandas as pd
import os
from datetime import datetime

# Configuration
SUMMARY_FILE = r'c:\Users\user\Downloads\r2b\summary.xlsx'
OOS_FILE = r'c:\Users\user\Downloads\r2b\OOS1.xlsx'
OUTPUT_FILE = r'c:\Users\user\Downloads\r2b\reconciliation.xlsx'
HISTORY_FILE = r'c:\Users\user\Downloads\r2b\history.csv'

def reconcile_data():
    print("Starting data reconciliation (Global Script)...")
    
    if not os.path.exists(SUMMARY_FILE):
        print(f"Error: Summary file {SUMMARY_FILE} not found.")
        return
    
    if not os.path.exists(OOS_FILE):
        print(f"Error: OOS file {OOS_FILE} not found.")
        return

    try:
        # Load Dataframes
        print(f"Loading files... {SUMMARY_FILE} and {OOS_FILE}")
        df_summary = pd.read_excel(SUMMARY_FILE)
        df_oos = pd.read_excel(OOS_FILE)

        # Normalize Columns for Merging
        if 'Number' in df_summary.columns:
            df_summary['Number'] = df_summary['Number'].astype(str).str.strip()
        
        # OOS1 specific column handling
        # Map OOS columns
        oos_rename_map = {
            'Agent MSISDN': 'AGENT_MSISDN',
            'Average of oos_target': 'Montants OOS',
            'ISL_Terr': 'Site',
            'SITENAME': 'Sous-Zone' 
        }
        
        available_cols = df_oos.columns.tolist()
        rename_dict = {k: v for k, v in oos_rename_map.items() if k in available_cols}
        df_oos = df_oos.rename(columns=rename_dict)
        
        # Identify fallback name from OOS (SITENAME which is now Sous-Zone, or just SITENAME if copy)
        # We want to preserve 'Sous-Zone' for hierarchy, but also use it as Name fallback
        if 'Sous-Zone' in df_oos.columns:
             df_oos['OOS_Name'] = df_oos['Sous-Zone']
        elif 'SITENAME' in available_cols:
             df_oos['OOS_Name'] = df_oos['SITENAME']
        else:
             df_oos['OOS_Name'] = None

        if 'AGENT_MSISDN' not in df_oos.columns:
            print("Error: 'Agent MSISDN' column not found in OOS file.")
            return

        df_oos['AGENT_MSISDN'] = df_oos['AGENT_MSISDN'].astype(str).str.strip()
        
        # Deduplicate OOS data
        if df_oos.duplicated(subset=['AGENT_MSISDN']).any():
            print("Detailed OOS data contains duplicates for agents. Aggregating...")
            
            # 1. Numeric aggregation (Mean)
            if 'Montants OOS' in df_oos.columns:
                 df_oos['Montants OOS'] = pd.to_numeric(df_oos['Montants OOS'], errors='coerce').fillna(0.0)
                 df_numeric = df_oos[['AGENT_MSISDN', 'Montants OOS']].groupby('AGENT_MSISDN', as_index=False).mean()
            else:
                 df_numeric = df_oos[['AGENT_MSISDN']].drop_duplicates()

            # 2. Categorical aggregation (First)
            # Include temporary OOS_Name
            desired_cat_cols = ['Site', 'Sous-Zone', 'Routes', 'segment_group', 'TERRITORY CORRECT', 'OOS_Name']
            cat_cols = [c for c in desired_cat_cols if c in df_oos.columns]
            
            if cat_cols:
                cols_to_use = ['AGENT_MSISDN'] + cat_cols
                df_cat = df_oos[cols_to_use].groupby('AGENT_MSISDN', as_index=False).first()
                df_oos_agg = pd.merge(df_numeric, df_cat, on='AGENT_MSISDN', how='left')
                df_oos = df_oos_agg
            else:
                df_oos = df_numeric

        # Merge Dataframes
        print("Merging data...")
        # summary.xlsx has ['Date', 'Number', 'Name', 'Balance']
        df_merged = pd.merge(df_summary, df_oos, left_on='Number', right_on='AGENT_MSISDN', how='inner')

        # Logic for 'Noms'
        # Priority 1: Name from Summary (Transaction file)
        # Priority 2: OOS_Name (SITENAME from OOS)
        # Priority 3: Number
        
        def determine_name(row):
            # Check Summary Name
            s_name = str(row.get('Name', '')).strip()
            if s_name and s_name.lower() not in ['nan', 'unknown', 'none', '']:
                return s_name
            
            # Check OOS Name
            o_name = str(row.get('OOS_Name', '')).strip()
            if o_name and o_name.lower() not in ['nan', 'unknown', 'none', '']:
                return o_name
                
            return str(row.get('Number', ''))

        df_merged['Noms'] = df_merged.apply(determine_name, axis=1)

        # Force float type for numeric columns
        df_merged['Montants OOS'] = pd.to_numeric(df_merged.get('Montants OOS', 0), errors='coerce').fillna(0.0)
        df_merged['Balance'] = pd.to_numeric(df_merged.get('Balance', 0), errors='coerce').fillna(0.0)
        
        df_merged['Valeur Calculee'] = df_merged['Balance'] - df_merged['Montants OOS']
        
        # Avoid division by zero and ensure float result
        def clean_div(row):
            oos = float(row['Montants OOS'])
            bal = float(row['Balance'])
            if oos == 0:
                return 0.0
            return bal / oos

        df_merged['Jours de Stock'] = df_merged.apply(clean_div, axis=1)

        final_columns_map = {
            'Number': 'Numero',
            'Noms': 'Noms',
            'Routes': 'Routes',
            'Sous-Zone': 'Sous-Zone',
            'Montants OOS': 'Montants OOS',
            'Balance': 'Balance',
            'Valeur Calculee': 'Valeur Calculee',
            'Jours de Stock': 'Jours de Stock',
            'Site': 'Site'
        }
        
        # Verify columns exist
        for col_in_merged, col_final in final_columns_map.items():
            if col_in_merged not in df_merged.columns:
                print(f"Warning: Column {col_in_merged} not found in merged data. Filling with default.")
                df_merged[col_in_merged] = "N/A"
                
        existing_cols = [c for c in final_columns_map.keys() if c in df_merged.columns]
        df_final = df_merged[existing_cols]
        df_final = df_final.rename(columns=final_columns_map)

        # Final check on types
        numeric_final_cols = ['Montants OOS', 'Balance', 'Valeur Calculee', 'Jours de Stock']
        for col in numeric_final_cols:
            if col in df_final.columns:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0.0)
        
        if 'Numero' in df_final.columns:
            df_final['Numero'] = pd.to_numeric(df_final['Numero'], errors='coerce').fillna(0).astype('int64')

        # --- HISTORICAL LOGGING ---
        try:
             today_str = datetime.now().strftime('%Y-%m-%d')
             total_balance = df_final['Balance'].sum() if 'Balance' in df_final.columns else 0
             total_oos = df_final['Montants OOS'].sum() if 'Montants OOS' in df_final.columns else 0
             total_pos = len(df_final)
             pos_rupture = df_final[df_final['Jours de Stock'] < 0.5].shape[0] if 'Jours de Stock' in df_final.columns else 0
             rupture_rate = (pos_rupture / total_pos * 100) if total_pos > 0 else 0
             
             new_row = {
                 'Date': today_str,
                 'Total_Balance': total_balance,
                 'Total_OOS': total_oos,
                 'Rupture_Rate': rupture_rate,
                 'POS_Count': total_pos
             }
             
             if os.path.exists(HISTORY_FILE):
                 df_hist = pd.read_csv(HISTORY_FILE)
             else:
                 df_hist = pd.DataFrame(columns=['Date', 'Total_Balance', 'Total_OOS', 'Rupture_Rate', 'POS_Count'])
             
             df_hist = df_hist[df_hist['Date'] != today_str]
             df_hist = pd.concat([df_hist, pd.DataFrame([new_row])], ignore_index=True)
             df_hist.to_csv(HISTORY_FILE, index=False)
             print(f"History updated for {today_str}.")
             
        except Exception as h_err:
             print(f"Warning: Could not update history log: {h_err}")

        # Save to Excel
        print(f"Saving to {OUTPUT_FILE}...")
        df_final.to_excel(OUTPUT_FILE, index=False)
        print("Reconciliation complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reconcile_data()
