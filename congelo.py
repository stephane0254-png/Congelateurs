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
    .stats-box {
        padding: 10px; border-radius: 8px; background-color: #f0f2f6;
        margin-bottom: 20px; border: 1px solid #ddd; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIG GITHUB ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
FILE_CSV = "stock_congelateur.csv"
FILE_CONTENANTS = "contenants.csv"
FILE_LIEUX = "lieux.csv"

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

# --- CHARGEMENT DES DONNÉES ---
def load_data():
    cols = ["Nom", "Catégorie", "Nombre", "Unité", "Lieu", "Date", "Contenant"]
    if os.path.exists(FILE_CSV):
        try:
            temp_df = pd.read_csv(FILE_CSV).fillna("")
            # Mise à jour auto si la colonne Unité manque
            if "Unité" not in temp_df.columns: temp_df["Unité"] = "Portions"
            temp_df.columns = [c.capitalize() if c.lower() != "catégorie" else "Catégorie" for c in temp_df.columns]
            for c in cols:
                if c not in temp_df.columns: temp_df[c] = ""
            return temp_df[cols]
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

df = load_data()

# Chargement Contenants
if os.path.exists(FILE_CONTENANTS):
    df_cont = pd.read_csv(FILE_CONTENANTS)
else:
    df_cont = pd.DataFrame({"Nom": ["Pyrex", "Tupperware", "Verre Carré"]})

# Chargement Lieux
if os.path.exists(FILE_LIEUX):
    df_lieux = pd.read_csv(FILE_LIEUX)
else:
    df_lieux = pd.DataFrame({"Nom": ["Cuisine", "Buanderie"]})

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

tab1, tab_recap, tab_lieux, tab2 = st.tabs(["📦 Stock", "📋 Récapitulatif", "📍 Lieux", "⚙️ Contenants"])

with tab1:
    LOGOS = {"Plat cuisiné": "🍲", "Surgelé": "❄️", "Autre": "📦"}
    UNITES = ["Portions", "Grammes", "Pièces"]

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", ["Plat cuisiné", "Surgelé", "Autre"])
            
            # Utilisation de la liste des lieux dynamique
            liste_lieux_form = sorted(df_lieux["Nom"].tolist())
            loc_a = c2.selectbox("Lieu", liste_lieux_form)
            
            c3, c4, c5 = st.columns([2, 1, 2])
            cont_list = sorted(df_cont["Nom"].tolist())
            cont_a = c3.selectbox("Contenant", cont_list)
            q_a = c4.number_input("Qté", min_value=1, step=1)
            u_a = c5.selectbox("Unité", UNITES)
            
            if st.form_submit_button("Ajouter"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = pd.DataFrame([{"Nom": n, "Catégorie": cat_a, "Contenant": cont_a, "Lieu": loc_a, "Nombre": int(q_a), "Unité": u_a, "Date": ts}])
                df = pd.concat([new_row, df], ignore_index=True)
                st.session_state.last_added_id = f"{n}_{ts}"
                update_stock(df, f"Ajout {n}")

    # Filtres
    c_s, c_sort, c_reset = st.columns([4, 1, 1])
    if "search_val" not in st.session_state: st.session_state.search_val = ""
    search = c_s.text_input("🔍 Rechercher", key="search_val", label_visibility="collapsed")
    
    if c_sort.button("⌛"):
        modes = ["alpha", "newest", "oldest"]
        st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
    c_reset.button("🔄", on_click=reset_filters)

    f1, f2 = st.columns(2)
    f_cat = f1.selectbox("Filtrer par catégorie", ["Toutes", "Plat cuisiné", "Surgelé", "Autre"], key="cat_val")
    # Filtre lieu dynamique
    f_loc = f2.selectbox("Filtrer par lieu", ["Tous"] + sorted(df_lieux["Nom"].tolist()), key="loc_val")

    working_df = df.copy()
    if not working_df.empty:
        working_df['Date_dt'] = pd.to_datetime(working_df['Date'], errors='coerce', dayfirst=True)
        if search: working_df = working_df[working_df['Nom'].str.contains(search, case=False)]
        if f_cat != "Toutes": working_df = working_df[working_df['Catégorie'] == f_cat]
        if f_loc != "Tous": working_df = working_df[working_df['Lieu'] == f_loc]
        
        working_df['is_last'] = (working_df['Nom'] + "_" + working_df['Date']) == st.session_state.last_added_id
        if st.session_state.sort_mode == "alpha":
            working_df = working_df.sort_values(by=['is_last', 'Nom'], ascending=[False, True])
        elif st.session_state.sort_mode == "oldest":
            working_df = working_df.sort_values(by=['is_last', 'Date_dt', 'Nom'], ascending=[False, True, True])
        elif st.session_state.sort_mode == "newest":
            working_df = working_df.sort_values(by=['is_last', 'Date_dt', 'Nom'], ascending=[False, False, True])
        
        working_df = working_df.reset_index()

    if working_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        for _, row in working_df.iterrows():
            orig_idx = row['index']
            is_new = row['is_last']
            status_color = "#ddd"
            if pd.notna(row['Date_dt']):
                diff = (datetime.now() - row['Date_dt']).days
                if diff >= 180: status_color = "#ff4b4b"
                elif diff >= 90: status_color = "#ffa500"
            if is_new: status_color = "#2e7d32"

            with st.container(border=True):
                st.markdown(f'<div style="height: 5px; background-color: {status_color}; border-radius: 5px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                c_top1, c_top2 = st.columns([1, 1])
                c_top1.caption(f"📍 {row['Lieu']}")
                if is_new: c_top2.markdown("<p style='text-align:right; color:#2e7d32; font-size:0.8rem; font-weight:bold; margin:0;'>✨ NOUVEAU</p>", unsafe_allow_html=True)
                
                st.subheader(row['Nom'])
                st.caption(f"{LOGOS.get(row['Catégorie'], '📦')} {row['Catégorie']} | 📦 {row['Contenant']}")
                
                col1, col2, col3, col4 = st.columns([1, 1.5, 1, 2])
                if col1.button("➖", key=f"min_{orig_idx}"):
                    if df.at[orig_idx, 'Nombre'] > 1:
                        df.at[orig_idx, 'Nombre'] -= 1
                        update_stock(df, "Moins")
                
                # Affichage Nombre + Unité
                unite_display = row['Unité'] if 'Unité' in row else ""
                col2.markdown(f"<div class='qty-text'>{row['Nombre']} <small>{unite_display}</small></div>", unsafe_allow_html=True)
                
                if col3.button("➕", key=f"plus_{orig_idx}"):
                    df.at[orig_idx, 'Nombre'] += 1
                    update_stock(df, "Plus")
                
                if col4.button("🍽️ Fini", key=f"fin_{orig_idx}"):
                    df = df.drop(orig_idx).reset_index(drop=True)
                    st.session_state.last_added_id = None
                    update_stock(df, "Fini")

# --- RÉCAPITULATIF ---
with tab_recap:
    st.subheader("📋 Liste par congélateur")
    liste_lieux_recap = sorted(df_lieux["Nom"].tolist())
    if not liste_lieux_recap:
        st.warning("Veuillez créer un lieu dans l'onglet 'Lieux' d'abord.")
    else:
        lieu_recap = st.radio("Choisir le lieu :", liste_lieux_recap, horizontal=True, key="radio_recap")
        
        recap_df = df.copy()
        if not recap_df.empty:
            recap_df = recap_df[recap_df['Lieu'] == lieu_recap]
            recap_df['Date_dt'] = pd.to_datetime(recap_df['Date'], errors='coerce', dayfirst=True)
            
            if not recap_df.empty:
                now = datetime.now()
                nb_rouge = len(recap_df[pd.notna(recap_df['Date_dt']) & ((now - recap_df['Date_dt']).dt.days >= 180)])
                nb_orange = len(recap_df[pd.notna(recap_df['Date_dt']) & ((now - recap_df['Date_dt']).dt.days >= 90) & ((now - recap_df['Date_dt']).dt.days < 180)])
                
                if nb_rouge > 0 or nb_orange > 0:
                    msg = []
                    if nb_rouge > 0: msg.append(f"🔴 **{nb_rouge}** produit(s) de +6 mois")
                    if nb_orange > 0: msg.append(f"🟠 **{nb_orange}** produit(s) de +3 mois")
                    st.markdown(f"<div class='stats-box'>⚠️ À consommer en priorité : {' / '.join(msg)}</div>", unsafe_allow_html=True)

            recap_df = recap_df.sort_values(by='Date_dt', ascending=True, na_position='last')
            if recap_df.empty:
                st.info(f"Le congélateur {lieu_recap} est vide.")
            else:
                for _, row in recap_df.iterrows():
                    icon = "⚪"
                    if pd.notna(row['Date_dt']):
                        diff = (datetime.now() - row['Date_dt']).days
                        if diff >= 180: icon = "🔴"
                        elif diff >= 90: icon = "🟠"
                        date_display = f"({row['Date_dt'].strftime('%d/%m/%Y')})"
                    else:
                        date_display = f"(Date: {row['Date']})" if row['Date'] else "(Pas de date)"
                    
                    unite_txt = row['Unité'] if 'Unité' in row else ""
                    st.text(f"{icon} {row['Nom']} - {row['Nombre']} {unite_txt} {date_display}")
        else:
            st.info("Le stock est vide.")

# --- ONGLET LIEUX (NOUVEAU) ---
with tab_lieux:
    st.subheader("📍 Gestion des Lieux")
    with st.form("conf_lieux", clear_on_submit=True):
        new_l = st.text_input("Ajouter un lieu (ex: Cellier, Garage)")
        if st.form_submit_button("Valider"):
            if new_l and new_l not in df_lieux["Nom"].values:
                df_lieux = pd.concat([df_lieux, pd.DataFrame([{"Nom": new_l}])], ignore_index=True)
                df_lieux.to_csv(FILE_LIEUX, index=False)
                save_to_github(FILE_LIEUX, "Nouveau lieu")
                st.rerun()
    
    for i, r in df_lieux.sort_values("Nom").iterrows():
        c_n, c_d = st.columns([4, 1])
        c_n.write(f"• {r['Nom']}")
        if c_d.button("🗑️", key=f"del_loc_{i}"):
            df_lieux = df_lieux.drop(i).reset_index(drop=True)
            df_lieux.to_csv(FILE_LIEUX, index=False)
            save_to_github(FILE_LIEUX, "Suppr lieu")
            st.rerun()

# --- CONFIGURATION CONTENANTS ---
with tab2:
    st.subheader("🛠️ Configuration des Contenants")
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
        if c_d.button("🗑️", key=f"del_cont_{i}"):
            df_cont = df_cont.drop(i).reset_index(drop=True)
            df_cont.to_csv(FILE_CONTENANTS, index=False)
            save_to_github(FILE_CONTENANTS, "Suppr contenant")
            st.rerun()
