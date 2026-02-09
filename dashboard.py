import streamlit as st
import pandas as pd
import altair as alt
import os

# Configuration
DATA_FILE = 'reconciliation.xlsx'
LOGO_FILE = 'logo.png'

st.set_page_config(page_title="Cockpit MFS", layout="wide", page_icon="📶")

# --- CUSTOM CSS FOR UI ENHANCEMENT ---
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    
    /* KPI Cards Styling */
    .kpi-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        flex: 1;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-5px); }
    .kpi-title { font-size: 14px; color: #6c757d; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .kpi-value { font-size: 28px; font-weight: 800; color: #212529; }
    .kpi-sub { font-size: 12px; color: #adb5bd; margin-top: 5px; }
    
    /* Cluster Cards */
    .cluster-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    
    /* Headers */
    .header-style { 
        font-size: 32px; 
        font-weight: 800; 
        color: #1a1a1a; 
        text-align: center; 
        padding: 20px 0; 
        text-transform: uppercase; 
        background: -webkit-linear-gradient(45deg, #0d6efd, #0dcaf0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 18px;
        font-weight: 700;
        color: #495057;
        margin: 20px 0 10px 0;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        df = pd.read_excel(DATA_FILE)
        
        # Numeric Coercion
        for col in ['Balance', 'Montants OOS', 'Jours de Stock', 'Valeur Calculee']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0

        # Text Coercion
        for col in ['Site', 'Routes', 'Sous-Zone', 'Noms']:
             if col in df.columns:
                 df[col] = df[col].astype(str).replace('nan', 'Inconnu')
             else:
                 df[col] = 'Inconnu'
        
        # Numero
        if 'Numero' in df.columns:
            df['Numero'] = pd.to_numeric(df['Numero'], errors='coerce').fillna(0).astype('int64')

        return df
    except Exception as e:
        st.error(f"Erreur de chargement: {e}")
        return None

def display_kpi_card(title, value, sub="", color="#212529"):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value" style="color: {color}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def main():
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_column_width=True)
    
    df = load_data()
    if df is None:
        st.error("Données absentes.")
        return

    # Filters
    all_sites = ["Tous"] + sorted(list(df['Site'].dropna().unique()))
    selected_site = st.sidebar.selectbox("Filtre Niveau 1 : Site", all_sites)
    
    df_filtered = df.copy()
    if selected_site != "Tous":
        df_filtered = df[df['Site'] == selected_site]

    # --- Header ---
    st.markdown('<div class="header-style">PILOTAGE DU STOCK MFS</div>', unsafe_allow_html=True)

    # --- MAIN KPIs (Redesigned) ---
    total_balance = df_filtered['Balance'].sum()
    total_oos = df_filtered['Montants OOS'].sum()
    total_pos = len(df_filtered)
    
    pos_rupture = df_filtered[df_filtered['Jours de Stock'] < 0.5].shape[0]
    rupture_rate_val = (pos_rupture / total_pos * 100) if total_pos > 0 else 0
    
    global_days = (total_balance / total_oos) if total_oos > 0 else 0
    sleeping_cash = df_filtered[df_filtered['Jours de Stock'] > 5.0]['Balance'].sum()

    kp1, kp2, kp3, kp4 = st.columns(4)
    with kp1: display_kpi_card("💵 Stock Actuel", f"{total_balance/1_000_000:.1f} M", "FCFA Disponible")
    with kp2: display_kpi_card("🎯 Objectif Cible", f"{total_oos/1_000_000:.1f} M", "Besoin Théorique")
    
    rate_color = "#dc3545" if rupture_rate_val > 20 else "#198754"
    with kp3: display_kpi_card("⚠️ Taux Rupture", f"{rupture_rate_val:.1f}%", f"{pos_rupture} POS Critiques", color=rate_color)
    
    with kp4: display_kpi_card("⏳ Couverture", f"{global_days:.1f} J", "Cible: 1.0 Jour")

    # --- CLUSTER FOCUS (New Request) ---
    st.markdown('<div class="sub-header">🌍 Performance par Cluster (Focus Taux de Rupture)</div>', unsafe_allow_html=True)
    
    # Calculate for Cité Sic and Ndogbong explicitly
    def get_cluster_stats(cluster_name):
        subset = df[df['Site'].astype(str).str.contains(cluster_name, case=False, na=False)]
        if subset.empty: return None
        count = len(subset)
        rupt = subset[subset['Jours de Stock'] < 0.5].shape[0]
        rate = (rupt / count * 100) if count > 0 else 0
        return rate, count, rupt

    c_sic_stats = get_cluster_stats("Cite Sic")
    c_ndog_stats = get_cluster_stats("Ndogbong")
    
    cl1, cl2 = st.columns(2)
    
    if c_sic_stats:
        rate, count, rupt = c_sic_stats
        color_bar = "red" if rate > 20 else "green"
        with cl1:
            st.markdown(f"""
            <div class="cluster-card" style="border-left-color: {color_bar};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin:0; color:#333;">🏙️ CITE SIC</h3>
                        <div style="font-size:12px; color:#777;">{rupt} ruptures sur {count} POS</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:32px; font-weight:bold; color:{color_bar}">{rate:.1f}%</span>
                        <div style="font-size:10px; text-transform:uppercase;">Taux Rupture</div>
                    </div>
                </div>
                <div style="background:#eee; height:8px; width:100%; margin-top:10px; border-radius:4px;">
                    <div style="background:{color_bar}; height:8px; width:{min(rate, 100)}%; border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    if c_ndog_stats:
        rate, count, rupt = c_ndog_stats
        color_bar = "red" if rate > 20 else "green"
        with cl2:
            st.markdown(f"""
            <div class="cluster-card" style="border-left-color: {color_bar};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin:0; color:#333;">🏙️ NDOGBONG</h3>
                        <div style="font-size:12px; color:#777;">{rupt} ruptures sur {count} POS</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:32px; font-weight:bold; color:{color_bar}">{rate:.1f}%</span>
                        <div style="font-size:10px; text-transform:uppercase;">Taux Rupture</div>
                    </div>
                </div>
                <div style="background:#eee; height:8px; width:100%; margin-top:10px; border-radius:4px;">
                    <div style="background:{color_bar}; height:8px; width:{min(rate, 100)}%; border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- Charts Data Prep ---
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

    # --- CHARTS SECTION ---
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown('<div class="sub-header">📊 Distribution État du Parc</div>', unsafe_allow_html=True)
        pie_data = df_filtered['Statut'].value_counts().reset_index()
        pie_data.columns = ['Statut', 'Compte']
        pie_data['Pourcentage'] = (pie_data['Compte'] / pie_data['Compte'].sum()).map("{:.1%}".format)
        
        bars = alt.Chart(pie_data).mark_bar().encode(
            x=alt.X('Compte', title='Nombre de PDV'),
            y=alt.Y('Statut', sort=domain, title=None),
            color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_), legend=None),
            tooltip=['Statut', 'Compte', 'Pourcentage']
        )
        text = bars.mark_text(align='left', baseline='middle', dx=3).encode(text='Pourcentage')
        st.altair_chart((bars + text).properties(height=300), use_container_width=True)

    with c2:
        st.markdown('<div class="sub-header">📍 Top 10 Manques (Cash à Injecter)</div>', unsafe_allow_html=True)
        df_recharge = df_filtered[df_filtered['Manque (Gap)'] > 0].sort_values(by='Manque (Gap)', ascending=False).head(10)
        
        if not df_recharge.empty:
            chart_gap = alt.Chart(df_recharge).mark_bar().encode(
                x=alt.X('Manque (Gap)', title='Montant (FCFA)'),
                y=alt.Y('Noms', sort='-x', title=None),
                color=alt.Color('Jours de Stock', scale=alt.Scale(scheme='redyellowgreen'), title=None),
                tooltip=['Noms', 'Manque (Gap)', 'Site']
            ).properties(height=300)
            st.altair_chart(chart_gap, use_container_width=True)
        else:
            st.info("Aucun manque critique.")

    # Scatter
    st.markdown('<div class="sub-header">📈 Précision Stockage</div>', unsafe_allow_html=True)
    
    under = df_filtered[df_filtered['Balance'] < df_filtered['Montants OOS']].shape[0]
    u_pct = (under / total_pos * 100) if total_pos > 0 else 0
    
    interp = f"🔴 **Attention : {u_pct:.1f}% du parc est sous-stocké.**" if u_pct > 50 else f"🟢 **Bonne nouvelle : Seules {u_pct:.1f}% des POS sont sous-stockés.**"
    st.markdown(f"<div style='background:#fff; padding:10px; border-radius:5px; margin-bottom:10px;'>{interp}</div>", unsafe_allow_html=True)

    chart = alt.Chart(df_filtered).mark_circle(size=60).encode(
        x=alt.X('Montants OOS', title='Objectif'),
        y=alt.Y('Balance', title='Stock Réel'),
        color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_)),
        tooltip=['Noms', 'Balance', 'Montants OOS', 'Site']
    ).properties(height=450).interactive()
    
    line = alt.Chart(pd.DataFrame({'x':[0, df_filtered['Montants OOS'].max()], 'y':[0, df_filtered['Montants OOS'].max()]})).mark_line(strokeDash=[5,5], color='gray').encode(x='x', y='y')
    
    st.altair_chart(chart + line, use_container_width=True)

    # Table
    st.markdown('<div class="sub-header">📋 Détail Réseau</div>', unsafe_allow_html=True)
    st.dataframe(df_filtered[['Numero','Noms','Site','Routes','Balance','Montants OOS','Manque (Gap)','Jours de Stock','Statut']], use_container_width=True)

if __name__ == "__main__":
    main()
