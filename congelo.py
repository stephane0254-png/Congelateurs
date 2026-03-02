import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Titre de l'onglet navigateur
st.set_page_config(page_title="Stock congélateurs", layout="wide")

# --- CONNEXION SUPABASE ---
# Ces clés doivent être dans vos Streamlit Secrets
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CSS (Design original conservé) ---
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

# --- FONCTIONS DE CHARGEMENT ---
def load_stock():
    # On récupère tout le stock (nom des colonnes en minuscules comme dans Supabase)
    res = supabase.table("stock").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if df_raw.empty:
        return pd.DataFrame(columns=["id", "nom", "categorie", "nombre", "unite", "lieu", "date", "contenant"])
    return df_raw

def load_simple_table(table_name):
    res = supabase.table(table_name).select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if df_raw.empty:
        return pd.DataFrame({"nom": []})
    return df_raw

# Chargement des données au démarrage
df = load_stock()
df_cont = load_simple_table("contenants")
df_lieux = load_simple_table("lieux")
df_cats = load_simple_table("categories")

def reset_filters():
    st.session_state.search_val = ""
    st.session_state.cat_val = "Toutes"
    st.session_state.loc_val = "Tous"
    st.session_state.sort_mode = "alpha" 
    st.session_state.last_added_id = None

# --- INTERFACE ---
st.markdown('<div class="main-title">🗄️ Stock congélateurs</div>', unsafe_allow_html=True)

if 'sort_mode' not in st.session_state: st.session_state.sort_mode = "alpha"
if 'last_added_id' not in st.session_state: st.session_state.last_added_id = None

tab1, tab_recap, tab_lieux, tab_cats, tab_cont = st.tabs(["📦 Stock", "📋 Récapitulatif", "📍 Lieux", "🏷️ Catégories", "⚙️ Contenants"])

