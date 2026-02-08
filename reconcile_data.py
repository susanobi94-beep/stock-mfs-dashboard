import pandas as pd
import os

# Configuration
SUMMARY_FILE = r'c:\Users\user\Downloads\r2b\summary.xlsx'
OOS_FILE = r'c:\Users\user\Downloads\r2b\OOS1.xlsx'
OUTPUT_FILE = r'c:\Users\user\Downloads\r2b\reconciliation.xlsx'

def reconcile_data():
    print("Starting data reconciliation...")
    
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
            df_summary['Number'] = df_summary['Number'].astype(str)
        
        # OOS1 specific column handling
        # Dashboard requirements: Site (Broad), Sous-Zone (Specific), Routes (Distribution Rte_X)
        # OOS1 columns: 'ISL_Terr' (Broad), 'SITENAME' (Narrow), 'Routes' (Rte_X), 'Agent MSISDN', 'Average of oos_target'
        # Mapping:
        # Agent MSISDN -> AGENT_MSISDN
        # Average of oos_target -> Montants OOS
        # ISL_Terr -> Site
        # SITENAME -> Sous-Zone
        # Routes -> Routes (Keep original)
        
        oos_rename_map = {
            'Agent MSISDN': 'AGENT_MSISDN',
            'Average of oos_target': 'Montants OOS',
            'ISL_Terr': 'Site',
            'SITENAME': 'Sous-Zone'
        }
        
        available_cols = df_oos.columns.tolist()
        rename_dict = {k: v for k, v in oos_rename_map.items() if k in available_cols}
        
        df_oos = df_oos.rename(columns=rename_dict)
        
        if 'AGENT_MSISDN' not in df_oos.columns:
            print("Error: 'Agent MSISDN' column not found in OOS file.")
            print(f"Available columns: {available_cols}")
            return

        df_oos['AGENT_MSISDN'] = df_oos['AGENT_MSISDN'].astype(str)
        
        # Deduplicate OOS data
        if df_oos.duplicated(subset=['AGENT_MSISDN']).any():
            print("Detailed OOS data contains duplicates for agents. Aggregating...")
            
            # 1. Numeric aggregation (Mean)
            numeric_cols = []
            if 'Montants OOS' in df_oos.columns:
                 numeric_cols.append('Montants OOS')
            
            if numeric_cols:
                cols_to_use = ['AGENT_MSISDN'] + numeric_cols
                df_numeric = df_oos[cols_to_use].groupby('AGENT_MSISDN', as_index=False).mean()
            else:
                df_numeric = df_oos[['AGENT_MSISDN']].drop_duplicates()

            # 2. Categorical aggregation (First)
            # Prioritize categorical columns: Site, Sous-Zone, Routes, segment_group, TERRITORY CORRECT
            desired_cat_cols = ['Site', 'Sous-Zone', 'Routes', 'segment_group', 'TERRITORY CORRECT']
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
        df_merged = pd.merge(df_summary, df_oos, left_on='Number', right_on='AGENT_MSISDN', how='inner')

        # Calculate Values
        print("Calculating metrics...")
        
        if 'Montants OOS' in df_merged.columns:
            df_merged['Montants OOS'] = pd.to_numeric(df_merged['Montants OOS'], errors='coerce').fillna(0)
        else:
            df_merged['Montants OOS'] = 0
            
        if 'Balance' in df_merged.columns:
            df_merged['Balance'] = pd.to_numeric(df_merged['Balance'], errors='coerce').fillna(0)
        else:
            df_merged['Balance'] = 0
        
        df_merged['Valeur Calculee'] = df_merged['Balance'] - df_merged['Montants OOS']
        
        def clean_div(x, y):
            return (x / y) if y != 0 else 0

        df_merged['Jours de Stock'] = df_merged.apply(lambda row: clean_div(row['Balance'], row['Montants OOS']), axis=1)

        if 'nom et prenoms' not in df_merged.columns:
             df_merged['nom et prenoms'] = df_merged['Number']

        final_columns_map = {
            'Number': 'Numero',
            'nom et prenoms': 'Noms',
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

        # Save to Excel
        print(f"Saving to {OUTPUT_FILE}...")
        df_final.to_excel(OUTPUT_FILE, index=False)
        print("Reconciliation complete.")
        print(f"Preview:\n{df_final.head()}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reconcile_data()
