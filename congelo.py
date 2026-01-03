import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# Titre de l'onglet navigateur
st.set_page_config(page_title="Stock congélateurs", layout="wide")

# --- CSS (Cadre englobant tout le produit) ---
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    .product-box {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #ddd;
        margin-bottom: 15px; /* Espace entre les blocs produits */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    div.stButton > button { height: 35px !important; font-weight: bold !important; width: 100%; }
    .qty-text {
        text-align: center; font-weight: bold; font-size: 1.2rem;
        background: #f0f2f6; border-radius: 4px; line-height: 35px; height: 35px;
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
        df = df.rename(columns={'nom': 'Nom', 'catégorie': 'Catégorie', 'nombre': 'Nombre', 'lieu': 'Lieu', 'date': 'Date', 'contenant': 'Contenant'})
    except:
        df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])
else:
    df = pd.DataFrame(columns=["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"])

if os.path.exists(FILE_CONTENANTS):
    try:
        df_cont = pd.read_csv(FILE_CONTENANTS)
    except:
        df_cont = pd.DataFrame({"Nom": ["Pyrex", "Tupperware", "Verre Carré"]})
else:
    df_cont = pd.DataFrame({"Nom": ["Pyrex", "Tupperware", "Verre Carré"]})

# --- FONCTIONS ---
def update_stock(new_df, msg):
    new_df.to_csv(FILE_CSV, index=False)
    save_to_github(FILE_CSV, msg)
    st.rerun()

# --- INTERFACE ---
st.title("❄️ Stock congélateurs")

if 'sort_mode' not in st.session_state: st.session_state.sort_mode = "alpha"
if 'last_added_id' not in st.session_state: st.session_state.last_added_id = None

tab1, tab2 = st.tabs(["📦 Stock", "⚙️ Configuration"])

with tab1:
    LOGOS = {"Plat cuisiné": "🍲", "Surgelé": "❄️", "Autre": "📦"}

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", ["Plat cuisiné", "Surgelé", "Autre"])
            loc_a = c2.selectbox("Lieu", ["Cuisine", "Buanderie"])
            cont_list = sorted(df_cont["Nom"].tolist())
            cont_a = st.selectbox("Contenant", cont_list)
            q_a = st.number_input("Nombre", min_value=1, step=1)
            
            if st.form_submit_button("Ajouter"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat_a, "Contenant": cont_a, "Lieu": loc_a, "Nombre": int(q_a), "Date": ts}])
                df = pd.concat([df, new_row], ignore_index=True)
                st.session_state.last_added_id = f"{n}_{ts}"
                update_stock(df, f"Ajout {n}")

    # FILTRES
    c_s, c_sort, c_reset = st.columns([4, 1, 1])
    search = c_s.text_input("🔍 Rechercher", key="search_val", label_visibility="collapsed")
    if c_sort.button("⌛"):
        modes = ["alpha", "newest", "oldest"]
        st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
    if c_reset.button("🔄"):
        st.session_state.search_val = ""
        st.session_state.sort_mode = "alpha"
        st.session_state.last_added_id = None
        st.rerun()

    working_df = df.copy()
    if not working_df.empty:
        working_df['Date_dt'] = pd.to_datetime(working_df['Date'], errors='coerce')
        if search: working_df = working_df[working_df['Nom'].str.contains(search, case=False)]
        
        if st.session_state.sort_mode == "alpha":
            working_df = working_df.sort_values(by='Nom').reset_index()
        elif st.session_state.sort_mode == "oldest":
            working_df = working_df.sort_values(by=['Date_dt', 'Nom']).reset_index()
        else:
            working_df = working_df.sort_values(by=['Date_dt', 'Nom'], ascending=[False, True]).reset_index()

        if st.session_state.last_added_id:
            working_df['temp_id'] = working_df['Nom'] + "_" + working_df['Date'].astype(str)
            mask = working_df['temp_id'] == st.session_state.last_added_id
            if mask.any():
                working_df = pd.concat([working_df[mask], working_df[~mask]]).drop(columns=['temp_id'])

    # AFFICHAGE
    if working_df.empty:
        st.info("Aucun produit.")
    else:
        for _, row in working_df.iterrows():
            idx = row['index']
            is_new = (f"{row['Nom']}_{row['Date']}") == st.session_state.last_added_id
            
            # Calcul de la couleur du bandeau selon l'ancienneté
            status_color = "#ddd" # Par défaut gris
            if row['Date']:
                try:
                    diff = (datetime.now() - pd.to_datetime(row['Date'])).days
                    if diff >= 180: status_color = "#ff4b4b" # Rouge (6 mois)
                    elif diff >= 90: status_color = "#ffa500" # Orange (3 mois)
                except: pass
            
            # Si c'est un nouveau produit, on force le vert
            if is_new: status_color = "#2e7d32"

            # DEBUT DU BANDEAU ENGLOBANT
            st.markdown(f'<div class="product-box" style="border-left: 10px solid {status_color};">', unsafe_allow_html=True)
            
            # Infos du haut
            c_top1, c_top2 = st.columns([1, 1])
            c_top1.caption(f"📍 {row['Lieu']}")
            if is_new: c_top2.markdown("<p style='text-align:right; color:#2e7d32; font-size:0.8rem; font-weight:bold; margin:0;'>✨ NOUVEAU</p>", unsafe_allow_html=True)
            
            # Nom et détails
            st.subheader(row['Nom'])
            st.caption(f"{LOGOS.get(row['Catégorie'], '📦')} {row['Catégorie']} | 📦 {row['Contenant']}")
            
            st.write("") # Petit espace avant les boutons
            
            # Boutons (Inclus dans le cadre)
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            if col1.button("➖", key=f"min_{idx}"):
                if df.at[idx, 'Nombre'] > 1:
                    df.at[idx, 'Nombre'] -= 1
                    update_stock(df, "Moins")
            col2.markdown(f"<div class='qty-text'>{row['Nombre']}</div>", unsafe_allow_html=True)
            if col3.button("➕", key=f"plus_{idx}"):
                df.at[idx, 'Nombre'] += 1
                update_stock(df, "Plus")
            if col4.button("🍽️ Fini", key=f"fin_{idx}"):
                df = df.drop(idx).reset_index(drop=True)
                st.session_state.last_added_id = None
                update_stock(df, "Fini")
            
            # FIN DU BANDEAU ENGLOBANT
            st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("🛠️ Configuration")
    with st.form("conf_cont", clear_on_submit=True):
        new_c = st.text_input("Ajouter un contenant")
        if st.form_submit_button("Valider"):
            if new_c and new_c not in df_cont["Nom"].values:
                df_cont = pd.concat([df_cont, pd.DataFrame([{"Nom": new_c}])], ignore_index=True)
                df_cont.to_csv(FILE_CONTENANTS, index=False)
                save_to_github(FILE_CONTENANTS, "Nouveau contenant")
                st.rerun()
    
    for i, r in df_cont.sort_values("Nom").iterrows():
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"• {r['Nom']}")
        if c_d.button("🗑️", key=f"del_{i}"):
            df_cont = df_cont.drop(i).reset_index(drop=True)
            df_cont.to_csv(FILE_CONTENANTS, index=False)
            save_to_github(FILE_CONTENANTS, "Suppr contenant")
            st.rerun()
