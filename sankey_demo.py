import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# Configuration
DATA_FILE = r'c:\Users\user\Downloads\r2b\reconciliation.xlsx'

st.set_page_config(page_title="Démonstration Sankey", layout="wide")

def load_data():
    if not os.path.exists(DATA_FILE):
        st.error("Fichier de données introuvable.")
        return None
    return pd.read_excel(DATA_FILE)

def main():
    st.title("🔀 Démonstration : Diagramme de Sankey")
    st.markdown("Ce visuel permet de voir **les flux de volume** (Argent) depuis les **Sites** vers les **Statuts de Stock**.")

    df = load_data()
    if df is None: return

    # 1. Classification
    def classify_pos(days):
        if days < 0.5: return "🔴 Rupture"
        if days < 1.0: return "🟠 Tension"
        if days <= 3.0: return "🟢 Confort"
        return "🔵 Surstock"
    
    df['Statut'] = df['Jours de Stock'].apply(classify_pos)

    # 2. Prepare Data for Sankey
    # Flow 1: Site -> Statut
    # We need to aggregate Balance by (Site, Statut)
    df_agg = df.groupby(['Site', 'Statut'])['Balance'].sum().reset_index()

    # Create Nodes
    all_sites = list(df_agg['Site'].unique())
    all_statuses = list(df_agg['Statut'].unique())
    
    # Nodes list
    labels = all_sites + all_statuses
    
    # Map labels to indices
    label_map = {label: i for i, label in enumerate(labels)}
    
    # Create Links
    source = []
    target = []
    value = []
    color_link = []
    
    status_colors = {
        "🔴 Rupture": "rgba(239, 85, 59, 0.4)",
        "🟠 Tension": "rgba(255, 161, 90, 0.4)",
        "🟢 Confort": "rgba(0, 204, 150, 0.4)",
        "🔵 Surstock": "rgba(99, 110, 250, 0.4)"
    }

    for _, row in df_agg.iterrows():
        src_idx = label_map[row['Site']]
        tgt_idx = label_map[row['Statut']]
        
        source.append(src_idx)
        target.append(tgt_idx)
        value.append(row['Balance'])
        color_link.append(status_colors.get(row['Statut'], "grey"))

    # 3. Plot
    fig = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = 0.5),
          label = labels,
          color = "blue"
        ),
        link = dict(
          source = source,
          target = target,
          value = value,
          color = color_link
      ))])

    fig.update_layout(title_text="Flux du Stock : Site -> Statut", font_size=14, height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 **Intérêt :** On voit instantanément quel Site contribue le plus au 'Surstock' (Gros flux bleu) ou à la 'Rupture' (Flux rouge).")

if __name__ == "__main__":
    main()
