import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# Titre de l'onglet navigateur
st.set_page_config(page_title="Stock congélateurs", layout="wide")

# --- CSS STYLE ---
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    .product-card {
        background-color: white;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 5px;
        border: 1px solid #ddd;
        border-left: 8px solid transparent;
    }
    .badge-loc {
        font-size: 0.7rem;
        background-color: #e1f5fe;
        color: #0288d1;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .card-title { font-size: 1.1rem; font-weight: bold; margin-top: 5px; }
    .card-meta { font-size: 0.75rem; color: #666; margin-bottom: 10px; }
    div.stButton > button { height: 35px !important; font-weight: bold !important; }
    .qty-display {
        text-align: center; font-weight: bold; font-size: 1.2rem;
        line-height: 35px; background: #f0f2f6; border-radius: 4px;
    }
    .new-badge {
        float: right;
        font-size: 0.7rem;
        color: #2e7d32;
        font-weight: bold;
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

# --- CHARGEMENT ---
if os.path.exists(FILE_CSV):
    try:
        df = pd.read_csv(FILE_CSV).fillna("")
        mapping = {'nom': 'Nom', 'catégorie': 'Catégorie', 'nombre': 'Nombre', 'lieu': 'Lieu', 'date': 'Date', 'contenant': 'Contenant'}
        df = df.rename(columns=mapping)
    except:
        df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])
else:
    df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])

initial_cont = ["Couvercle rouge", "Couvercle vert", "Grand bleu", "Petit bleu", "Plastique blanc", "Préemballage", "Pyrex", "Tupperware", "Verre Carré", "Moyen bleu"]
if os.path.exists(FILE_CONTENANTS):
    try:
        df_cont = pd.read_csv(FILE_CONTENANTS)
    except:
        df_cont = pd.DataFrame({"Nom": initial_cont})
else:
    df_cont = pd.DataFrame({"Nom": initial_cont})

# --- FONCTIONS ---
def update_stock(new_df, msg):
    new_df.to_csv(FILE_CSV, index=False)
    save_to_github(FILE_CSV, msg)
    st.rerun()

def update_contenants(new_df, msg):
    new_df.to_csv(FILE_CONTENANTS, index=False)
    save_to_github(FILE_CONTENANTS, msg)
    st.rerun()

def reset_all():
    st.session_state.search_val = ""
    st.session_state.cat_val = "Toutes"
    st.session_state.loc_val = "Tous"
    st.session_state.sort_mode = "alpha"
    st.session_state.last_added_id = None

# --- INTERFACE ---
st.title("❄️ Stock congélateurs")

if 'sort_mode' not in st.session_state:
    st.session_state.sort_mode = "alpha"
if 'last_added_id' not in st.session_state:
    st.session_state.last_added_id = None

tab1, tab2 = st.tabs(["📦 Stock", "⚙️ Configuration"])

