import streamlit as st
import pandas as pd
import os

# Configuration
DATA_FILE = 'reconciliation.xlsx'

st.set_page_config(page_title="Diag MFS", layout="wide")

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        df = pd.read_excel(DATA_FILE)
        # Force column names to be stripped strings
        df.columns = df.columns.astype(str).str.strip()
        
        # Simple numeric coercion
        for col in ['Balance', 'Montants OOS', 'Jours de Stock']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Simple text coercion
        for col in ['Site', 'Routes', 'Sous-Zone', 'Noms']:
             if col in df.columns:
                 df[col] = df[col].astype(str).replace('nan', 'Inconnu')
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def main():
    st.title("Diagnostic Mode")
    
    df = load_data()
    if df is None:
        st.error("No Data File")
        return

    # 1. Show raw data count
    st.metric("Total Rows Loaded", len(df))
    
    # 2. Basic Filtering (Simplified)
    sites = ["All"] + sorted(list(df['Site'].unique()))
    sel_site = st.selectbox("Select Site", sites)
    
    if sel_site != "All":
        df_show = df[df['Site'] == sel_site]
    else:
        df_show = df

    st.metric("Rows After Filter", len(df_show))

    # 3. Show Data Table (First 10 rows)
    st.subheader("Data Preview (Head 10)")
    st.table(df_show.head(10))

    # 4. Native Streamlit Charts (No Plotly)
    st.subheader("Native Bar Chart: Balance")
    st.bar_chart(df_show['Balance'])

    st.subheader("Native Bar Chart: Montants OOS")
    st.bar_chart(df_show['Montants OOS'])
    
    # 5. Check if numeric values are non-zero
    st.subheader("Data Quality Check")
    zero_bal = df_show[df_show['Balance'] == 0].shape[0]
    zero_oos = df_show[df_show['Montants OOS'] == 0].shape[0]
    st.write(f"Rows with Balance = 0: {zero_bal}")
    st.write(f"Rows with OOS = 0: {zero_oos}")

if __name__ == "__main__":
    main()
