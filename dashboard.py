import streamlit as st
import pandas as pd
import altair as alt
import os

# Configuration
DATA_FILE = 'reconciliation.xlsx'
LOGO_FILE = 'logo.png'

st.set_page_config(page_title="Cockpit MFS", layout="wide", page_icon="📶")

# --- CUSTOM CSS (Clean & Minimal) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .header-style { 
        font-size: 40px; 
        font-weight: 900; 
        color: #000000; 
        text-align: center; 
        padding-bottom: 20px; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
    }
    .sub-header {
        font-size: 20px;
        font-weight: bold;
        color: #333;
        margin-bottom: 15px;
        border-bottom: 2px solid #eee;
        padding-bottom: 5px;
    }
    .interpretation-box {
        background-color: #e9ecef;
        padding: 15px;
        border-radius: 5px;
        margin-top: 10px;
        border-left: 5px solid #0d6efd;
        font-size: 14px;
        color: #495057;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        df = pd.read_excel(DATA_FILE)
        
        # --- ROBUST DATA CLEANING ---
        numeric_cols = ['Balance', 'Montants OOS', 'Jours de Stock', 'Valeur Calculee']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0

        text_cols = ['Site', 'Routes', 'Sous-Zone', 'Noms']
        for col in text_cols:
             if col in df.columns:
                 df[col] = df[col].astype(str).replace('nan', 'Inconnu')
             else:
                 df[col] = 'Inconnu'
        
        if 'Numero' in df.columns:
            df['Numero'] = pd.to_numeric(df['Numero'], errors='coerce').fillna(0).astype('int64')

        return df
    except Exception as e:
        st.error(f"Erreur de chargement des données: {e}")
        return None

def main():
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_column_width=True)
    
    st.sidebar.markdown("<h3 style='color: white;'>Filtres</h3>", unsafe_allow_html=True)
    
    df = load_data()
    if df is None:
        st.error("Données non trouvées sur le serveur.")
        return

    # Filters
    all_sites = ["Tous"] + sorted(list(df['Site'].dropna().unique()))
    selected_site = st.sidebar.selectbox("Site", all_sites)
    
    if selected_site != "Tous":
        df_filtered = df[df['Site'] == selected_site]
    else:
        df_filtered = df.copy()

    # Route Filter
    available_routes = ["Tous"] + sorted(list(df_filtered['Routes'].unique()))
    selected_route = st.sidebar.selectbox("Route Distribution", available_routes)
    
    if selected_route != "Tous":
        df_filtered = df_filtered[df_filtered['Routes'] == selected_route]
            
    # Sous-Zone Filter
    valid_sous_zones = df_filtered['Sous-Zone'].dropna().unique()
    available_sous_zones = ["Tous"] + sorted(list(valid_sous_zones))
    
    if len(available_sous_zones) > 2:
         selected_sous_zone = st.sidebar.selectbox("Sous-Zone / PDV", available_sous_zones)
         if selected_sous_zone != "Tous":
            df_filtered = df_filtered[df_filtered['Sous-Zone'] == selected_sous_zone]

    # --- Header ---
    st.markdown('<p class="header-style">Pilotage du Stock MFS <span style="color:#FFCC00;">●</span></p>', unsafe_allow_html=True)

    # --- KPIs ---
    total_balance = df_filtered['Balance'].sum()
    total_oos = df_filtered['Montants OOS'].sum()
    sleeping_cash = df_filtered[df_filtered['Jours de Stock'] > 5.0]['Balance'].sum()
    
    total_pos = len(df_filtered)
    pos_rupture = df_filtered[df_filtered['Jours de Stock'] < 0.5].shape[0]
    rupture_rate_val = (pos_rupture / total_pos * 100) if total_pos > 0 else 0
    
    global_days = (total_balance / total_oos) if total_oos > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stock Actuel", f"{total_balance/1_000_000:.1f}M", "FCFA")
    c2.metric("Objectif Stock", f"{total_oos/1_000_000:.1f}M", "FCFA")
    c3.metric("Taux Rupture", f"{rupture_rate_val:.1f}%", f"{pos_rupture} POS")
    c4.metric("Couverture", f"{global_days:.1f}j", "Cible: 1.0j")

    # --- Banner ---
    st.markdown("---")
    if rupture_rate_val > 20:
        st.error(f"⚠️ **ALERTE CRITIQUE : Le Taux est de {rupture_rate_val:.1f}% (> 20%).** Action requise immédiate.")
    else:
        st.success(f"✅ **PERFORMANCE : Taux maîtrisé à {rupture_rate_val:.1f}%.**")
    st.markdown("---")

    # --- Data Prep for Charts ---
    df_filtered['Manque (Gap)'] = df_filtered.apply(lambda row: max(0.0, float(row['Montants OOS']) - float(row['Balance'])), axis=1)
    
    def classify_pos(days):
        try:
            d = float(days)
            if d < 0.5: return "Rupture"
            if d < 1.0: return "Tension"
            if d <= 3.0: return "Confort"
            return "Surstock"
        except:
            return "Erreur"

    df_filtered['Statut'] = df_filtered['Jours de Stock'].apply(classify_pos)
    
    domain = ["Rupture", "Tension", "Confort", "Surstock", "Erreur"]
    range_ = ["#d32f2f", "#f57c00", "#2e7d32", "#1976d2", "gray"]

    # --- Interpretation for Scatter ---
    # Analyze the distribution relative to the diagonal (Balance = OOS)
    under_target = df_filtered[df_filtered['Balance'] < df_filtered['Montants OOS']].shape[0]
    over_target = total_pos - under_target
    under_percent = (under_target / total_pos * 100) if total_pos > 0 else 0
    
    interpretation_text = ""
    if under_percent > 60:
        interpretation_text = f"🚨 **Tendance Claire : Sous-Stockage Massif.** <br> {under_percent:.1f}% des points de vente sont en dessous de leur objectif (la majorité des points sont sous la ligne pointillée). Il faut prioriser le rechargement global."
    elif under_percent < 40:
        interpretation_text = f"🔵 **Tendance Claire : Sur-Stockage.** <br> {100-under_percent:.1f}% des points ont plus de stock que prévu. Il peut y avoir du cash dormant à récupérer."
    else:
        interpretation_text = f"⚖️ **Situation Équilibrée.** <br> Le réseau est partagé entre sous-stockage ({under_percent:.1f}%) et sur-stockage ({100-under_percent:.1f}%). Ciblez les cas extrêmes."

    # --- Charts with Altair ---
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown('<div class="sub-header">📊 État du Parc (Distribution)</div>', unsafe_allow_html=True)
        pie_data = df_filtered['Statut'].value_counts().reset_index()
        pie_data.columns = ['Statut', 'Compte']
        pie_data['Pourcentage'] = (pie_data['Compte'] / pie_data['Compte'].sum()).map("{:.1%}".format)
        
        # Interactive Bar Chart with Percentage labels
        bars = alt.Chart(pie_data).mark_bar().encode(
            x=alt.X('Compte', title='Nombre de PDV'),
            y=alt.Y('Statut', sort=domain, title=None),
            color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_), legend=None),
            tooltip=['Statut', 'Compte', 'Pourcentage']
        )
        
        text = bars.mark_text(
            align='left',
            baseline='middle',
            dx=3  # Nudges text to right so it doesn't overlap bar
        ).encode(
            text='Pourcentage'
        )
        
        final_chart = (bars + text).properties(height=300)
        st.altair_chart(final_chart, use_container_width=True)
        st.caption("Ce graphique montre la répartition des points de vente par niveau de santé stock.")

    with c2:
        st.markdown('<div class="sub-header">📍 Où manque-t-il de l\'argent ? (Top 15)</div>', unsafe_allow_html=True)
        df_recharge = df_filtered[df_filtered['Manque (Gap)'] > 0].sort_values(by='Manque (Gap)', ascending=False).head(15)
        
        if not df_recharge.empty:
            chart_gap = alt.Chart(df_recharge).mark_bar().encode(
                x=alt.X('Manque (Gap)', title='Montant à recharger (FCFA)'),
                y=alt.Y('Noms', sort='-x', title=None),
                color=alt.Color('Jours de Stock', scale=alt.Scale(scheme='redyellowgreen'), title='Jours Stock'),
                tooltip=['Noms', 'Manque (Gap)', 'Jours de Stock', 'Site', 'Numero']
            ).properties(height=300).interactive()
            st.altair_chart(chart_gap, use_container_width=True)
        else:
            st.success("✅ Aucun manque significatif identifié.")
        st.caption("Ces 15 points de vente représentent le plus gros besoin immédiat en cash.")

    # Scatter Full Width
    st.markdown('<div class="sub-header">📈 Précision du Stockage (Balance vs Cible)</div>', unsafe_allow_html=True)
    
    # Text interpretation next to title or below
    st.markdown(f'<div class="interpretation-box">{interpretation_text}</div>', unsafe_allow_html=True)
    
    # Scatter Chart
    chart_scatter = alt.Chart(df_filtered).mark_circle(size=60).encode(
        x=alt.X('Montants OOS', title='Objectif (OOS)'),
        y=alt.Y('Balance', title='Stock Actuel'),
        color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_), title='Statut'),
        tooltip=['Noms', 'Numero', 'Balance', 'Montants OOS', 'Jours de Stock', 'Site', 'Routes']
    ).properties(height=500).interactive()
    
    # Diagonal line
    max_val = max(df_filtered['Montants OOS'].max(), df_filtered['Balance'].max())
    line_data = pd.DataFrame({'x': [0, max_val], 'y': [0, max_val]})
    line = alt.Chart(line_data).mark_line(color='gray', strokeDash=[5, 5]).encode(x='x', y='y')
    
    st.altair_chart(chart_scatter + line, use_container_width=True)

    # --- Detailed Table ---
    st.markdown('<div class="sub-header">📋 État Complet du Réseau</div>', unsafe_allow_html=True)
    
    df_table = df_filtered.copy()
    def get_action(gap):
        return f"⚠️ RECHARGER {gap:,.0f}" if gap > 0 else "✅ OK"
    
    df_table['Action'] = df_table['Manque (Gap)'].apply(get_action)
    df_table = df_table.sort_values(by='Manque (Gap)', ascending=False)
    
    display_cols = ['Numero', 'Noms', 'Site', 'Routes', 'Sous-Zone', 'Balance', 'Montants OOS', 'Jours de Stock', 'Action']
    display_cols = [c for c in display_cols if c in df_table.columns]

    st.dataframe(df_table[display_cols], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
