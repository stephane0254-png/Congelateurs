import streamlit as st
import pandas as pd
import os
import base64
import requests
from datetime import datetime

# Titre de l'onglet navigateur
st.set_page_config(page_title="Gestion des stocks", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .main-title {
        font-size: 2.2rem !important;
        font-weight: bold;
        padding-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 10px;
        line-height: 1.4 !important;
    }
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
FILE_CATS = "categories.csv"

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

# Chargement Catégories
if os.path.exists(FILE_CATS):
    df_cats = pd.read_csv(FILE_CATS)
else:
    df_cats = pd.DataFrame({"Nom": ["Plat cuisiné", "Surgelé", "Autre"]})

# --- FONCTIONS ---
def update_stock(new_df, msg):
    new_df.to_csv(FILE_CSV, index=False)
    save_to_github(FILE_CSV, msg)
    st.rerun()

def update_generic_file(new_df, file_path, msg):
    new_df.to_csv(file_path, index=False)
    save_to_github(file_path, msg)
    st.rerun()

def reset_filters():
    st.session_state.search_val = ""
    st.session_state.cat_val = "Toutes"
    st.session_state.loc_val = "Tous"
    st.session_state.sort_mode = "alpha" 
    st.session_state.last_added_id = None

# --- INTERFACE ---
st.markdown('<div class="main-title">🗄️ Gestion des stocks</div>', unsafe_allow_html=True)

if 'sort_mode' not in st.session_state: st.session_state.sort_mode = "alpha"
if 'last_added_id' not in st.session_state: st.session_state.last_added_id = None

tab1, tab_recap, tab_lieux, tab_cats, tab_cont = st.tabs(["📦 Stock", "📋 Récapitulatif", "📍 Lieux", "🏷️ Catégories", "⚙️ Contenants"])

with tab1:
    UNITES = ["Portions", "kg", "Pièces"]
    liste_categories = sorted(df_cats["Nom"].tolist())

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", liste_categories)
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
    f_cat = f1.selectbox("Filtrer par catégorie", ["Toutes"] + liste_categories, key="cat_val")
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
                c_top1, c_top2, c_top3 = st.columns([2, 1, 1])
                c_top1.caption(f"📍 {row['Lieu']}")
                
                # --- MODIFICATION PRODUIT ---
                with c_top2.popover("📝 Éditer"):
                    with st.form(f"edit_prod_{orig_idx}"):
                        new_n = st.text_input("Nom", value=row['Nom'])
                        new_c = st.selectbox("Catégorie", liste_categories, index=liste_categories.index(row['Catégorie']) if row['Catégorie'] in liste_categories else 0)
                        new_l = st.selectbox("Lieu", sorted(df_lieux["Nom"].tolist()), index=sorted(df_lieux["Nom"].tolist()).index(row['Lieu']) if row['Lieu'] in df_lieux["Nom"].values else 0)
                        new_cont = st.selectbox("Contenant", sorted(df_cont["Nom"].tolist()), index=sorted(df_cont["Nom"].tolist()).index(row['Contenant']) if row['Contenant'] in df_cont["Nom"].values else 0)
                        new_u = st.selectbox("Unité", UNITES, index=UNITES.index(row['Unité']) if row['Unité'] in UNITES else 0)
                        if st.form_submit_button("Enregistrer"):
                            df.at[orig_idx, 'Nom'] = new_n
                            df.at[orig_idx, 'Catégorie'] = new_c
                            df.at[orig_idx, 'Lieu'] = new_l
                            df.at[orig_idx, 'Contenant'] = new_cont
                            df.at[orig_idx, 'Unité'] = new_u
                            update_stock(df, f"Modif {new_n}")

                if is_new: c_top3.markdown("<p style='text-align:right; color:#2e7d32; font-size:0.8rem; font-weight:bold; margin:0;'>✨ NOUVEAU</p>", unsafe_allow_html=True)
                
                st.subheader(row['Nom'])
                st.caption(f"🏷️ {row['Catégorie']} | 📦 {row['Contenant']}")
                
                col1, col2, col3, col4 = st.columns([1, 1.5, 1, 2])
                if col1.button("➖", key=f"min_{orig_idx}"):
                    if df.at[orig_idx, 'Nombre'] > 1:
                        df.at[orig_idx, 'Nombre'] -= 1
                        update_stock(df, "Moins")
                
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
    st.subheader("📋 Liste par lieu")
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
                    msg = [f"🔴 **{nb_rouge}** de +6 mois" if nb_rouge > 0 else "", f"🟠 **{nb_orange}** de +3 mois" if nb_orange > 0 else ""]
                    st.markdown(f"<div class='stats-box'>⚠️ À consommer : {' / '.join(filter(None, msg))}</div>", unsafe_allow_html=True)

            recap_df = recap_df.sort_values(by='Date_dt', ascending=True, na_position='last')
            if recap_df.empty: st.info(f"Le lieu {lieu_recap} est vide.")
            else:
                for _, row in recap_df.iterrows():
                    icon = "⚪"
                    if pd.notna(row['Date_dt']):
                        diff = (datetime.now() - row['Date_dt']).days
                        icon = "🔴" if diff >= 180 else "🟠" if diff >= 90 else "⚪"
                        date_display = f"({row['Date_dt'].strftime('%d/%m/%Y')})"
                    else: date_display = "(Pas de date)"
                    st.text(f"{icon} {row['Nom']} - {row['Nombre']} {row.get('Unité', '')} {date_display}")
        else: st.info("Le stock est vide.")

# --- ONGLET LIEUX ---
with tab_lieux:
    st.subheader("📍 Gestion des Lieux")
    with st.form("conf_lieux", clear_on_submit=True):
        new_l = st.text_input("Ajouter un lieu")
        if st.form_submit_button("Valider"):
            if new_l and new_l not in df_lieux["Nom"].values:
                df_lieux = pd.concat([df_lieux, pd.DataFrame([{"Nom": new_l}])], ignore_index=True)
                update_generic_file(df_lieux, FILE_LIEUX, "Nouveau lieu")

    for i, r in df_lieux.sort_values("Nom").iterrows():
        c_n, c_e, c_d = st.columns([3, 1, 1])
        c_n.write(f"• {r['Nom']}")
        with c_e.popover("✏️"):
            new_name = st.text_input("Renommer", value=r['Nom'], key=f"edit_loc_input_{i}")
            if st.button("OK", key=f"btn_loc_{i}"):
                old_name = r['Nom']
                df_lieux.at[i, 'Nom'] = new_name
                df_lieux.to_csv(FILE_LIEUX, index=False)
                # Mise à jour du stock impacté
                df.loc[df['Lieu'] == old_name, 'Lieu'] = new_name
                df.to_csv(FILE_CSV, index=False)
                save_to_github(FILE_CSV, f"Update lieu {old_name}->{new_name}")
                update_generic_file(df_lieux, FILE_LIEUX, f"Rename lieu {old_name}")
        if c_d.button("🗑️", key=f"del_loc_{i}"):
            df_lieux = df_lieux.drop(i).reset_index(drop=True)
            update_generic_file(df_lieux, FILE_LIEUX, "Suppr lieu")

# --- ONGLET CATÉGORIES ---
with tab_cats:
    st.subheader("🏷️ Gestion des Catégories")
    with st.form("conf_cats", clear_on_submit=True):
        new_cat = st.text_input("Ajouter une catégorie (ex: Viande, Dessert)")
        if st.form_submit_button("Valider"):
            if new_cat and new_cat not in df_cats["Nom"].values:
                df_cats = pd.concat([df_cats, pd.DataFrame([{"Nom": new_cat}])], ignore_index=True)
                update_generic_file(df_cats, FILE_CATS, "Nouvelle catégorie")

    for i, r in df_cats.sort_values("Nom").iterrows():
        c_n, c_e, c_d = st.columns([3, 1, 1])
        c_n.write(f"• {r['Nom']}")
        with c_e.popover("✏️"):
            new_name = st.text_input("Renommer", value=r['Nom'], key=f"edit_cat_input_{i}")
            if st.button("OK", key=f"btn_cat_{i}"):
                old_name = r['Nom']
                df_cats.at[i, 'Nom'] = new_name
                df_cats.to_csv(FILE_CATS, index=False)
                # Mise à jour du stock impacté
                df.loc[df['Catégorie'] == old_name, 'Catégorie'] = new_name
                df.to_csv(FILE_CSV, index=False)
                save_to_github(FILE_CSV, f"Update cat {old_name}->{new_name}")
                update_generic_file(df_cats, FILE_CATS, f"Rename cat {old_name}")
        if c_d.button("🗑️", key=f"del_cat_{i}"):
            df_cats = df_cats.drop(i).reset_index(drop=True)
            update_generic_file(df_cats, FILE_CATS, "Suppr catégorie")

# --- CONFIGURATION CONTENANTS ---
with tab_cont:
    st.subheader("🛠️ Configuration des Contenants")
    with st.form("conf_cont", clear_on_submit=True):
        new_c = st.text_input("Ajouter un contenant")
        if st.form_submit_button("Valider"):
            if new_c and new_c not in df_cont["Nom"].values:
                df_cont = pd.concat([df_cont, pd.DataFrame([{"Nom": new_c}])], ignore_index=True)
                update_generic_file(df_cont, FILE_CONTENANTS, "Nouveau contenant")

    for i, r in df_cont.sort_values("Nom").iterrows():
        c_n, c_e, c_d = st.columns([3, 1, 1])
        c_n.write(f"• {r['Nom']}")
        with c_e.popover("✏️"):
            new_name = st.text_input("Renommer", value=r['Nom'], key=f"edit_cont_input_{i}")
            if st.button("OK", key=f"btn_cont_{i}"):
                old_name = r['Nom']
                df_cont.at[i, 'Nom'] = new_name
                df_cont.to_csv(FILE_CONTENANTS, index=False)
                # Mise à jour du stock impacté
                df.loc[df['Contenant'] == old_name, 'Contenant'] = new_name
                df.to_csv(FILE_CSV, index=False)
                save_to_github(FILE_CSV, f"Update cont {old_name}->{new_name}")
                update_generic_file(df_cont, FILE_CONTENANTS, f"Rename cont {old_name}")
        if c_d.button("🗑️", key=f"del_cont_{i}"):
            df_cont = df_cont.drop(i).reset_index(drop=True)
            update_generic_file(df_cont, FILE_CONTENANTS, "Suppr contenant")
