import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# Mode Wide mais avec CSS pour réduire les marges
st.set_page_config(page_title="Congélo", layout="wide")

# CSS pour compacter l'interface sur mobile
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    h1 { font-size: 1.5rem !important; }
    h4 { font-size: 1.1rem !important; }
    .stButton button { width: 100%; padding: 0.2rem; }
    hr { margin: 0.5rem 0 !important; }
    div[data-testid="stExpander"] { margin-bottom: 0.5rem; }
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

# Ajout compact
with st.expander("➕ Nouveau produit"):
    with st.form("ajout", clear_on_submit=True):
        n = st.text_input("Nom")
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Cat", ["Plat cuisiné", "Surgelé", "Autre"])
        loc = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
        cont = st.selectbox("Contenant", ["Couvercle rouge", "Couvercle vert", "Grand bleu", "Petit bleu", "Plastique blanc", "Préemballage", "Pyrex", "Tupperware", "Verre Carré", "Moyen bleu"])
        q = st.number_input("Nombre", min_value=1, step=1)
        if st.form_submit_button("Ajouter"):
            new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat, "Contenant": cont, "Lieu": loc, "Nombre": int(q), "Date": datetime.now().strftime("%Y-%m-%d")}])
            df = pd.concat([df, new_row], ignore_index=True)
            update_stock(df, f"Ajout {n}")

# Filtres compacts
f1, f2 = st.columns(2)
recherche = f1.text_input("🔍 Rechercher...", label_visibility="collapsed", placeholder="Rechercher...")
f_loc = f2.selectbox("Lieu", ["Tous", "Cuisine", "Buanderie"], label_visibility="collapsed")

d_f = df.copy()
if recherche:
    d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if f_loc != "Tous":
    d_f = d_f[d_f['Lieu'] == f_loc]

st.divider()

# LISTE COMPACTE
if d_f.empty:
    st.info("Vide.")
else:
    for i, row in d_f.iterrows():
        # Calcul couleur
        color = "transparent"
        try:
            diff = (datetime.now() - datetime.strptime(str(row['Date']).split(" ")[0], "%Y-%m-%d")).days
            if diff >= 180: color = "#ff4b4b"
            elif diff >= 90: color = "#ffa500"
        except: pass

        with st.container():
            # Disposition smartphone : Nom (gauche) | Commandes (droite)
            col_info, col_ctrl, col_del = st.columns([5, 4, 1])
            
            # 1. Infos (Nom + détails en petit)
            col_info.markdown(f"""
                <div style='border-left: 4px solid {color}; padding-left: 8px; line-height: 1.2;'>
                    <b style='font-size: 0.95rem;'>{row['Nom']}</b><br>
                    <span style='font-size: 0.75rem; color: gray;'>{row['Catégorie']} | {row['Lieu']}</span>
                </div>
                """, unsafe_allow_html=True)
            
            # 2. Boutons Moins / Nombre / Plus
            q_moins, q_val, q_plus = col_ctrl.columns([1, 1, 1])
            if q_moins.button("➖", key=f"m_{i}"):
                if df.at[i, 'Nombre'] > 1:
                    df.at[i, 'Nombre'] -= 1
                    update_stock(df, f"Maj {row['Nom']}")
            
            q_val.markdown(f"<p style='text-align: center; font-weight: bold; margin-top: 5px;'>{row['Nombre']}</p>", unsafe_allow_html=True)
            
            if q_plus.button("➕", key=f"p_{i}"):
                df.at[i, 'Nombre'] += 1
                update_stock(df, f"Maj {row['Nom']}")

            # 3. Poubelle
            if col_del.button("🗑️", key=f"d_{i}"):
                df = df.drop(i).reset_index(drop=True)
                update_stock(df, f"Suppr {row['Nom']}")
            
            st.divider()
