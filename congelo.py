import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Stock congélateurs", layout="wide")

# --- STYLE CSS (PROPRE) ---
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    .product-card {
        background-color: white;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 5px;
        border: 1px solid #ddd;
        border-left: 8px solid #ddd;
    }
    .badge-loc {
        font-size: 0.7rem;
        background-color: #e1f5fe;
        color: #0288d1;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .new-label {
        float: right;
        font-size: 0.7rem;
        color: #2e7d32;
        font-weight: bold;
    }
    .card-title { font-size: 1.1rem; font-weight: bold; margin-top: 5px; margin-bottom: 2px; color: black; }
    .card-meta { font-size: 0.75rem; color: #666; }
    div.stButton > button { height: 35px !important; font-weight: bold !important; width: 100%; }
    .qty-display {
        text-align: center; font-weight: bold; font-size: 1.2rem;
        line-height: 35px; background: #f0f2f6; border-radius: 4px; height: 35px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIG GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_CSV = "stock_congelateur.csv"
FILE_CONTENANTS = "contenants.csv"

def save_to_github(file_path, commit_message):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": f"application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        data = {"message": commit_message, "content": content}
        if sha: data["sha"] = sha
        requests.put(url, headers=headers, json=data)

# --- CHARGEMENT DES DONNÉES ---
if os.path.exists(FILE_CSV):
    try:
        df = pd.read_csv(FILE_CSV).fillna("")
        df = df.rename(columns={'nom': 'Nom', 'catégorie': 'Catégorie', 'nombre': 'Nombre', 'lieu': 'Lieu', 'date': 'Date', 'contenant': 'Contenant'})
    except:
        df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])
else:
    df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])

if os.path.exists(FILE_CONTENANTS):
    try:
        df_cont = pd.read_csv(FILE_CONTENANTS)
    except:
        df_cont = pd.DataFrame({"Nom": ["Pyrex", "Tupperware", "Verre Carré"]})
else:
    df_cont = pd.DataFrame({"Nom": ["Pyrex", "Tupperware", "Verre Carré"]})

# --- ACTIONS ---
def update_stock(new_df, msg):
    new_df.to_csv(FILE_CSV, index=False)
    save_to_github(FILE_CSV, msg)
    st.rerun()

def update_contenants(new_df, msg):
    new_df.to_csv(FILE_CONTENANTS, index=False)
    save_to_github(FILE_CONTENANTS, msg)
    st.rerun()

# --- INTERFACE ---
st.title("❄️ Stock congélateurs")

if 'sort_mode' not in st.session_state: st.session_state.sort_mode = "alpha"
if 'last_added_id' not in st.session_state: st.session_state.last_added_id = None

tab1, tab2 = st.tabs(["📦 Stock", "⚙️ Configuration"])

