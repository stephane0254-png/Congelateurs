import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Congélo", layout="wide")

# CSS pour resserrer au maximum et forcer l'alignement
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0.2rem !important; /* Rapproche les boutons */
    }
    [data-testid="column"] {
        width: auto !important;
        flex: 1 1 auto !important;
        padding: 0 !important;
    }
    div.stButton > button {
        padding: 0 !important;
        width: 30px !important;
        height: 30px !important;
        font-size: 12px !important;
    }
    hr { margin: 0.3rem 0 !important; }
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

# --- CALCUL DES ALERTES ET TRI ---
def get_priority(date_str):
    try:
        diff = (datetime.now() - datetime.strptime(str(date_str).split(" ")[0], "%Y-%m-%d")).days
        if diff >= 180: return 0, "#ff4b4b" # Rouge (Priorité 0)
        if diff >= 90: return 1, "#ffa500"  # Orange (Priorité 1)
        return 2, "transparent"            # Frais (Priorité 2)
    except: return 2, "transparent"

d_f = df.copy()
if not d_f.empty:
    d_f['priority'] = d_f['Date'].apply(lambda x: get_priority(x)[0])
    d_f['color'] = d_f['Date'].apply(lambda x: get_priority(x)[1])
    d_f = d_f.sort_values(by=['priority', 'Nom']).reset_index()

if recherche:
    d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
if f_cat != "Toutes":
    d_f = d_f[d_f['Catégorie'] == f_cat]
if f_loc != "Tous":
    d_f = d_f[d_f['Lieu'] == f_loc]

st.divider()

# LISTE RESSERRÉE
if d_f.empty:
    st.info("Vide.")
else:
    for _, row in d_f.iterrows():
        i = row['index'] # Index original pour les actions
        
        # Répartition des colonnes très serrée [Texte large, Boutons étroits]
        cols = st.columns([6, 1.2, 1, 1.2, 1.2])
        
        cols[0].markdown(f"""
            <div style='border-left: 4px solid {row['color']}; padding-left: 5px; line-height: 1.1;'>
                <b style='font-size: 0.8rem; white-space: nowrap;'>{row['Nom']}</b><br>
                <span style='font-size: 0.65rem; color: gray;'>{row['Catégorie']}|{row['Contenant']}|{row['Lieu']}</span>
            </div>
            """, unsafe_allow_html=True)
        
        if cols[1].button("➖", key=f"m_{i}"):
            if df.at[i, 'Nombre'] > 1:
                df.at[i, 'Nombre'] -= 1
                update_stock(df, f"Maj {row['Nom']}")

        cols[2].markdown(f"<p style='text-align: center; font-weight: bold; margin-top: 6px; font-size: 0.85rem;'>{row['Nombre']}</p>", unsafe_allow_html=True)

        if cols[3].button("➕", key=f"p_{i}"):
            df.at[i, 'Nombre'] += 1
            update_stock(df, f"Maj {row['Nom']}")

        if cols[4].button("🗑️", key=f"d_{i}"):
            df = df.drop(i).reset_index(drop=True)
            update_stock(df, f"Suppr {row['Nom']}")
        
        st.markdown("<hr>", unsafe_allow_html=True)
