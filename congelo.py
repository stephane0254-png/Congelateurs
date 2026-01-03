import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# Titre de l'onglet navigateur
st.set_page_config(page_title="Stock congélateurs", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .block-container { padding: 0.5rem !important; }
    div.stButton > button { height: 35px !important; font-weight: bold !important; width: 100%; }
    .qty-text {
        text-align: center; font-weight: bold; font-size: 1.2rem;
        background: #f0f2f6; border-radius: 4px; line-height: 35px; height: 35px;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div:nth-child(1) {
        border-left-width: 10px !important;
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

def reset_filters():
    st.session_state.search_val = ""
    st.session_state.cat_val = "Toutes"
    st.session_state.loc_val = "Tous"
    st.session_state.sort_mode = "alpha"
    st.session_state.last_added_id = None

# --- INTERFACE ---
st.title("❄️ Stock congélateurs")

if 'sort_mode' not in st.session_state: st.session_state.sort_mode = "alpha"
if 'last_added_id' not in st.session_state: st.session_state.last_added_id = None

tab1, tab_recap, tab2 = st.tabs(["📦 Stock", "📋 Récapitulatif", "⚙️ Configuration"])

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

    c_s, c_sort, c_reset = st.columns([4, 1, 1])
    if "search_val" not in st.session_state: st.session_state.search_val = ""
    search = c_s.text_input("🔍 Rechercher", key="search_val", label_visibility="collapsed")
    if c_sort.button("⌛"):
        modes = ["alpha", "newest", "oldest"]
        st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
    c_reset.button("🔄", on_click=reset_filters)

    f1, f2 = st.columns(2)
    f_cat = f1.selectbox("Filtrer par catégorie", ["Toutes", "Plat cuisiné", "Surgelé", "Autre"], key="cat_val")
    f_loc = f2.selectbox("Filtrer par lieu", ["Tous", "Cuisine", "Buanderie"], key="loc_val")

    working_df = df.copy()
    if not working_df.empty:
        # Harmonisation : On s'assure que toutes les dates sont des objets datetime valides
        working_df['Date_dt'] = pd.to_datetime(working_df['Date'], errors='coerce')
        
        if search: working_df = working_df[working_df['Nom'].str.contains(search, case=False)]
        if f_cat != "Toutes": working_df = working_df[working_df['Catégorie'] == f_cat]
        if f_loc != "Tous": working_df = working_df[working_df['Lieu'] == f_loc]
        
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

    if working_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        for _, row in working_df.iterrows():
            idx = row['index']
            is_new = (f"{row['Nom']}_{row['Date']}") == st.session_state.last_added_id
            status_color = "#ddd"
            if pd.notna(row['Date_dt']):
                try:
                    diff = (datetime.now() - row['Date_dt']).days
                    if diff >= 180: status_color = "#ff4b4b"
                    elif diff >= 90: status_color = "#ffa500"
                except: pass
            if is_new: status_color = "#2e7d32"

            with st.container(border=True):
                st.markdown(f'<div style="height: 5px; background-color: {status_color}; border-radius: 5px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                c_top1, c_top2 = st.columns([1, 1])
                c_top1.caption(f"📍 {row['Lieu']}")
                if is_new: c_top2.markdown("<p style='text-align:right; color:#2e7d32; font-size:0.8rem; font-weight:bold; margin:0;'>✨ NOUVEAU</p>", unsafe_allow_html=True)
                st.subheader(row['Nom'])
                st.caption(f"{LOGOS.get(row['Catégorie'], '📦')} {row['Catégorie']} | 📦 {row['Contenant']}")
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

# --- ONGLET RÉCAPITULATIF CORRIGÉ (Lecture des dates robuste) ---
with tab_recap:
    st.subheader("📋 Liste par congélateur")
    lieu_recap = st.radio("Choisir le lieu :", ["Cuisine", "Buanderie"], horizontal=True)
    
    recap_df = df.copy()
    if not recap_df.empty:
        recap_df = recap_df[recap_df['Lieu'] == lieu_recap]
        
        # Tentative de conversion robuste
        # On essaie d'abord avec le format jour en premier (JJ/MM/AAAA)
        recap_df['Date_dt'] = pd.to_datetime(recap_df['Date'], dayfirst=True, errors='coerce')
        
        # Pour les lignes qui n'ont toujours pas de date (NaT), on tente une conversion automatique plus large
        mask_inconnu = recap_df['Date_dt'].isna() & (recap_df['Date'] != "")
        if mask_inconnu.any():
            recap_df.loc[mask_inconnu, 'Date_dt'] = pd.to_datetime(recap_df.loc[mask_inconnu, 'Date'], errors='coerce')

        # Tri chronologique (00:00:00 par défaut si l'heure manque)
        recap_df = recap_df.sort_values(by='Date_dt', ascending=True, na_position='last')
        
        if recap_df.empty:
            st.info(f"Le congélateur {lieu_recap} est vide.")
        else:
            st.write(f"**Produits dans {lieu_recap} (triés par ancienneté) :**")
            for _, row in recap_df.iterrows():
                icon = "⚪"
                if pd.notna(row['Date_dt']):
                    diff = (datetime.now() - row['Date_dt']).days
                    if diff >= 180: icon = "🔴"
                    elif diff >= 90: icon = "🟠"
                    date_display = f"({row['Date_dt'].strftime('%d/%m/%Y')})"
                else:
                    # Si c'est vraiment inconnu, on affiche quand même la valeur brute du CSV pour comprendre l'erreur
                    valeur_brute = row['Date'] if row['Date'] else "Vide"
                    date_display = f"(Format inconnu : {valeur_brute})"
                
                st.text(f"{icon} {row['Nom']} - Qté: {row['Nombre']} {date_display}")
    else:
        st.info("Aucun produit en stock.")

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
