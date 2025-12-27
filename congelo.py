import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Mon Congélateur", layout="wide")

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

# --- OPTIONS ---
LISTE_CAT = ["Plat cuisiné", "Surgelé", "Autre"]
LISTE_CONT = ["Couvercle rouge", "Couvercle vert", "Grand bleu", "Petit bleu", "Plastique blanc", "Préemballage", "Pyrex", "Tupperware", "Verre Carré", "Moyen bleu"]
LISTE_LOC = ["Cuisine", "Buanderie"]

# --- CHARGEMENT ---
if os.path.exists(FILE_CSV):
    df = pd.read_csv(FILE_CSV).fillna("")
    mapping = {'nom': 'Nom', 'catégorie': 'Catégorie', 'nombre': 'Nombre', 'lieu': 'Lieu', 'date': 'Date', 'contenant': 'Contenant'}
    df = df.rename(columns=mapping)
else:
    df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])

# --- FONCTIONS D'ACTION ---
def update_stock(new_df, msg):
    new_df.to_csv(FILE_CSV, index=False)
    save_to_github(FILE_CSV, msg)
    st.rerun()

# --- INTERFACE ---
st.title("❄️ Mon Congélateur")

# Section AJOUT (Card-style)
with st.expander("➕ Ajouter un produit", expanded=False):
    with st.form("ajout"):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nom")
        c = col1.selectbox("Catégorie", LISTE_CAT)
        cont = col1.selectbox("Contenant", LISTE_CONT)
        l = col2.selectbox("Lieu", LISTE_LOC)
        q = col2.number_input("Nombre", min_value=1, step=1)
        if st.form_submit_button("Ajouter au stock"):
            new_row = pd.DataFrame([{"Nom": n, "Catégorie": c, "Contenant": cont, "Lieu": l, "Nombre": int(q), "Date": datetime.now().strftime("%Y-%m-%d")}])
            df = pd.concat([df, new_row], ignore_index=True)
            update_stock(df, f"Ajout {n}")

# RECHERCHE ET FILTRES
st.subheader("🔍 Recherche")
f_col1, f_col2 = st.columns(2)
recherche = f_col1.text_input("Filtrer par nom...")
f_loc = f_col2.selectbox("Filtrer par lieu", ["Tous"] + LISTE_LOC)

d_f = df.copy()
if recherche:
    d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if f_loc != "Tous":
    d_f = d_f[d_f['Lieu'] == f_loc]

# AFFICHAGE DE LA LISTE (Style "Ancienne Application")
st.divider()

if d_f.empty:
    st.info("Aucun produit.")
else:
    for i, row in d_f.iterrows():
        # Calcul de la couleur d'alerte
        color = "inherit"
        try:
            diff = (datetime.now() - datetime.strptime(str(row['Date']).split(" ")[0], "%Y-%m-%d")).days
            if diff >= 180: color = "#ff4b4b" # Rouge
            elif diff >= 90: color = "#ffa500" # Orange
        except: pass

        # Création de la ligne avec colonnes
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            
            # Nom et détails (avec indicateur de couleur)
            c1.markdown(f"<div style='border-left: 5px solid {color}; padding-left: 10px;'>"
                        f"<b>{row['Nom']}</b><br>"
                        f"<small>{row['Catégorie']} | {row['Contenant']} | {row['Lieu']}</small></div>", unsafe_allow_html=True)
            
            # Date
            c2.write(f"📅 {row['Date']}")

            # Boutons de quantité (+ / -)
            col_q1, col_q2, col_q3 = c3.columns([1, 1, 1])
            if col_q1.button("➖", key=f"min_{i}"):
                if df.at[i, 'Nombre'] > 1:
                    df.at[i, 'Nombre'] -= 1
                    update_stock(df, f"Update {row['Nom']}")
                else:
                    st.warning("Utilisez la poubelle pour supprimer.")

            col_q2.markdown(f"<h4 style='text-align: center; margin: 0;'>{row['Nombre']}</h4>", unsafe_allow_html=True)

            if col_q3.button("➕", key=f"plus_{i}"):
                df.at[i, 'Nombre'] += 1
                update_stock(df, f"Update {row['Nom']}")

            # Bouton Poubelle
            if c4.button("🗑️", key=f"del_{i}"):
                df = df.drop(i).reset_index(drop=True)
                update_stock(df, f"Suppression {row['Nom']}")
            
            st.divider()
