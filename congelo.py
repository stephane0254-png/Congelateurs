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

# --- CHARGEMENT & ADAPTATION ---
# On définit l'ordre des colonnes que NOUS voulons afficher
COL_AFFICHAGE = ["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"]

if os.path.exists(FILE_CSV):
    df = pd.read_csv(FILE_CSV).fillna("")
    
    # Mapping flexible pour s'adapter à votre fichier Drive
    # On renomme si jamais des minuscules s'étaient glissées
    mapping = {
        'nom': 'Nom',
        'catégorie': 'Catégorie',
        'nombre': 'Nombre',
        'lieu': 'Lieu',
        'date': 'Date',
        'contenant': 'Contenant'
    }
    df = df.rename(columns=mapping)
    
    # Sécurité : Si une colonne manque, on la crée pour éviter le crash
    for col in COL_AFFICHAGE:
        if col not in df.columns:
            df[col] = ""
else:
    df = pd.DataFrame(columns=COL_AFFICHAGE)

# --- INTERFACE ---
st.title("❄️ Gestion du Congélateur")

col_add, col_list = st.columns([1, 2])

with col_add:
    st.header("➕ Ajouter")
    with st.form("ajout_plat", clear_on_submit=True):
        n = st.text_input("Nom du produit")
        c = st.selectbox("Catégorie", LISTE_CAT)
        cont = st.selectbox("Contenant", LISTE_CONT)
        l = st.selectbox("Lieu", LISTE_LOC)
        q = st.number_input("Nombre de portions", min_value=1, step=1, value=1)
        
        if st.form_submit_button("Ajouter au stock"):
            if n:
                new_row = pd.DataFrame([{
                    "Nom": n, "Catégorie": c, "Contenant": cont, 
                    "Lieu": l, "Nombre": int(q), "Date": datetime.now().strftime("%Y-%m-%d")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(FILE_CSV, index=False)
                save_to_github(FILE_CSV, f"Ajout {n}")
                st.success(f"{n} ajouté !")
                st.rerun()

with col_list:
    st.header("🔍 Inventaire")
    
    f_col1, f_col2 = st.columns(2)
    recherche = f_col1.text_input("Rechercher un plat...")
    f_loc = f_col2.selectbox("Filtrer par lieu", ["Tous"] + LISTE_LOC)
    
    d_f = df.copy()
    if recherche:
        d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
    if f_loc != "Tous":
        d_f = d_f[d_f['Lieu'] == f_loc]
    
    def check_alerte(date_str):
        if not date_str or date_str == "": return "⚪ Inconnue"
        try:
            # Nettoyage de la date pour ne garder que YYYY-MM-DD
            d_str = str(date_str).split(" ")[0]
            diff = (datetime.now() - datetime.strptime(d_str, "%Y-%m-%d")).days
            if diff >= 180: return "🔴 +6 mois"
            if diff >= 90: return "🟠 +3 mois"
            return "🟢 Frais"
        except: return "⚪ Format date"

    if not d_f.empty:
        d_f['État'] = d_f['Date'].apply(check_alerte)
        
        # Affichage avec vos noms de colonnes exacts
        st.dataframe(
            d_f[["Nom", "Catégorie", "Nombre", "Lieu", "Date", "État", "Contenant"]],
            column_config={
                "Nombre": st.column_config.NumberColumn("Nombre", format="%d"),
                "État": st.column_config.TextColumn("Fraîcheur")
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
        
        st.divider()
        st.subheader("🍴 Sortir un plat")
        options_plats = [f"{i} | {row['Nom']} ({row['Lieu']})" for i, row in d_f.iterrows()]
        sel_plat = st.selectbox("Sélectionner le plat consommé", options=options_plats)
        
        if st.button("Marquer comme consommé"):
            idx_to_del = int(sel_plat.split(" | ")[0])
            nom_plat = df.at[idx_to_del, "Nom"]
            df = df.drop(idx_to_del).reset_index(drop=True)
            df.to_csv(FILE_CSV, index=False)
            save_to_github(FILE_CSV, f"Consommé {nom_plat}")
            st.rerun()
    else:
        st.info("Le congélateur est vide ou aucun résultat ne correspond.")
