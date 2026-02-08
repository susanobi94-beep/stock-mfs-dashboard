import streamlit as st
import pandas as pd
import altair as alt
import os

# Configuration
DATA_FILE = 'reconciliation.xlsx'
LOGO_FILE = 'logo.png'

st.set_page_config(page_title="Cockpit MFS", layout="wide", page_icon="📶")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 20px;
        height: 100%;
    }
    .metric-title { font-size: 14px; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
    @media (min-width: 768px) { .metric-value { font-size: 32px; } }
    .metric-delta { font-size: 14px; color: #28a745; }
    .metric-delta.neg { color: #dc3545; }
    .chart-container {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .header-style { font-size: 40px; font-weight: 900; color: #000000; text-align: center; padding-bottom: 30px; text-transform: uppercase; letter-spacing: 2px; }
    @media (min-width: 768px) { .header-style { font-size: 85px; } }
    [data-testid="stSidebar"] { background-color: #000000; color: #ffffff; }
    [data-testid="stSidebar"] .css-17lntkn { color: white; }
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

def metric_card(title, value, delta=None, color="black"):
    delta_html = f"<div class='metric-delta'>{delta}</div>" if delta else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value" style="color: {color}">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def main():
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_column_width=True)
    
    st.sidebar.markdown("<h3 style='color: white;'>Filtres</h3>", unsafe_allow_html=True)
    
    df = load_data()
    if df is None:
        st.error("Données non trouvées.")
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

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: metric_card("Stock Actuel", f"{total_balance/1_000_000:.1f}M", "FCFA")
    with col2: metric_card("Objectif Stock", f"{total_oos/1_000_000:.1f}M", "FCFA")
    
    rate_color = "#dc3545" if rupture_rate_val > 20 else "#28a745"
    with col3: metric_card("Taux Rupture", f"{rupture_rate_val:.1f}%", "Cible: < 20%", color=rate_color)
    
    with col4: metric_card("Cash Dormant", f"{sleeping_cash/1_000_000:.1f}M", "> 5 Jours", color="#ffc107")
    with col5: metric_card("Couverture Globale", f"{global_days:.1f}j", "Cible: 1.0j")

    # --- Banner ---
    st.markdown("---")
    if rupture_rate_val > 20:
        st.error(f"⚠️ **ALERTE CRITIQUE : Le Taux de Rupture est de {rupture_rate_val:.1f}% (> 20%).** \n\n"
                 f"Il est impératif de réapprovisionner les {pos_rupture} points de vente en rupture immédiatement.")
    else:
        st.success(f"✅ **PERFORMANCE : Le Taux de Rupture est maîtrisé à {rupture_rate_val:.1f}% (< 20%).**")
    st.markdown("---")
    
    # --- Cluster Focus ---
    if selected_site == "Tous":
        def quick_kpi(df_sub, name):
            if df_sub.empty: return
            sub_pos = len(df_sub)
            sub_rupture = df_sub[df_sub['Jours de Stock'] < 0.5].shape[0]
            sub_rate = (sub_rupture / sub_pos * 100) if sub_pos > 0 else 0
            sub_color = "red" if sub_rate > 20 else "green"
            icon = "🔴" if sub_rate > 20 else "🟢"
            st.markdown(f"""
            <div style="padding:15px; border-radius:8px; background-color:white; border-left: 5px solid {sub_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom:10px;">
                <h4 style="margin:0; text-transform:uppercase; color: #555;">{icon} {name}</h4>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                     <div style="font-size:28px; font-weight:bold; color:{sub_color}">{sub_rate:.1f}%</div>
                     <div style="color:#888; font-size:12px;">Objectif < 20%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.subheader("🔍 Focus Clusters Clés")
        cols = st.columns(2)
        c_sic = df[df['Site'].str.contains("Cite Sic", case=False, na=False)]
        c_ndog = df[df['Site'].str.contains("Ndogbong", case=False, na=False)]
        with cols[0]: 
            if not c_sic.empty: quick_kpi(c_sic, "Cité Sic")
        with cols[1]: 
            if not c_ndog.empty: quick_kpi(c_ndog, "Ndogbong")

    # --- Charts with Altair (Replacing Plotly) ---
    c1, c2 = st.columns([2, 1])
    
    df_filtered['Manque (Gap)'] = df_filtered.apply(lambda row: max(0.0, float(row['Montants OOS']) - float(row['Balance'])), axis=1)
    df_recharge = df_filtered[df_filtered['Manque (Gap)'] > 0].sort_values(by='Manque (Gap)', ascending=False).head(20)
    
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

    with c1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📍 Où manque-t-il de l'argent ? (Top 20)")
        if not df_recharge.empty:
            chart_gap = alt.Chart(df_recharge).mark_bar().encode(
                x=alt.X('Manque (Gap)', title='Montant à recharger'),
                y=alt.Y('Noms', sort='-x', title='Agent / POS'),
                color=alt.Color('Jours de Stock', scale=alt.Scale(scheme='redyellowgreen'), title='Jours Stock'),
                tooltip=['Noms', 'Manque (Gap)', 'Jours de Stock', 'Site']
            ).interactive()
            st.altair_chart(chart_gap, use_container_width=True)
        else:
            st.success("Aucun manque de stock détecté.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📊 État du Parc")
        pie_data = df_filtered['Statut'].value_counts().reset_index()
        pie_data.columns = ['Statut', 'Compte']
        
        chart_pie = alt.Chart(pie_data).mark_bar().encode(
            x='Compte',
            y=alt.Y('Statut', sort=domain),
            color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_), legend=None),
            tooltip=['Statut', 'Compte']
        ).properties(height=300)
        
        st.altair_chart(chart_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Row 2: Scatter
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("📈 Précision du Stockage (Balance vs Cible)")
    
    chart_scatter = alt.Chart(df_filtered).mark_circle(size=60).encode(
        x=alt.X('Montants OOS', title='Objectif (OOS)'),
        y=alt.Y('Balance', title='Stock Actuel'),
        color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_)),
        tooltip=['Noms', 'Numero', 'Balance', 'Montants OOS', 'Jours de Stock', 'Site']
    ).interactive().properties(height=500)
    
    st.altair_chart(chart_scatter, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Row 3: Action Table
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("📋 État Complet du Réseau")
    
    df_table = df_filtered.copy()
    def get_action(gap):
        return f"⚠️ RECHARGER {gap:,.0f}" if gap > 0 else "✅ OK"
    
    df_table['Action'] = df_table['Manque (Gap)'].apply(get_action)
    df_table = df_table.sort_values(by='Manque (Gap)', ascending=False)
    
    display_cols = ['Numero', 'Noms', 'Site', 'Routes', 'Sous-Zone', 'Balance', 'Montants OOS', 'Jours de Stock', 'Action']
    display_cols = [c for c in display_cols if c in df_table.columns]

    st.dataframe(df_table[display_cols], use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
