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

# --- CHARGEMENT SÉCURISÉ ---
def load_data():
    cols = ["Nom", "Catégorie", "Nombre", "Lieu", "Date", "Contenant"]
    if os.path.exists(FILE_CSV):
        try:
            temp_df = pd.read_csv(FILE_CSV).fillna("")
            temp_df.columns = [c.capitalize() if c.lower() != "catégorie" else "Catégorie" for c in temp_df.columns]
            for c in cols:
                if c not in temp_df.columns: temp_df[c] = ""
            return temp_df[cols]
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

df = load_data()

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
        working_df['Date_dt'] = pd.to_datetime(working_df['Date'], errors='coerce', dayfirst=True)
        if search: working_df = working_df[working_df['Nom'].str.contains(search, case=False)]
        if f_cat != "Toutes": working_df = working_df[working_df['Catégorie'] == f_cat]
        if f_loc != "Tous": working_df = working_df[working_df['Lieu'] == f_loc]
        
        if st.session_state.sort_mode == "alpha":
            working_df = working_df.sort_values(by='Nom')
        elif st.session_state.sort_mode == "oldest":
            working_df = working_df.sort_values(by=['Date_dt', 'Nom'])
        else:
            working_df = working_df.sort_values(by=['Date_dt', 'Nom'], ascending=[False, True])
        working_df = working_df.reset_index()

    if working_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        for _, row in working_df.iterrows():
            orig_idx = row['index']
            is_new = (f"{row['Nom']}_{row['Date']}") == st.session_state.last_added_id
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
                col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                if col1.button("➖", key=f"min_{orig_idx}"):
                    if df.at[orig_idx, 'Nombre'] > 1:
                        df.at[orig_idx, 'Nombre'] -= 1
                        update_stock(df, "Moins")
                col2.markdown(f"<div class='qty-text'>{row['Nombre']}</div>", unsafe_allow_html=True)
                if col3.button("➕", key=f"plus_{orig_idx}"):
                    df.at[orig_idx, 'Nombre'] += 1
                    update_stock(df, "Plus")
                if col4.button("🍽️ Fini", key=f"fin_{orig_idx}"):
                    df = df.drop(orig_idx).reset_index(drop=True)
                    st.session_state.last_added_id = None
                    update_stock(df, "Fini")

# --- RÉCAPITULATIF AVEC STATS ---
with tab_recap:
    st.subheader("📋 Liste par congélateur")
    lieu_recap = st.radio("Choisir le lieu :", ["Cuisine", "Buanderie"], horizontal=True, key="radio_recap")
    
    recap_df = df.copy()
    if not recap_df.empty:
        recap_df = recap_df[recap_df['Lieu'] == lieu_recap]
        recap_df['Date_dt'] = pd.to_datetime(recap_df['Date'], errors='coerce', dayfirst=True)
        
        # Calcul des statistiques d'ancienneté pour le lieu choisi
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
            st.write(f"**Produits dans {lieu_recap} (par ancienneté) :**")
            for _, row in recap_df.iterrows():
                icon = "⚪"
                if pd.notna(row['Date_dt']):
                    diff = (datetime.now() - row['Date_dt']).days
                    if diff >= 180: icon = "🔴"
                    elif diff >= 90: icon = "🟠"
                    date_display = f"({row['Date_dt'].strftime('%d/%m/%Y')})"
                else:
                    date_display = f"(Date: {row['Date']})" if row['Date'] else "(Pas de date)"
                
                st.text(f"{icon} {row['Nom']} - Qté: {row['Nombre']} {date_display}")
    else:
        st.info("Le stock est vide.")

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
