import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuration
DATA_FILE = 'reconciliation.xlsx'
LOGO_FILE = 'logo.png'

st.set_page_config(page_title="Cockpit MFS", layout="wide", page_icon="📶")

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        df = pd.read_excel(DATA_FILE)
        
        # Numeric coercion
        numeric_cols = ['Balance', 'Montants OOS', 'Jours de Stock']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # String coercion
        text_cols = ['Site', 'Routes', 'Sous-Zone', 'Noms']
        for col in text_cols:
             if col in df.columns:
                 df[col] = df[col].astype(str).replace('nan', 'Inconnu')

        # Numero numeric
        if 'Numero' in df.columns:
            df['Numero'] = pd.to_numeric(df['Numero'], errors='coerce').fillna(0).astype('int64')

        return df
    except Exception as e:
        st.error(f"Erreur data: {e}")
        return None

def main():
    # Sidebar
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_column_width=True)
    
    st.title("Pilotage Stock MFS (Mode Simplifié)")
    
    df = load_data()
    if df is None:
        st.error("Fichier de données manquant.")
        return

    # Filters
    all_sites = ["Tous"] + sorted(list(df['Site'].unique()))
    selected_site = st.sidebar.selectbox("Site", all_sites)
    
    df_filtered = df[df['Site'] == selected_site] if selected_site != "Tous" else df.copy()

    # Determine Status
    def get_status(d):
        if d < 0.5: return "Rupture"
        if d < 1.0: return "Tension"
        if d <= 3.0: return "Confort"
        return "Surstock"
    
    df_filtered['Statut'] = df_filtered['Jours de Stock'].apply(get_status)

    # KPIs Standard
    total_balance = df_filtered['Balance'].sum()
    total_oos = df_filtered['Montants OOS'].sum()
    pos_rupture = df_filtered[df_filtered['Statut'] == "Rupture"].shape[0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Stock Actuel", f"{total_balance:,.0f}")
    c2.metric("Objectif", f"{total_oos:,.0f}")
    
    rupture_rate = (pos_rupture / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    c3.metric("Taux Rupture", f"{rupture_rate:.1f}%")

    if rupture_rate > 20:
        st.error(f"Alerte: Taux de rupture > 20% ({pos_rupture} POS)")
    else:
        st.success("Taux de rupture maîtrisé")

    # Simple Charts (No Custom Maps initially)
    st.subheader("Distribution du Parc")
    fig_pie = px.pie(df_filtered, names='Statut', title="Répartition par Statut")
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Précision Stock (Balance vs OOS)")
    # Basic Scatter
    fig_scatter = px.scatter(
        df_filtered, 
        x='Montants OOS', 
        y='Balance', 
        color='Statut',
        hover_data=['Noms', 'Numero'],
        title="Balance vs Objectif"
    )
    # Force axis to start at 0
    max_val = max(df_filtered['Montants OOS'].max(), df_filtered['Balance'].max(), 100)
    fig_scatter.update_layout(xaxis_range=[0, max_val], yaxis_range=[0, max_val])
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Raw Data
    st.subheader("Données Détaillées")
    st.dataframe(df_filtered)

if __name__ == "__main__":
    main()