with tab1:
    LOGOS = {"Plat cuisiné": "🍲", "Surgelé": "❄️", "Autre": "📦"}

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", ["Plat cuisiné", "Surgelé", "Autre"])
            loc_a = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
            cont_list = sorted(df_cont["Nom"].tolist())
            cont_a = st.selectbox("Contenant", cont_list)
            q_a = st.number_input("Nombre", min_value=1, step=1)
            
            if st.form_submit_button("Ajouter"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat_a, "Contenant": cont_a, "Lieu": loc_a, "Nombre": int(q_a), "Date": ts}])
                df = pd.concat([df, new_row], ignore_index=True)
                st.session_state.last_added_id = f"{n}_{ts}"
                update_stock(df, f"Ajout {n}")

    # FILTRES
    c_s, c_sort, c_reset = st.columns([4, 1, 1])
    search = c_s.text_input("🔍 Rechercher", key="search_val", label_visibility="collapsed")
    if c_sort.button("⌛"):
        modes = ["alpha", "newest", "oldest"]
        st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
    if c_reset.button("🔄"):
        st.session_state.search_val = ""
        st.session_state.sort_mode = "alpha"
        st.session_state.last_added_id = None
        st.rerun()

    # TRI ET FILTRAGE
    working_df = df.copy()
    if not working_df.empty:
        working_df['Date_dt'] = pd.to_datetime(working_df['Date'], errors='coerce')
        if search: working_df = working_df[working_df['Nom'].str.contains(search, case=False)]
        
        # Tri principal
        if st.session_state.sort_mode == "alpha":
            working_df = working_df.sort_values(by='Nom').reset_index()
        elif st.session_state.sort_mode == "oldest":
            working_df = working_df.sort_values(by=['Date_dt', 'Nom']).reset_index()
        else:
            working_df = working_df.sort_values(by=['Date_dt', 'Nom'], ascending=[False, True]).reset_index()

        # Epinglage du dernier ajouté
        if st.session_state.last_added_id:
            working_df['temp_id'] = working_df['Nom'] + "_" + working_df['Date'].astype(str)
            mask = working_df['temp_id'] == st.session_state.last_added_id
            if mask.any():
                top = working_df[mask]
                bottom = working_df[~mask]
                working_df = pd.concat([top, bottom]).drop(columns=['temp_id'])

    # AFFICHAGE DES CARTES
    if working_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        for _, row in working_df.iterrows():
            idx = row['index']
            # Couleur selon date
            b_color = "#ddd"
            try:
                diff = (datetime.now() - pd.to_datetime(row['Date'])).days
                if diff >= 180: b_color = "#ff4b4b"
                elif diff >= 90: b_color = "#ffa500"
            except: pass
            
            # Détection nouveau
            is_new = (f"{row['Nom']}_{row['Date']}") == st.session_state.last_added_id
            new_tag = '<div class="new-label">✨ NOUVEAU</div>' if is_new else ''
            card_border = "border: 2px solid #2e7d32;" if is_new else ""
            
            # GÉNÉRATION HTML UNIQUE (Anti-bug)
            html_content = f"""
            <div class="product-card" style="border-left: 8px solid {b_color}; {card_border}">
                <span class="badge-loc">📍 {row['Lieu']}</span>
                {new_tag}
                <div class="card-title">{row['Nom']}</div>
                <div class="card-meta">{LOGOS.get(row['Catégorie'], "📦")} {row['Catégorie']} | 📦 {row['Contenant']}</div>
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)
            
            # Boutons de contrôle
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            if col1.button("➖", key=f"min_{idx}"):
                if df.at[idx, 'Nombre'] > 1:
                    df.at[idx, 'Nombre'] -= 1
                    update_stock(df, "Moins")
            col2.markdown(f"<div class='qty-display'>{row['Nombre']}</div>", unsafe_allow_html=True)
            if col3.button("➕", key=f"plus_{idx}"):
                df.at[idx, 'Nombre'] += 1
                update_stock(df, "Plus")
            if col4.button("🍽️ Fini", key=f"fin_{idx}"):
                df = df.drop(idx).reset_index(drop=True)
                st.session_state.last_added_id = None
                update_stock(df, "Consommé")
            st.write("")

with tab2:
    st.subheader("🛠️ Configuration des Contenants")
    with st.form("conf_cont", clear_on_submit=True):
        new_c = st.text_input("Ajouter un type de contenant")
        if st.form_submit_button("Valider"):
            if new_c and new_c not in df_cont["Nom"].values:
                df_cont = pd.concat([df_cont, pd.DataFrame([{"Nom": new_c}])], ignore_index=True)
                update_contenants(df_cont, f"Nouveau contenant: {new_c}")
    
    st.write("---")
    for i, r in df_cont.sort_values("Nom").iterrows():
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"• {r['Nom']}")
        if c_d.button("🗑️", key=f"del_{i}"):
            df_cont = df_cont.drop(i).reset_index(drop=True)
            update_contenants(df_cont, "Suppression contenant")
