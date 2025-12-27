import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Congélo", layout="wide")

# CSS AGRESSIF pour forcer l'alignement horizontal sur Mobile
st.markdown("""
    <style>
    .block-container { padding: 1rem !important; }
    /* Force les colonnes de la liste à rester sur une seule ligne */
    [data-testid="column"] {
        flex-direction: row !important;
        display: flex !important;
        align-items: center !important;
    }
    /* Ajustement spécifique pour les lignes de produits */
    .product-box {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }
    div.stButton > button {
        padding: 2px 5px !important;
        height: 35px !important;
        width: 35px !important;
    }
    hr { margin: 0.5rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- GITHUB CONFIG ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_CSV = "stock_congelateur.csv"

def save_to_github(file_path, commit_message):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
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

# --- FONCTION RESET ---
def reset_filters():
    st.session_state["search_key"] = ""
    st.session_state["cat_key"] = "Toutes"
    st.session_state["loc_key"] = "Tous"

# --- INTERFACE ---
st.title("❄️ Mon Congélateur")

with st.expander("➕ Nouveau produit"):
    with st.form("ajout", clear_on_submit=True):
        n = st.text_input("Nom")
        c1, c2 = st.columns(2)
        cat_add = c1.selectbox("Cat", ["Plat cuisiné", "Surgelé", "Autre"])
        loc_add = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
        cont_add = st.selectbox("Contenant", ["Couvercle rouge", "Couvercle vert", "Grand bleu", "Petit bleu", "Plastique blanc", "Préemballage", "Pyrex", "Tupperware", "Verre Carré", "Moyen bleu"])
        q_add = st.number_input("Nombre", min_value=1, step=1)
        if st.form_submit_button("Ajouter"):
            new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat_add, "Contenant": cont_add, "Lieu": loc_add, "Nombre": int(q_add), "Date": datetime.now().strftime("%Y-%m-%d")}])
            df = pd.concat([df, new_row], ignore_index=True)
            update_stock(df, f"Ajout {n}")

# RECHERCHE ET FILTRES
col_search, col_reset = st.columns([5, 1])
recherche = col_search.text_input("🔍", placeholder="Rechercher...", label_visibility="collapsed", key="search_key")
col_reset.button("🔄", on_click=reset_filters)

f1, f2 = st.columns(2)
f_cat = f1.selectbox("Catégorie", ["Toutes", "Plat cuisiné", "Surgelé", "Autre"], key="cat_key", label_visibility="collapsed")
f_loc = f2.selectbox("Lieu", ["Tous", "Cuisine", "Buanderie"], key="loc_key", label_visibility="collapsed")

d_f = df.copy()
if recherche:
    d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if f_cat != "Toutes":
    d_f = d_f[d_f['Catégorie'] == f_cat]
if f_loc != "Tous":
    d_f = d_f[d_f['Lieu'] == f_loc]

st.divider()

# LISTE FORCEE EN LIGNE
if d_f.empty:
    st.info("Vide.")
else:
    for i, row in d_f.iterrows():
        color = "transparent"
        try:
            diff = (datetime.now() - datetime.strptime(str(row['Date']).split(" ")[0], "%Y-%m-%d")).days
            if diff >= 180: color = "#ff4b4b"
            elif diff >= 90: color = "#ffa500"
        except: pass

        # On utilise une seule ligne avec des colonnes horizontales forcées
        c_info, c_m, c_v, c_p, c_d = st.columns([4, 1, 1, 1, 1])
        
        c_info.markdown(f"""
            <div style='border-left: 4px solid {color}; padding-left: 5px; line-height: 1.1;'>
                <b style='font-size: 0.8rem;'>{row['Nom']}</b><br>
                <span style='font-size: 0.6rem; color: gray;'>{row['Catégorie']} | {row['Contenant']}</span>
            </div>
            """, unsafe_allow_html=True)
        
        if c_m.button("➖", key=f"m_{i}"):
            if df.at[i, 'Nombre'] > 1:
                df.at[i, 'Nombre'] -= 1
                update_stock(df, f"Maj {row['Nom']}")

        c_v.markdown(f"<p style='text-align: center; font-weight: bold; margin-top: 8px; font-size: 0.9rem;'>{row['Nombre']}</p>", unsafe_allow_html=True)

        if c_p.button("➕", key=f"p_{i}"):
            df.at[i, 'Nombre'] += 1
            update_stock(df, f"Maj {row['Nom']}")

        if c_d.button("🗑️", key=f"d_{i}"):
            df = df.drop(i).reset_index(drop=True)
            update_stock(df, f"Suppr {row['Nom']}")
        
        st.markdown("<hr>", unsafe_allow_html=True)
