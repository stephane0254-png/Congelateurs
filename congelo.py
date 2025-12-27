import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Mon Congélateur Pro", layout="wide")

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
else:
    df = pd.DataFrame(columns=["Produit", "Catégorie", "Contenant", "Lieu", "Portions", "Date"])

# --- INTERFACE ---
st.title("❄️ Gestion du Congélateur")

col_add, col_list = st.columns([1, 2])

with col_add:
    st.header("➕ Ajouter")
    with st.form("ajout_plat", clear_on_submit=True):
        p = st.text_input("Nom du produit")
        c = st.selectbox("Catégorie", LISTE_CAT)
        cont = st.selectbox("Contenant", LISTE_CONT)
        l = st.selectbox("Lieu", LISTE_LOC)
        q = st.number_input("Nombre de portions", min_value=1, step=1, value=1)
        
        if st.form_submit_button("Ajouter au stock"):
            if p:
                new_row = pd.DataFrame([{
                    "Produit": p, "Catégorie": c, "Contenant": cont, 
                    "Lieu": l, "Portions": int(q), "Date": datetime.now().strftime("%Y-%m-%d")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(FILE_CSV, index=False)
                save_to_github(FILE_CSV, f"Ajout {p}")
                st.success(f"{p} ajouté !")
                st.rerun()

with col_list:
    st.header("🔍 Inventaire")
    
    # Filtres rapides
    f_col1, f_col2 = st.columns(2)
    recherche = f_col1.text_input("Rechercher un plat...")
    f_loc = f_col2.selectbox("Filtrer par lieu", ["Tous"] + LISTE_LOC)
    
    d_f = df.copy()
    if recherche:
        d_f = d_f[d_f['Produit'].str.contains(recherche, case=False)]
    if f_loc != "Tous":
        d_f = d_f[d_f['Lieu'] == f_loc]
    
    # Calcul des alertes (6 mois = 180 jours)
    def check_alerte(date_str):
        try:
            diff = (datetime.now() - datetime.strptime(date_str, "%Y-%m-%d")).days
            if diff >= 180: return "🔴 +6 mois"
            if diff >= 90: return "🟠 +3 mois"
            return "🟢 Frais"
        except: return ""

    if not d_f.empty:
        d_f['Alerte'] = d_f['Date'].apply(check_alerte)
        
        st.dataframe(
            d_f[["Produit", "Catégorie", "Contenant", "Lieu", "Portions", "Date", "Alerte"]],
            column_config={
                "Portions": st.column_config.NumberColumn("Portions", format="%d"),
                "Alerte": st.column_config.TextColumn("État")
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
        
        st.divider()
        st.subheader("🍴 Sortir un plat")
        sel_plat = st.selectbox("Sélectionner le plat consommé", 
                               options=[f"{i} | {row['Produit']} ({row['Lieu']})" for i, row in d_f.iterrows()])
        
        if st.button("Marquer comme consommé"):
            idx_to_del = int(sel_plat.split(" | ")[0])
            nom_plat = df.at[idx_to_del, "Produit"]
            df = df.drop(idx_to_del).reset_index(drop=True)
            df.to_csv(FILE_CSV, index=False)
            save_to_github(FILE_CSV, f"Consommé {nom_plat}")
            st.rerun()
    else:
        st.info("Le congélateur est vide ou aucun résultat ne correspond.")
