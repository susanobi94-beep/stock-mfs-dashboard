import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import os
from datetime import datetime, timedelta

# Configuration
DATA_FILE = 'reconciliation.csv'
HISTORY_FILE = 'history.csv'
LOGO_FILE = 'logo.png'

st.set_page_config(page_title="Cockpit MFS", layout="wide", page_icon="📶")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
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
    .cluster-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
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
    .pareto-box {
        background-color: #e8f4fd;
        border-left: 5px solid #0d6efd;
        padding: 15px;
        margin-top: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    df = None
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
        except Exception as e:
            st.error(f"Erreur chargement CSV: {e}")
            
    if df is None:
        fallback = DATA_FILE.replace('.csv', '.xlsx')
        if os.path.exists(fallback):
             try:
                 df = pd.read_excel(fallback)
             except Exception as e:
                 st.error(f"Erreur chargement XLSX fallback: {e}")
                 return None
        else:
            return None

    # Coercion (Applies to both CSV and XLSX)
    if df is not None:
        for col in ['Balance', 'Montants OOS', 'Jours de Stock', 'Valeur Calculee']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        for col in ['Site', 'Routes', 'Sous-Zone', 'Noms', 'Segment']:
             if col in df.columns:
                 df[col] = df[col].astype(str).replace(['nan', 'NaN', 'None', ''], 'Inconnu')
        if 'Numero' in df.columns:
            df['Numero'] = pd.to_numeric(df['Numero'], errors='coerce').fillna(0).astype('int64')
            
    return df

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return None
    try:
        df_hist = pd.read_csv(HISTORY_FILE)
        df_hist['Date'] = pd.to_datetime(df_hist['Date'])
        return df_hist
    except:
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
        st.info("⌛ En attente de données... Le dossier a été nettoyé. Veuillez patienter pendant la synchronisation ou rafraîchir la page.")
        return

    # Filters
    all_sites = ["Tous"] + sorted(list(df['Site'].dropna().astype(str).unique()))
    selected_site = st.sidebar.selectbox("Filtre Niveau 1 : Site", all_sites)
    
    df_filtered = df.copy()
    if selected_site != "Tous":
        df_filtered = df[df['Site'] == selected_site]
        
    available_routes = ["Tous"] + sorted(list(df_filtered['Routes'].dropna().astype(str).unique()))
    selected_route = st.sidebar.selectbox("Filtre Niveau 2 : Route Distribution", available_routes)
    
    if selected_route != "Tous":
        df_filtered = df_filtered[df_filtered['Routes'] == selected_route]

    available_sz = ["Tous"] + sorted(list(df_filtered['Sous-Zone'].dropna().astype(str).unique()))
    selected_sz = st.sidebar.selectbox("Filtre Niveau 3 : Sous-Zone / PDV", available_sz)
    
    if selected_sz != "Tous":
        df_filtered = df_filtered[df_filtered['Sous-Zone'] == selected_sz]

    # --- Header ---
    st.markdown('<div class="header-style">WAR ROOM : PILOTAGE DU STOCK MFS</div>', unsafe_allow_html=True)

    # --- Calculations ---
    df_filtered['Manque (Gap)'] = df_filtered.apply(lambda row: max(0.0, float(row['Montants OOS']) - float(row['Balance'])), axis=1)
    
    # NEW STATUS LOGIC
    # Rupture: < 10% target
    # Tension: 10% - 40% target
    # Confort: 40% - 120% target
    # Surstock: > 120% target
    def classify_war_room(row):
        try:
            balance = float(row['Balance'])
            target = float(row['Montants OOS'])
            if target <= 0: return "Surstock" # No target means any balance is surplus
            
            ratio = balance / target
            if ratio < 0.10: return "🔴 RUPTURE"
            if ratio < 0.40: return "🟠 TENSION"
            if ratio <= 1.20: return "🟢 CONFORT"
            return "🔵 SURSTOCK"
        except:
            return "UNKNOWN"

    df_filtered['Statut'] = df_filtered.apply(classify_war_room, axis=1)
    
    # Aggregates
    total_balance = df_filtered['Balance'].sum()
    total_oos = df_filtered['Montants OOS'].sum()
    total_pos = len(df_filtered)
    
    pos_rupture = df_filtered[df_filtered['Statut'] == "🔴 RUPTURE"].shape[0]
    pos_tension = df_filtered[df_filtered['Statut'] == "🟠 TENSION"].shape[0]
    rupture_rate_val = (pos_rupture / total_pos * 100) if total_pos > 0 else 0
    manque_a_gagner = df_filtered['Manque (Gap)'].sum()
    
    # --- KPIs ---
    kp1, kp2, kp3, kp4 = st.columns(4)
    
    with kp1: 
        display_kpi_card("⚠️ TAUX DE RUPTURE", f"{rupture_rate_val:.1f}%", f"{pos_rupture} POS < 10% Cible", color="#dc3545")
    
    with kp2:
        tension_pct = (pos_tension / total_pos * 100) if total_pos > 0 else 0
        display_kpi_card("🟠 ZONE DE TENSION", f"{tension_pct:.1f}%", f"{pos_tension} POS à recharger vite", color="#f57c00")
        
    with kp3:
        display_kpi_card("📉 MANQUE À GAGNER", f"{manque_a_gagner/1_000_000:.2f} M", "FCFA à Injecter", color="#212529")
    
    with kp4:
        global_days = (total_balance / total_oos) if total_oos > 0 else 0
        display_kpi_card("⏳ COUVERTURE", f"{global_days:.1f} J", "Cible Marché: 1.0 J")

    # --- CLUSTER FOCUS ---
    st.markdown('<div class="sub-header">🌍 Performance par Cluster</div>', unsafe_allow_html=True)
    
    def get_cluster_stats(cluster_name):
        subset = df_filtered[df_filtered['Site'].astype(str).str.contains(cluster_name, case=False, na=False)]
        if subset.empty: return None
        count = len(subset)
        rupt_df = subset[subset['Statut'] == "🔴 RUPTURE"]
        rupt = rupt_df.shape[0]
        rate = (rupt / count * 100) if count > 0 else 0
        
        # Segments stats
        stats_dict = {'rate': rate, 'count': count, 'rupt': rupt}
        if 'Segment' in subset.columns:
            stats_dict['hvc_out'] = rupt_df[rupt_df['Segment'] == 'HVC'].shape[0]
            stats_dict['hvc_tot'] = subset[subset['Segment'] == 'HVC'].shape[0]
            stats_dict['mvc_out'] = rupt_df[rupt_df['Segment'] == 'MVC'].shape[0]
            stats_dict['mvc_tot'] = subset[subset['Segment'] == 'MVC'].shape[0]
            stats_dict['lvc_out'] = rupt_df[rupt_df['Segment'] == 'LVC'].shape[0]
            stats_dict['lvc_tot'] = subset[subset['Segment'] == 'LVC'].shape[0]
        else:
            stats_dict['hvc_out'] = stats_dict['hvc_tot'] = 0
            stats_dict['mvc_out'] = stats_dict['mvc_tot'] = 0
            stats_dict['lvc_out'] = stats_dict['lvc_tot'] = 0
            
        return stats_dict

    c_sic_stats = get_cluster_stats("Cite Sic")
    c_ndog_stats = get_cluster_stats("Ndogbong")
    
    cl1, cl2 = st.columns(2)
    
    def render_cluster_card(name, stats):
        rate = stats['rate']
        count = stats['count']
        rupt = stats['rupt']
        color_bar = "red" if rate > 20 else "green"
        
        # Small HTML for segments
        segments_html = f"""
        <div style="display:flex; justify-content:space-between; margin-top:12px; font-size:11px; color:#555; text-align:center;">
            <div style="flex:1;"><b>HVC:</b> <span style="color:#dc3545;">{stats['hvc_out']}</span> / {stats['hvc_tot']}</div>
            <div style="flex:1; border-left:1px solid #ccc; border-right:1px solid #ccc;"><b>MVC:</b> <span style="color:#dc3545;">{stats['mvc_out']}</span> / {stats['mvc_tot']}</div>
            <div style="flex:1;"><b>LVC:</b> <span style="color:#dc3545;">{stats['lvc_out']}</span> / {stats['lvc_tot']}</div>
        </div>
        """
        
        st.markdown(f"""
        <div class="cluster-card" style="border-left-color: {color_bar};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h3 style="margin:0; color:#333;">🌐 {name}</h3>
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
            {segments_html}
        </div>
        """, unsafe_allow_html=True)

    with cl1:
        if c_sic_stats: render_cluster_card("CITE SIC", c_sic_stats)
    with cl2:
        if c_ndog_stats: render_cluster_card("NDOGBONG", c_ndog_stats)

    # --- ROUTE PERFORMANCE ---
    st.markdown('<div class="sub-header">🛣️ Taux de Rupture par Routes</div>', unsafe_allow_html=True)
    
    route_stats = df_filtered.groupby('Routes').apply(
        lambda x: pd.Series({
            'Total POS': len(x),
            'Ruptures': x[x['Statut'] == "🔴 RUPTURE"].shape[0]
        })
    ).reset_index()
    
    route_stats['Taux Rupture'] = (route_stats['Ruptures'] / route_stats['Total POS'] * 100).fillna(0)
    route_stats = route_stats.sort_values(by='Taux Rupture', ascending=False)
    
    if not route_stats.empty:
        chart_routes = alt.Chart(route_stats).mark_bar().encode(
            x=alt.X('Taux Rupture', title='Taux de Rupture (%)'),
            y=alt.Y('Routes', sort='-x', title=None),
            color=alt.condition(
                alt.datum['Taux Rupture'] > 20,
                alt.value('#dc3545'),
                alt.value('#198754')
            ),
            tooltip=['Routes', 'Total POS', 'Ruptures', alt.Tooltip('Taux Rupture', format='.1f')]
        ).properties(height=max(300, len(route_stats) * 30))
        
        text_routes = chart_routes.mark_text(
            align='left',
            baseline='middle',
            dx=3
        ).encode(
            text=alt.Text('Taux Rupture', format='.1f')
        )
        
        st.altair_chart(chart_routes + text_routes, use_container_width=True)
    else:
        st.info("Pas de données de routes disponibles.")

    # --- MATRICE DE PRIORITÉ MFS (BUBBLE CHART) ---
    st.markdown('<div class="sub-header">📊 Matrice de Priorité MFS (Cible vs Réalisation)</div>', unsafe_allow_html=True)
    
    if not df_filtered.empty:
        # AGGREGATE BY ROUTE
        df_route_matrix = df_filtered.groupby('Routes').apply(
            lambda x: pd.Series({
                'Montants OOS': x['Montants OOS'].sum(),
                'Balance': x['Balance'].sum(),
                'Manque (Gap)': x['Manque (Gap)'].sum(),
                'Ruptures': x[x['Statut'] == "🔴 RUPTURE"].shape[0],
                'Total POS': len(x)
            })
        ).reset_index()

        # Calculate Rupture Rate (Y axis): (POS in Rupture / Total POS) * 100
        df_route_matrix['Taux de Rupture (%)'] = (df_route_matrix['Ruptures'] / df_route_matrix['Total POS'] * 100).fillna(0)
        
        # Quadrant Separators
        x_sep = df_route_matrix['Montants OOS'].median() if not df_route_matrix['Montants OOS'].empty else 0
        y_sep = 20.0 # Standard threshold
        
        fig_matrix = px.scatter(
            df_route_matrix,
            x='Montants OOS',
            y='Taux de Rupture (%)',
            size='Manque (Gap)',
            color='Routes',
            hover_name='Routes',
            text='Routes',
            labels={'Montants OOS': 'Volume Cible Total (FCFA)', 'Taux de Rupture (%)': 'Taux de Rupture (%)'},
            size_max=60,
            template='plotly_white',
            range_y=[105, -5] # INVERTED: 0% at Top, 100% at Bottom
        )
        
        # Quadrant Annotations (P1-P4)
        # Inverted Scale: P3/P4 (Good) at Top (< 20%), P1/P2 (Bad) at Bottom (> 20%)
        max_x = df_route_matrix['Montants OOS'].max() * 1.1 if not df_route_matrix.empty else 100
        fig_matrix.add_annotation(x=max_x*0.75, y=10, text="P3", showarrow=False, font=dict(size=50, color="rgba(0,0,0,0.05)"))
        fig_matrix.add_annotation(x=max_x*0.25, y=10, text="P4", showarrow=False, font=dict(size=50, color="rgba(0,0,0,0.05)"))
        fig_matrix.add_annotation(x=max_x*0.75, y=80, text="P1", showarrow=False, font=dict(size=50, color="rgba(0,0,0,0.05)"))
        fig_matrix.add_annotation(x=max_x*0.25, y=80, text="P2", showarrow=False, font=dict(size=50, color="rgba(0,0,0,0.05)"))
        
        # Custom Ticks for Y axis
        fig_matrix.update_layout(
            yaxis = dict(
                tickmode = 'array',
                tickvals = [0, 5, 10, 15, 20, 40, 60, 80, 100],
                ticktext = ['0%', '5%', '10%', '15%', '20%', '40%', '60%', '80%', '100%']
            )
        )
        
        # Add Separator Lines
        fig_matrix.add_hline(y=y_sep, line_dash="dash", line_color="#dc3545", line_width=2, opacity=0.8)
        fig_matrix.add_vline(x=x_sep, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Highlight Crisis Zone (P1: Bottom Right)
        # Since axis is inverted, Y goes from y_sep(20) down to 100
        fig_matrix.add_vrect(x0=x_sep, x1=max_x, y0=y_sep, y1=100, fillcolor="red", opacity=0.08, layer="below", line_width=0)

        fig_matrix.update_layout(height=600)
        st.plotly_chart(fig_matrix, use_container_width=True)
    else:
        st.info("Aucune donnée pour la matrice.")

    # --- Charts Data Prep ---
    df_filtered['Manque (Gap)'] = df_filtered.apply(lambda row: max(0.0, float(row['Montants OOS']) - float(row['Balance'])), axis=1)
    
    def classify_chart(days):
        try:
            d = float(days)
            if d < 0.5: return "Rupture"
            if d < 1.0: return "Tension"
            if d <= 3.0: return "Confort"
            return "Surstock"
        except:
            return "Erreur"
            
    domain = ["🔴 RUPTURE", "🟠 TENSION", "🟢 CONFORT", "🔵 SURSTOCK", "UNKNOWN"]
    range_ = ["#d32f2f", "#f57c00", "#2e7d32", "#1976d2", "gray"]

    # --- CHARTS ROW 1 ---
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown('<div class="sub-header">📊 Distribution du Parc</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="sub-header">📍 Top 10 Manques (Float à Injecter)</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="sub-header">📈 Précision Stockage</div>', unsafe_allow_html=True)
    
    under = df_filtered[df_filtered['Balance'] < df_filtered['Montants OOS']].shape[0]
    u_pct = (under / total_pos * 100) if total_pos > 0 else 0
    interp = f"🔴 **Attention : {u_pct:.1f}% du parc est sous-stocké.**" if u_pct > 50 else f"🟢 **Seules {u_pct:.1f}% des POS sont sous-stockés.**"
    st.markdown(f"<div style='background:#fff; padding:10px; border-radius:5px; margin-bottom:10px;'>{interp}</div>", unsafe_allow_html=True)

    chart = alt.Chart(df_filtered).mark_circle(size=60).encode(
        x=alt.X('Montants OOS', title='Objectif'),
        y=alt.Y('Balance', title='Stock Réel'),
        color=alt.Color('Statut', scale=alt.Scale(domain=domain, range=range_)),
        tooltip=['Noms', 'Balance', 'Montants OOS', 'Site']
    ).properties(height=450).interactive()
    line = alt.Chart(pd.DataFrame({'x':[0, df_filtered['Montants OOS'].max()], 'y':[0, df_filtered['Montants OOS'].max()]})).mark_line(strokeDash=[5,5], color='gray').encode(x='x', y='y')
    st.altair_chart(chart + line, use_container_width=True)

    # --- PARETO ANALYSIS ---
    st.markdown('<div class="sub-header">📉 Analyse Pareto (Loi 80/20) - Priorités de Rechargement</div>', unsafe_allow_html=True)
    
    df_pareto = df_filtered[df_filtered['Manque (Gap)'] > 0].sort_values(by='Manque (Gap)', ascending=False).copy()
    
    if not df_pareto.empty:
        total_gap = df_pareto['Manque (Gap)'].sum()
        df_pareto['Cum_Gap'] = df_pareto['Manque (Gap)'].cumsum()
        df_pareto['Cum_Percent'] = (df_pareto['Cum_Gap'] / total_gap * 100)
        
        pareto_cutoff = df_pareto[df_pareto['Cum_Percent'] <= 80]
        vital_few_count = len(pareto_cutoff)
        vital_few_amount = pareto_cutoff['Manque (Gap)'].sum()
        
        st.markdown(f"""
        <div class="pareto-box">
            <h4>💡 Insight Décisionnel</h4>
            En rechargeant seulement <b>{vital_few_count} Points de Vente</b> (sur {len(df_pareto)} en manque), 
            vous résolvez <b>80%</b> du problème de liquidité (soit {vital_few_amount:,.0f} FCFA).
        </div>
        """, unsafe_allow_html=True)

        base = alt.Chart(df_pareto.head(50)).encode(x=alt.X('Noms', sort=None, title='POS'))
        bar = base.mark_bar(color='#0d6efd').encode(y=alt.Y('Manque (Gap)', title='Manque Float'))
        line = base.mark_line(color='#dc3545', strokeWidth=3).encode(
            y=alt.Y('Cum_Percent', title='% Cumulé', scale=alt.Scale(domain=[0, 100]))
        )
        threshold = alt.Chart(pd.DataFrame({'y': [80]})).mark_rule(color='green', strokeDash=[5,5]).encode(y='y')
        st.altair_chart((bar + line + threshold).resolve_scale(y='independent'), use_container_width=True)

        st.markdown('**📋 Liste des Priorités Absolues ("Vital Few" - Top 80%)**')
        def get_detailed_status(row):
             gap = float(row['Manque (Gap)'])
             return f"🔴 Recharger {gap:,.0f} F"
        df_pareto['Action'] = df_pareto.apply(get_detailed_status, axis=1)
        
        # Download Button Pareto (UPDATED WITH ROUTES)
        csv_pareto = df_pareto[['Numero', 'Noms', 'Site', 'Routes', 'Manque (Gap)', 'Cum_Percent', 'Action']].head(vital_few_count + 5).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger la Liste Pareto (CSV)",
            data=csv_pareto,
            file_name='pareto_priorities.csv',
            mime='text/csv',
        )
        
        st.dataframe(df_pareto[['Numero', 'Noms', 'Site', 'Routes', 'Manque (Gap)', 'Cum_Percent', 'Action']].head(vital_few_count + 5), use_container_width=True)
    else:
        st.success("✅ Tout est en ordre. Pas de Pareto nécessaire.")

    # --- TABLE DETAIL ---
    st.markdown('<div class="sub-header">📊 Priorités d\'Action Tactique (Top Urgences)</div>', unsafe_allow_html=True)
    
    # Priority sorting: Rupture first, then Tension, then by Gap Size
    status_order = {"🔴 RUPTURE": 0, "🟠 TENSION": 1, "🟢 CONFORT": 2, "🔵 SURSTOCK": 3, "UNKNOWN": 4}
    df_filtered['Sort_Order'] = df_filtered['Statut'].map(status_order)
    
    df_action = df_filtered.sort_values(by=['Sort_Order', 'Manque (Gap)'], ascending=[True, False])
    
    # Formatting for display
    display_cols = ['Numero', 'Noms', 'Site', 'Routes', 'Balance', 'Montants OOS', 'Statut']
    
    # Download Button
    csv_action = df_action[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger le Plan de Route Commercial (CSV)",
        data=csv_action,
        file_name='plan_route_commercial.csv',
        mime='text/csv',
    )
    
    st.dataframe(
        df_action[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Balance": st.column_config.NumberColumn(format="%d F"),
            "Montants OOS": st.column_config.NumberColumn(format="%d F"),
            "Statut": st.column_config.TextColumn(width="medium")
        }
    )

    # --- HISTORY CHART ---
    st.markdown('<div class="sub-header">📅 Évolution Historique du Stock</div>', unsafe_allow_html=True)
    df_hist = load_history()
    
    if df_hist is not None and not df_hist.empty:
        min_date = df_hist['Date'].min().date()
        max_date = df_hist['Date'].max().date()
        c_date1, c_date2 = st.columns([1, 3])
        with c_date1:
             start_date = st.date_input("Date Début", min_date, min_value=min_date, max_value=max_date)
             end_date = st.date_input("Date Fin", max_date, min_value=min_date, max_value=max_date)
        
        mask = (df_hist['Date'].dt.date >= start_date) & (df_hist['Date'].dt.date <= end_date)
        df_hist_filtered = df_hist.loc[mask]
        
        base = alt.Chart(df_hist_filtered).encode(x=alt.X('Date', title='Date'))
        line_stock = base.mark_line(color='#0d6efd').encode(y=alt.Y('Total_Balance', title='Stock Global'))
        line_rupture = base.mark_line(color='#dc3545', strokeDash=[5, 5]).encode(y=alt.Y('Rupture_Rate', title='Taux Rupture (%)'))

        st.altair_chart((line_stock + line_rupture).resolve_scale(y='independent'), use_container_width=True)
    else:
        st.info("Aucun historique disponible.")

if __name__ == "__main__":
    main()
