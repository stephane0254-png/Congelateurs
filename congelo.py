import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Congélo", layout="wide")

# CSS pour forcer l'alignement horizontal sur mobile et compacter
st.markdown("""
    <style>
    .block-container { padding: 1rem !important; }
    .product-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 5px 0;
    }
    div.stButton > button {
        padding: 2px 8px !important;
        height: auto !important;
        min-width: 35px !important;
    }
    hr { margin: 0.3rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURATION GITHUB ---
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
col_search, col_reset = st.columns([4, 1])
recherche = col_search.text_input("🔍", placeholder="Rechercher...", label_visibility="collapsed", key="search_input")
if col_reset.button("🔄", help="Réinitialiser"):
    st.rerun()

f1, f2 = st.columns(2)
f_cat = f1.selectbox("Catégorie", ["Toutes", "Plat cuisiné", "Surgelé", "Autre"], label_visibility="collapsed")
f_loc = f2.selectbox("Lieu", ["Tous", "Cuisine", "Buanderie"], label_visibility="collapsed")

d_f = df.copy()
if recherche:
    d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if f_cat != "Toutes":
    d_f = d_f[d_f['Catégorie'] == f_cat]
if f_loc != "Tous":
    d_f = d_f[d_f['Lieu'] == f_loc]

st.divider()

# LISTE OPTIMISÉE MOBILE
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

        col_main, col_btn_m, col_val, col_btn_p, col_btn_d = st.columns([4.5, 1.3, 0.8, 1.3, 1.3])
        
        col_main.markdown(f"""
            <div style='border-left: 4px solid {color}; padding-left: 8px; line-height: 1.1;'>
                <b style='font-size: 0.85rem; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{row['Nom']}</b>
                <span style='font-size: 0.65rem; color: gray;'>{row['Catégorie']} | {row['Contenant']} | {row['Lieu']}</span>
            </div>
            """, unsafe_allow_html=True)
        
        if col_btn_m.button("➖", key=f"m_{i}"):
            if df.at[i, 'Nombre'] > 1:
                df.at[i, 'Nombre'] -= 1
                update_stock(df, f"Maj {row['Nom']}")

        col_val.markdown(f"<p style='text-align: center; font-weight: bold; margin-top: 5px; font-size: 0.9rem;'>{row['Nombre']}</p>", unsafe_allow_html=True)

        if col_btn_p.button("➕", key=f"p_{i}"):
            df.at[i, 'Nombre'] += 1
            update_stock(df, f"Maj {row['Nombre']}")

        if col_btn_d.button("🗑️", key=f"d_{i}"):
            df = df.drop(i).reset_index(drop=True)
            update_stock(df, f"Suppr {row['Nom']}")
        
        st.markdown("<hr>", unsafe_allow_html=True)
