import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Configuration
# Configuration
# Use relative paths for deployment
DATA_FILE = 'reconciliation.xlsx'
LOGO_FILE = 'logo.png'

st.set_page_config(page_title="Cockpit MFS", layout="wide", page_icon="📶")

# --- CUSTOM CSS FOR TABLEAU-LIKE LOOK ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Card Style - Responsive */
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 20px;
        height: 100%; /* Fill column height */
    }
    .metric-title {
        font-size: 14px;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 24px; /* Slightly smaller for mobile safety */
        font-weight: bold;
        color: #2c3e50;
    }
    @media (min-width: 768px) {
        .metric-value {
            font-size: 32px;
        }
    }
    .metric-delta {
        font-size: 14px;
        color: #28a745;
    }
    .metric-delta.neg {
        color: #dc3545;
    }
    
    /* Chart Container */
    .chart-container {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Header - Responsive */
    .header-style {
        font-size: 40px; /* Default for mobile */
        font-weight: 900;
        color: #000000;
        text-align: center;
        padding-bottom: 30px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    @media (min-width: 768px) {
        .header-style {
            font-size: 85px; /* Large for desktop */
        }
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #000000;
        color: #ffffff;
    }
    [data-testid="stSidebar"] .css-17lntkn { /* Streamlit specific classes */
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        return pd.read_excel(DATA_FILE)
    except:
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
    # Sidebar Logo
    if os.path.exists(LOGO_FILE):
        # NOTE: Using use_column_width for compatibility with older Streamlit versions (1.31.x on HF)
        st.sidebar.image(LOGO_FILE, use_column_width=True)
    
    st.sidebar.markdown("<h3 style='color: white;'>Filtres</h3>", unsafe_allow_html=True)
    
    df = load_data()
    if df is None:
        st.error("Données non trouvées.")
        return

    # Filters
    # Hierarchy: Site -> Routes (Rte_X) -> Sous-Zone (SITENAME)
    
    # 1. Site Filter
    # Ensure columns exist, fill with default if not
    if 'Site' not in df.columns: df['Site'] = 'Unknown'
    if 'Routes' not in df.columns: df['Routes'] = 'Unknown'
    if 'Sous-Zone' not in df.columns: df['Sous-Zone'] = 'Unknown'

    all_sites = ["Tous"] + sorted(list(df['Site'].astype(str).dropna().unique()))
    selected_site = st.sidebar.selectbox("Site", all_sites)
    
    if selected_site != "Tous":
        df_filtered = df[df['Site'] == selected_site]
    else:
        df_filtered = df.copy()

    # 2. Route Filter (Distribution Routes: Rte_0...Rte_8)
    available_routes = ["Tous"] + sorted(list(df_filtered['Routes'].astype(str).unique()))
    selected_route = st.sidebar.selectbox("Route Distribution", available_routes)
    
    if selected_route != "Tous":
        df_filtered = df_filtered[df_filtered['Routes'] == selected_route]
            
    # 3. Sous-Zone Filter (formerly called Routes/SITENAME in dashboard)
    # Filter based on current selection
    valid_sous_zones = df_filtered['Sous-Zone'].dropna().unique()
    available_sous_zones = ["Tous"] + sorted(list(valid_sous_zones))
    
    # Only show filter if there are choices
    if len(available_sous_zones) > 2: # 'Tous' + at least 2 options
         selected_sous_zone = st.sidebar.selectbox("Sous-Zone / PDV", available_sous_zones)
         if selected_sous_zone != "Tous":
            df_filtered = df_filtered[df_filtered['Sous-Zone'] == selected_sous_zone]

    # --- Header ---
    st.markdown('<p class="header-style">Pilotage du Stock MFS <span style="color:#FFCC00;">●</span></p>', unsafe_allow_html=True)

    # --- KPIs (Custom HTML) ---
    total_balance = df_filtered['Balance'].sum()
    total_oos = df_filtered['Montants OOS'].sum()
    sleeping_cash = df_filtered[df_filtered['Jours de Stock'] > 5.0]['Balance'].sum()
    
    # --- New Rupture Calculation for Interpretation --- 
    total_pos = len(df_filtered)
    pos_rupture = df_filtered[df_filtered['Jours de Stock'] < 0.5].shape[0]
    rupture_rate_val = (pos_rupture / total_pos * 100) if total_pos > 0 else 0
    
    global_days = (total_balance / total_oos) if total_oos > 0 else 0

    # Streamlit columns stack on mobile automatically
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: metric_card("Stock Actuel", f"{total_balance/1_000_000:.1f}M", "FCFA")
    with col2: metric_card("Objectif Stock", f"{total_oos/1_000_000:.1f}M", "FCFA")
    
    # Rupture Rate Card (Replaces generic Points de Rupture for better KPI)
    # Or keep Points and replace Days? User specifically asked for Rate.
    # Let's replace 'POS en Rupture' to 'Taux Rupture' or keep POS and move Rate to replace 'Couverture'.
    # User focused on Rate < 20%. Let's put Rate in Col3.
    rate_color = "#dc3545" if rupture_rate_val > 20 else "#28a745" # Red if > 20%, Green otherwise
    with col3: metric_card("Taux Rupture", f"{rupture_rate_val:.1f}%", "Cible: < 20%", color=rate_color)
    
    with col4: metric_card("Cash Dormant", f"{sleeping_cash/1_000_000:.1f}M", "> 5 Jours", color="#ffc107") # Warning Color
    with col5: metric_card("Couverture Globale", f"{global_days:.1f}j", "Cible: 1.0j")

    # --- Decision Support / Interpretation Banner ---
    st.markdown("---")
    if rupture_rate_val > 20:
        st.error(f"⚠️ **ALERTE CRITIQUE : Le Taux de Rupture est de {rupture_rate_val:.1f}% (> 20%).** \n\n"
                 f"Il est impératif de réapprovisionner les {pos_rupture} points de vente en rupture immédiatement pour éviter une perte de chiffre d'affaires.")
    else:
        st.success(f"✅ **PERFORMANCE : Le Taux de Rupture est maîtrisé à {rupture_rate_val:.1f}% (< 20%).** \n\n"
                   "Maintenez le suivi pour rester sous l'objectif.")
    st.markdown("---")
    
    # --- Cluster Focus (If 'Tous' is selected) ---
    # Only show if we are viewing 'All' to avoid confusion if filtered
    if selected_site == "Tous":
        # Helper for mini-card
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
        
        # Filter for specific clusters (fuzzy matching to be safe)
        c_sic = df[df['Site'].str.contains("Cite Sic", case=False, na=False)]
        c_ndog = df[df['Site'].str.contains("Ndogbong", case=False, na=False)]
        
        with cols[0]: 
            if not c_sic.empty: quick_kpi(c_sic, "Cité Sic")
            else: st.info("Cluster 'Cité Sic' non trouvé.")
            
        with cols[1]: 
            if not c_ndog.empty: quick_kpi(c_ndog, "Ndogbong")
            else: st.info("Cluster 'Ndogbong' non trouvé.")
            
    # --- Charts with Container Style ---
    
    # Row 1: TreeMap & Pie
    # On mobile, we might want these full width. Streamlit columns adapt well.
    c1, c2 = st.columns([2, 1])
    
    # Prepare Data
    df_filtered['Manque (Gap)'] = df_filtered.apply(lambda row: max(0, row['Montants OOS'] - row['Balance']), axis=1)
    df_recharge = df_filtered[df_filtered['Manque (Gap)'] > 0]
    
    def classify_pos(days):
        if days < 0.5: return "🔴 Rupture"
        if days < 1.0: return "🟠 Tension"
        if days <= 3.0: return "🟢 Confort"
        return "🔵 Surstock"
    df_filtered['Statut'] = df_filtered['Jours de Stock'].apply(classify_pos)
    category_order = ["🔴 Rupture", "🟠 Tension", "🟢 Confort", "🔵 Surstock"]
    colors_map = {"🔴 Rupture": "#d32f2f", "🟠 Tension": "#f57c00", "🟢 Confort": "#2e7d32", "🔵 Surstock": "#1976d2"}

    with c1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📍 Où manque-t-il de l'argent ?")
        if not df_recharge.empty:
            # Hierarchy: Site -> Routes -> Sous-Zone -> Noms
            path_hierarchy = [px.Constant("Parc"), 'Site', 'Routes', 'Sous-Zone', 'Noms']
            
            fig_tree = px.treemap(
                df_recharge,
                path=path_hierarchy,
                values='Manque (Gap)',
                color='Jours de Stock',
                color_continuous_scale='RdYlGn',
                range_color=[0, 1.5],
            )
            fig_tree.update_layout(height=450, margin=dict(t=20, l=10, r=10, b=10))
            # use_container_width=True IS supported for charts in older versions
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.success("Aucun manque de stock détecté.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📊 État du Parc")
        pie_data = df_filtered['Statut'].value_counts().reset_index()
        pie_data.columns = ['Statut', 'Compte']
        fig_pie = px.pie(
            pie_data, 
            values='Compte', 
            names='Statut',
            color='Statut',
            color_discrete_map=colors_map,
            category_orders={'Statut': category_order},
            hole=0.4
        )
        fig_pie.update_layout(height=450, showlegend=True, legend=dict(orientation="h", y=-0.1))
        # use_container_width=True IS supported for charts in older versions
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Row 2: Scatter (Full Width)
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("📈 Précision du Stockage (Balance vs Cible)")
    fig_scatter = px.scatter(
        df_filtered, 
        x='Montants OOS', 
        y='Balance', 
        color='Statut',
        size='Balance', 
        hover_name='Noms',
        hover_data=['Site', 'Routes', 'Sous-Zone', 'Numero', 'Jours de Stock'],
        color_discrete_map=colors_map,
        category_orders={'Statut': category_order},
        opacity=0.8
    )
    max_val = max(df_filtered['Montants OOS'].max(), df_filtered['Balance'].max()) if not df_filtered.empty else 100
    fig_scatter.add_shape(type="line", line=dict(dash='dash', color='gray'), x0=0, y0=0, x1=max_val, y1=max_val)
    fig_scatter.update_layout(
        height=500, 
        template="plotly_white",
        xaxis_title="Besoin (OOS)",
        yaxis_title="Stock Actuel (Balance)",
        legend=dict(orientation="h", y=1.02, x=0.8)
    )
    # use_container_width=True IS supported for charts in older versions
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Row 3: Action Table
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.subheader("📋 État Complet du Réseau") # Changed title slightly
    
    df_table = df_filtered.copy()
    def get_action(gap):
        return f"⚠️ RECHARGER {gap:,.0f}" if gap > 0 else "✅ OK"
    
    df_table['Action'] = df_table['Manque (Gap)'].apply(get_action)
    
    # Sort by Gap descending so urgent items are first, but keep ALL rows (including OK)
    df_table = df_table.sort_values(by='Manque (Gap)', ascending=False)
    
    # Columns to display
    display_cols = ['Numero', 'Noms', 'Site', 'Routes', 'Sous-Zone', 'Balance', 'Montants OOS', 'Jours de Stock', 'Action']
    # Filter only available columns
    display_cols = [c for c in display_cols if c in df_table.columns]

    st.dataframe(
        df_table[display_cols],
        # use_container_width=True IS supported for dataframes in older versions (since ~1.2x)
        use_container_width=True,
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