with tab1:
    UNITES = ["Portions", "kg", "Pièces"]
    liste_categories = sorted(df_cats["nom"].tolist()) if not df_cats.empty else []

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", liste_categories)
            liste_lieux_form = sorted(df_lieux["nom"].tolist()) if not df_lieux.empty else []
            loc_a = c2.selectbox("Lieu", liste_lieux_form)
            
            c3, c4, c5 = st.columns([2, 1, 2])
            cont_list = sorted(df_cont["nom"].tolist()) if not df_cont.empty else []
            cont_a = c3.selectbox("Contenant", cont_list)
            q_a = c4.number_input("Qté", min_value=1, step=1)
            u_a = c5.selectbox("Unité", UNITES)
            
            if st.form_submit_button("Ajouter"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = {
                    "nom": n, "categorie": cat_a, "contenant": cont_a, 
                    "lieu": loc_a, "nombre": int(q_a), "unite": u_a, "date": ts
                }
                res = supabase.table("stock").insert(new_row).execute()
                if res.data:
                    st.session_state.last_added_id = res.data[0]['id']
                st.rerun()

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
    f_loc = f2.selectbox("Filtrer par lieu", ["Tous"] + sorted(df_lieux["nom"].tolist()), key="loc_val")

    working_df = df.copy()
    if not working_df.empty:
        working_df['date_dt'] = pd.to_datetime(working_df['date'], errors='coerce')
        if search: working_df = working_df[working_df['nom'].str.contains(search, case=False)]
        if f_cat != "Toutes": working_df = working_df[working_df['categorie'] == f_cat]
        if f_loc != "Tous": working_df = working_df[working_df['lieu'] == f_loc]
        
        # Gestion du tri
        working_df['is_last'] = working_df['id'] == st.session_state.last_added_id
        if st.session_state.sort_mode == "alpha":
            working_df = working_df.sort_values(by=['is_last', 'nom'], ascending=[False, True])
        elif st.session_state.sort_mode == "oldest":
            working_df = working_df.sort_values(by=['is_last', 'date_dt', 'nom'], ascending=[False, True, True])
        elif st.session_state.sort_mode == "newest":
            working_df = working_df.sort_values(by=['is_last', 'date_dt', 'nom'], ascending=[False, False, True])

    if working_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        for _, row in working_df.iterrows():
            is_new = row['is_last']
            status_color = "#ddd"
            if pd.notna(row['date_dt']):
                diff = (datetime.now() - row['date_dt']).days
                if diff >= 180: status_color = "#ff4b4b"
                elif diff >= 90: status_color = "#ffa500"
            if is_new: status_color = "#2e7d32"

            with st.container(border=True):
                st.markdown(f'<div style="height: 5px; background-color: {status_color}; border-radius: 5px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                c_top1, c_top2, c_top3 = st.columns([2, 1, 1])
                c_top1.caption(f"📍 {row['lieu']}")
                
                with c_top2.popover("📝 Éditer"):
                    with st.form(f"edit_prod_{row['id']}"):
                        new_n = st.text_input("Nom", value=row['nom'])
                        new_c = st.selectbox("Catégorie", liste_categories, index=liste_categories.index(row['categorie']) if row['categorie'] in liste_categories else 0)
                        new_l = st.selectbox("Lieu", sorted(df_lieux["nom"].tolist()), index=sorted(df_lieux["nom"].tolist()).index(row['lieu']) if row['lieu'] in df_lieux["nom"].values else 0)
                        new_cont = st.selectbox("Contenant", sorted(df_cont["nom"].tolist()), index=sorted(df_cont["nom"].tolist()).index(row['contenant']) if row['contenant'] in df_cont["nom"].values else 0)
                        new_u = st.selectbox("Unité", UNITES, index=UNITES.index(row['unite']) if row['unite'] in UNITES else 0)
                        if st.form_submit_button("Enregistrer"):
                            supabase.table("stock").update({
                                "nom": new_n, "categorie": new_c, "lieu": new_l, "contenant": new_cont, "unite": new_u
                            }).eq("id", row['id']).execute()
                            st.rerun()

                if is_new: c_top3.markdown("<p style='text-align:right; color:#2e7d32; font-size:0.8rem; font-weight:bold; margin:0;'>✨ NOUVEAU</p>", unsafe_allow_html=True)
                
                st.subheader(row['nom'])
                st.caption(f"🏷️ {row['categorie']} | 📦 {row['contenant']}")
                
                col1, col2, col3, col4 = st.columns([1, 1.5, 1, 2])
                if col1.button("➖", key=f"min_{row['id']}"):
                    if int(row['nombre']) > 1:
                        supabase.table("stock").update({"nombre": int(row['nombre']) - 1}).eq("id", row['id']).execute()
                        st.rerun()
                
                col2.markdown(f"<div class='qty-text'>{row['nombre']} <small>{row['unite']}</small></div>", unsafe_allow_html=True)
                
                if col3.button("➕", key=f"plus_{row['id']}"):
                    supabase.table("stock").update({"nombre": int(row['nombre']) + 1}).eq("id", row['id']).execute()
                    st.rerun()
                
                if col4.button("🍽️ Fini", key=f"fin_{row['id']}"):
                    supabase.table("stock").delete().eq("id", row['id']).execute()
                    st.session_state.last_added_id = None
                    st.rerun()

# --- RÉCAPITULATIF ---
with tab_recap:
    st.subheader("📋 Liste par lieu")
    liste_lieux_recap = sorted(df_lieux["nom"].tolist()) if not df_lieux.empty else []
    if not liste_lieux_recap:
        st.warning("Créez un lieu dans l'onglet 'Lieux'.")
    else:
        lieu_recap = st.radio("Lieu :", liste_lieux_recap, horizontal=True, key="radio_recap")
        recap_df = df.copy()
        if not recap_df.empty:
            recap_df = recap_df[recap_df['lieu'] == lieu_recap]
            recap_df['date_dt'] = pd.to_datetime(recap_df['date'], errors='coerce')
            
            if not recap_df.empty:
                now = datetime.now()
                nb_rouge = len(recap_df[pd.notna(recap_df['date_dt']) & ((now - recap_df['date_dt']).dt.days >= 180)])
                nb_orange = len(recap_df[pd.notna(recap_df['date_dt']) & ((now - recap_df['date_dt']).dt.days >= 90) & ((now - recap_df['date_dt']).dt.days < 180)])
                if nb_rouge > 0 or nb_orange > 0:
                    msg = [f"🔴 **{nb_rouge}** de +6 mois" if nb_rouge > 0 else "", f"🟠 **{nb_orange}** de +3 mois" if nb_orange > 0 else ""]
                    st.markdown(f"<div class='stats-box'>⚠️ À consommer : {' / '.join(filter(None, msg))}</div>", unsafe_allow_html=True)

            recap_df = recap_df.sort_values(by='date_dt', ascending=True, na_position='last')
            if recap_df.empty: st.info(f"Le lieu {lieu_recap} est vide.")
            else:
                for _, row in recap_df.iterrows():
                    icon = "⚪"
                    if pd.notna(row['date_dt']):
                        diff = (datetime.now() - row['date_dt']).days
                        icon = "🔴" if diff >= 180 else "🟠" if diff >= 90 else "⚪"
                        date_display = f"({row['date_dt'].strftime('%d/%m/%Y')})"
                    else: date_display = "(Pas de date)"
                    st.text(f"{icon} {row['nom']} - {row['nombre']} {row['unite']} {date_display}")
        else: st.info("Le stock est vide.")

# --- ONGLET LIEUX ---
with tab_lieux:
    st.subheader("📍 Gestion des Lieux")
    with st.form("conf_lieux", clear_on_submit=True):
        new_l = st.text_input("Ajouter un lieu")
        if st.form_submit_button("Valider"):
            if new_l:
                supabase.table("lieux").insert({"nom": new_l}).execute()
                st.rerun()

    for i, r in df_lieux.sort_values("nom").iterrows():
        c_n, c_e, c_d = st.columns([3, 1, 1])
        c_n.write(f"• {r['nom']}")
        with c_e.popover("✏️"):
            new_name = st.text_input("Renommer", value=r['nom'], key=f"edit_loc_input_{i}")
            if st.button("OK", key=f"btn_loc_{i}"):
                supabase.table("lieux").update({"nom": new_name}).eq("nom", r['nom']).execute()
                supabase.table("stock").update({"lieu": new_name}).eq("lieu", r['nom']).execute()
                st.rerun()
        if c_d.button("🗑️", key=f"del_loc_{i}"):
            supabase.table("lieux").delete().eq("nom", r['nom']).execute()
            st.rerun()

# --- ONGLET CATÉGORIES ---
with tab_cats:
    st.subheader("🏷️ Gestion des Catégories")
    with st.form("conf_cats", clear_on_submit=True):
        new_cat = st.text_input("Ajouter une catégorie")
        if st.form_submit_button("Valider"):
            if new_cat:
                supabase.table("categories").insert({"nom": new_cat}).execute()
                st.rerun()

    for i, r in df_cats.sort_values("nom").iterrows():
        c_n, c_e, c_d = st.columns([3, 1, 1])
        c_n.write(f"• {r['nom']}")
        with c_e.popover("✏️"):
            new_name = st.text_input("Renommer", value=r['nom'], key=f"edit_cat_input_{i}")
            if st.button("OK", key=f"btn_cat_{i}"):
                supabase.table("categories").update({"nom": new_name}).eq("nom", r['nom']).execute()
                supabase.table("stock").update({"categorie": new_name}).eq("categorie", r['nom']).execute()
                st.rerun()
        if c_d.button("🗑️", key=f"del_cat_{i}"):
            supabase.table("categories").delete().eq("nom", r['nom']).execute()
            st.rerun()

# --- CONFIGURATION CONTENANTS ---
with tab_cont:
    st.subheader("🛠️ Configuration des Contenants")
    with st.form("conf_cont", clear_on_submit=True):
        new_c = st.text_input("Ajouter un contenant")
        if st.form_submit_button("Valider"):
            if new_c:
                supabase.table("contenants").insert({"nom": new_c}).execute()
                st.rerun()

    for i, r in df_cont.sort_values("nom").iterrows():
        c_n, c_e, c_d = st.columns([3, 1, 1])
        c_n.write(f"• {r['nom']}")
        with c_e.popover("✏️"):
            new_name = st.text_input("Renommer", value=r['nom'], key=f"edit_cont_input_{i}")
            if st.button("OK", key=f"btn_cont_{i}"):
                supabase.table("contenants").update({"nom": new_name}).eq("nom", r['nom']).execute()
                supabase.table("stock").update({"contenant": new_name}).eq("contenant", r['nom']).execute()
                st.rerun()
        if c_d.button("🗑️", key=f"del_cont_{i}"):
            supabase.table("contenants").delete().eq("nom", r['nom']).execute()
            st.rerun()
