import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Congélo", layout="wide")

# --- CSS MOBILE REVISITÉ (Boutons style Lien) ---
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    
    /* On transforme les boutons en simples zones cliquables sans bordure */
    div.stButton > button {
        border: none !important;
        background-color: transparent !important;
        color: #007BFF !important; /* Couleur bleu lien */
        font-size: 1.8rem !important; /* Très grand pour cliquer facilement */
        font-weight: bold !important;
        padding: 0 !important;
        margin: 0 !important;
        height: 40px !important;
        box-shadow: none !important;
    }
    
    /* Style spécial pour le bouton Poubelle (P) */
    div.stButton > button[key^="d_"] {
        color: #ff4b4b !important;
        font-size: 1.2rem !important;
    }

    hr { margin: 0.3rem 0 !important; }
    .prod-name { font-size: 1rem; font-weight: bold; line-height: 1.1; }
    .prod-details { font-size: 0.75rem; color: #666; line-height: 1; }
    
    .qty-text { 
        font-size: 1.2rem; 
        font-weight: bold; 
        text-align: center; 
        line-height: 40px;
        color: #333;
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

# --- INTERFACE ---
st.title("❄️ Mon Congélateur")

with st.expander("➕ Nouveau produit"):
    with st.form("ajout", clear_on_submit=True):
        n = st.text_input("Nom")
        c1, c2 = st.columns(2)
        cat_a = c1.selectbox("Cat", ["Plat cuisiné", "Surgelé", "Autre"])
        loc_a = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
        cont_a = st.selectbox("Contenant", ["Couvercle rouge", "Couvercle vert", "Grand bleu", "Petit bleu", "Plastique blanc", "Préemballage", "Pyrex", "Tupperware", "Verre Carré", "Moyen bleu"])
        q_a = st.number_input("Nombre", min_value=1, step=1)
        if st.form_submit_button("Ajouter"):
            new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat_a, "Contenant": cont_a, "Lieu": loc_a, "Nombre": int(q_a), "Date": datetime.now().strftime("%Y-%m-%d")}])
            df = pd.concat([df, new_row], ignore_index=True)
            update_stock(df, f"Ajout {n}")

# FILTRES
c_s, c_r = st.columns([5, 1])
recherche = c_s.text_input("🔍", placeholder="Rechercher...", key="search_val", label_visibility="collapsed")
c_r.button("🔄", on_click=reset_all)

f1, f2 = st.columns(2)
f_cat = f1.selectbox("Cat", ["Toutes", "Plat cuisiné", "Surgelé", "Autre"], key="cat_val", label_visibility="collapsed")
f_loc = f2.selectbox("Lieu", ["Tous", "Cuisine", "Buanderie"], key="loc_val", label_visibility="collapsed")

# TRI ALERTES
def get_status(date_str):
    try:
        diff = (datetime.now() - datetime.strptime(str(date_str).split(" ")[0], "%Y-%m-%d")).days
        if diff >= 180: return 0, "#ff4b4b"
        if diff >= 90: return 1, "#ffa500"
        return 2, "transparent"
    except: return 2, "transparent"

d_f = df.copy()
if not d_f.empty:
    d_f['priority'] = d_f['Date'].apply(lambda x: get_status(x)[0])
    d_f['color'] = d_f['Date'].apply(lambda x: get_status(x)[1])
    d_f = d_f.sort_values(by=['priority', 'Nom']).reset_index()

if recherche:
    d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if f_cat != "Toutes":
    d_f = d_f[d_f['Catégorie'] == f_cat]
if f_loc != "Tous":
    d_f = d_f[d_f['Lieu'] == f_loc]

st.divider()

# LISTE COMPACTE MOBILE
if d_f.empty:
    st.info("Vide.")
else:
    for _, row in d_f.iterrows():
        idx = row['index']
        
        # --- LIGNE 1 : NOM ET BOUTON P ---
        col1, col2 = st.columns([6, 1])
        col1.markdown(f"<div style='border-left: 5px solid {row['color']}; padding-left: 8px;'><span class='prod-name'>{row['Nom']}</span></div>", unsafe_allow_html=True)
        # Pour forcer l'affichage, on utilise un caractère Unicode "plus lourd"
        if col2.button("P", key=f"d_{idx}"):
            df = df.drop(idx).reset_index(drop=True)
            update_stock(df, f"Suppr {row['Nom']}")

        # --- LIGNE 2 : INFOS ET CONTROLE QUANTITÉ ---
        c_det, c_m, c_v, c_p = st.columns([5, 1, 1, 1])
        
        c_det.markdown(f"<span class='prod-details'>{row['Catégorie']}<br>{row['Lieu']} | {row['Contenant']}</span>", unsafe_allow_html=True)
        
        # Utilisation de symboles gras mathématiques pour forcer le rendu du texte
        if c_m.button("−", key=f"m_{idx}"): # Signe moins Unicode robuste
            if df.at[idx, 'Nombre'] > 1:
                df.at[idx, 'Nombre'] -= 1
                update_stock(df, f"Maj {row['Nom']}")
        
        c_v.markdown(f"<div class='qty-text'>{row['Nombre']}</div>", unsafe_allow_html=True)
        
        if c_p.button("+", key=f"p_{idx}"):
            df.at[idx, 'Nombre'] += 1
            update_stock(df, f"Maj {row['Nom']}")
        
        st.markdown("<hr>", unsafe_allow_html=True)