with tab1:
    LOGOS_CAT = {"Plat cuisiné": "🍲", "Surgelé": "❄️", "Autre": "📦"}

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", ["Plat cuisiné", "Surgelé", "Autre"])
            loc_a = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
            list_options = sorted(df_cont["Nom"].tolist())
            cont_a = st.selectbox("Contenant", list_options)
            q_a = st.number_input("Nombre", min_value=1, step=1)
            
            if st.form_submit_button("Ajouter"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{
                    "Nom": n, "Catégorie": cat_a, "Contenant": cont_a, 
                    "Lieu": loc_a, "Nombre": int(q_a), "Date": timestamp
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                st.session_state.last_added_id = n + timestamp
                update_stock(df, f"Ajout {n}")

    # FILTRES ET TRI
    c_s, c_sort, c_r = st.columns([4, 1, 1])
    recherche = c_s.text_input("🔍", placeholder="Chercher...", key="search_val", label_visibility="collapsed")
    if c_sort.button("⌛"):
        modes = ["alpha", "newest", "oldest"]
        st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
    c_r.button("🔄", on_click=reset_all)

    f1, f2 = st.columns(2)
    f_cat = f1.selectbox("Catégorie", ["Toutes", "Plat cuisiné", "Surgelé", "Autre"], key="cat_val", label_visibility="collapsed")
    f_loc = f2.selectbox("Lieu", ["Tous", "Cuisine", "Buanderie"], key="loc_val", label_visibility="collapsed")

    # LOGIQUE DE TRI
    d_f = df.copy()
    if not d_f.empty:
        d_f['Date_dt'] = pd.to_datetime(d_f['Date'], errors='coerce')
        
        if recherche: d_f = d_f[d_f['Nom'].astype(str).str.contains(recherche, case=False)]
        if f_cat != "Toutes": d_f = d_f[d_f['Catégorie'] == f_cat]
        if f_loc != "Tous": d_f = d_f[d_f['Lieu'] == f_loc]
        
        # Tri de base
        if st.session_state.sort_mode == "alpha": 
            d_f = d_f.sort_values(by='Nom').reset_index()
            s_lbl = "🔤 Nom"
        elif st.session_state.sort_mode == "oldest": 
            d_f = d_f.sort_values(by=['Date_dt', 'Nom'], na_position='last').reset_index()
            s_lbl = "⌛ Plus anciens"
        else: 
            d_f = d_f.sort_values(by=['Date_dt', 'Nom'], ascending=[False, True], na_position='last').reset_index()
            s_lbl = "⌛ Plus récents"

        # Logique épinglage
        if st.session_state.last_added_id:
            mask = (d_f['Nom'] + d_f['Date'].astype(str)) == st.session_state.last_added_id
            if mask.any():
                added_row = d_f[mask]
                other_rows = d_f[~mask]
                d_f = pd.concat([added_row, other_rows])

    st.divider()

    # AFFICHAGE
    if d_f.empty:
        st.info("Aucun produit.")
    else:
        st.caption(f"Tri : {s_lbl}")
        for _, row in d_f.iterrows():
            idx = row['index']
            color = "#ddd"
            if row['Date']:
                try:
                    diff = (datetime.now() - pd.to_datetime(row['Date'])).days
                    if diff >= 180: color = "#ff4b4b"
                    elif diff >= 90: color = "#ffa500"
                except: pass
            
            logo = LOGOS_CAT.get(row['Catégorie'], "📦")
            is_last = (row['Nom'] + str(row['Date'])) == st.session_state.last_added_id
            
            # Correction de l'affichage HTML
            new_label = '<span class="new-badge">✨ NOUVEAU</span>' if is_last else ''
            border_style = "border: 2px solid #2e7d32;" if is_last else ""
            
            st.markdown(f"""
                <div class="product-card" style="border-left-color: {color}; {border_style}">
                    <span class="badge-loc">📍 {row['Lieu']}</span>
                    {new_label}
                    <div class="card-title">{row['Nom']}</div>
                    <div class="card-meta">{logo} {row['Catégorie']} | 📦 {row['Contenant']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            c_m, c_v, c_p, c_e = st.columns([1, 1, 1, 2])
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
                if is_last: st.session_state.last_added_id = None
                update_stock(df, f"Consommé {row['Nom']}")
            st.write("")

with tab2:
    st.subheader("🛠️ Gestion des Contenants")
    with st.form("add_contenant", clear_on_submit=True):
        nouveau_cont = st.text_input("Nom du nouveau contenant")
        if st.form_submit_button("Ajouter le contenant"):
            if nouveau_cont and nouveau_cont not in df_cont["Nom"].values:
                new_c_row = pd.DataFrame([{"Nom": nouveau_cont}])
                df_cont = pd.concat([df_cont, new_c_row], ignore_index=True)
                update_contenants(df_cont, f"Ajout contenant {nouveau_cont}")
            else: st.warning("Nom vide ou déjà existant.")

    st.write("---")
    st.write("**Liste actuelle :**")
    for i, c_row in df_cont.sort_values("Nom").iterrows():
        col_name, col_del = st.columns([3, 1])
        col_name.write(f"- {c_row['Nom']}")
        if col_del.button("🗑️", key=f"del_cont_{i}"):
            df_cont = df_cont.drop(i).reset_index(drop=True)
            update_contenants(df_cont, f"Suppression contenant {c_row['Nom']}")
