import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Congélo - Design Cartes", layout="wide")

# --- NOUVEAU CSS STYLE "CARTES" ---
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    
    /* Style de la carte */
    .product-card {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    
    .badge-loc {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 5px;
        font-size: 0.7rem;
        background-color: #f0f2f6;
        color: #555;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    .card-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin: 5px 0;
        color: #1f1f1f;
    }
    
    .card-meta {
        font-size: 0.75rem;
        color: #777;
        margin-bottom: 10px;
    }
    
    /* Alignement des boutons Streamlit pour qu'ils s'intègrent à la carte */
    div.stButton > button {
        height: 35px !important;
        padding: 0 !important;
    }
    
    .qty-display {
        background: #f8f9fa;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
        line-height: 35px;
        border: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIG GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_CSV = "stock_congelateur.csv"

def save_to_github(file_path, commit_message):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        data = {"message": commit_message, "content": content}
        if sha: data["sha"] = sha
        requests.put(url, headers=headers, json=data)

# --- CHARGEMENT ---
if os.path.exists(FILE_CSV):
    df = pd.read_csv(FILE_CSV).fillna("")
    mapping = {'nom': 'Nom', 'catégorie': 'Catégorie', 'nombre': 'Nombre', 'lieu': 'Lieu', 'date': 'Date', 'contenant': 'Contenant'}
    df = df.rename(columns=mapping)
else:
    df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])

def update_stock(new_df, msg):
    new_df.to_csv(FILE_CSV, index=False)
    save_to_github(FILE_CSV, msg)
    st.rerun()

def reset_all():
    st.session_state.search_val = ""
    st.session_state.cat_val = "Toutes"
    st.session_state.loc_val = "Tous"
    st.session_state.sort_mode = "alpha"

LOGOS_CAT = {"Plat cuisiné": "🍲", "Surgelé": "❄️", "Autre": "📦"}
if 'sort_mode' not in st.session_state: st.session_state.sort_mode = "alpha"

# --- INTERFACE ---
st.title("❄️ Mon Stock")

with st.expander("➕ Nouveau produit"):
    with st.form("ajout", clear_on_submit=True):
        n = st.text_input("Nom")
        c1, c2 = st.columns(2)
        cat_a = c1.selectbox("Catégorie", ["Plat cuisiné", "Surgelé", "Autre"])
        loc_a = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
        cont_a = st.selectbox("Contenant", ["Couvercle rouge", "Couvercle vert", "Grand bleu", "Petit bleu", "Plastique blanc", "Préemballage", "Pyrex", "Tupperware", "Verre Carré", "Moyen bleu"])
        q_a = st.number_input("Nombre", min_value=1, step=1)
        if st.form_submit_button("Ajouter"):
            new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat_a, "Contenant": cont_a, "Lieu": loc_a, "Nombre": int(q_a), "Date": datetime.now().strftime("%Y-%m-%d")}])
            df = pd.concat([df, new_row], ignore_index=True)
            update_stock(df, f"Ajout {n}")

# FILTRES
c_s, c_sort, c_r = st.columns([4, 1, 1])
recherche = c_s.text_input("🔍", placeholder="Chercher...", key="search_val", label_visibility="collapsed")
if c_sort.button("⌛"):
    modes = ["alpha", "oldest", "newest"]
    st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
c_r.button("🔄", on_click=reset_all)

# LOGIQUE DE TRI
def get_status(date_str):
    if not date_str: return "transparent"
    try:
        diff = (datetime.now() - datetime.strptime(str(date_str).split(" ")[0], "%Y-%m-%d")).days
        if diff >= 180: return "#ff4b4b"
        if diff >= 90: return "#ffa500"
        return "transparent"
    except: return "transparent"

d_f = df.copy()
if not d_f.empty:
    d_f['Date_dt'] = pd.to_datetime(d_f['Date'], errors='coerce')
    if st.session_state.sort_mode == "alpha": d_f = d_f.sort_values(by='Nom').reset_index()
    elif st.session_state.sort_mode == "oldest": d_f = d_f.sort_values(by=['Date_dt', 'Nom'], na_position='last').reset_index()
    else: d_f = d_f.sort_values(by=['Date_dt', 'Nom'], ascending=False, na_position='last').reset_index()

if recherche: d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if st.session_state.cat_val != "Toutes": d_f = d_f[d_f['Catégorie'] == st.session_state.cat_val]
if st.session_state.loc_val != "Tous": d_f = d_f[d_f['Lieu'] == st.session_state.loc_val]

st.divider()

# --- AFFICHAGE EN GRILLE DE CARTES ---
if d_f.empty:
    st.info("Aucun produit trouvé.")
else:
    # Sur ordinateur : 3 colonnes, sur mobile : Streamlit empile automatiquement
    cols = st.columns(1) # On peut changer en st.columns(3) pour forcer le PC, mais 1 est plus stable pour le test
    
    for i, row in d_f.iterrows():
        idx = row['index']
        color = get_status(row['Date'])
        logo = LOGOS_CAT.get(row['Catégorie'], "📦")
        
        # Début de la carte (Conteneur HTML)
        st.markdown(f"""
            <div class="product-card" style="border-left: 8px solid {color};">
                <div class="badge-loc">📍 {row['Lieu']}</div>
                <div class="card-title">{row['Nom']}</div>
                <div class="card-meta">{logo} {row['Catégorie']} | 📦 {row['Contenant']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Boutons d'action sous la carte
        c_m, c_v, c_p, c_e = st.columns([1, 1, 1, 1.5])
        
        if c_m.button("➖", key=f"m_{idx}"):
            if df.at[idx, 'Nombre'] > 1:
                df.at[idx, 'Nombre'] -= 1
                update_stock(df, f"Maj {row['Nom']}")
        
        c_v.markdown(f"<div class='qty-display'>{row['Nombre']}</div>", unsafe_allow_html=True)
        
        if c_p.button("➕", key=f"p_{idx}"):
            df.at[idx, 'Nombre'] += 1
            update_stock(df, f"Maj {row['Nom']}")
            
        if c_e.button("🍽️ Fini", key=f"e_{idx}"):
            df = df.drop(idx).reset_index(drop=True)
            update_stock(df, f"Consommé {row['Nom']}")
        
        st.write("") # Petit espace entre les cartes
