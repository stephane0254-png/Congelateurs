import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from supabase import create_client, Client

# Titre de l'onglet navigateur
st.set_page_config(page_title="Stock congélateurs", layout="wide")

# --- CONNEXION SUPABASE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CSS ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    .main-title { font-size: 2.2rem !important; font-weight: bold; padding-bottom: 1rem; display: flex; align-items: center; gap: 10px; line-height: 1.4 !important; }
    div.stButton > button { height: 35px !important; font-weight: bold !important; width: 100%; }
    .qty-text { text-align: center; font-weight: bold; font-size: 1.2rem; background: #f0f2f6; border-radius: 4px; line-height: 35px; height: 35px; }
    [data-testid="stVerticalBlockBorderWrapper"] > div:nth-child(1) { border-left-width: 10px !important; }
    .stats-box { padding: 10px; border-radius: 8px; background-color: #f0f2f6; margin-bottom: 20px; border: 1px solid #ddd; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS DE CHARGEMENT ---
def load_stock():
    res = supabase.table("stock").select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if df_raw.empty:
        return pd.DataFrame(columns=["id", "nom", "categorie", "nombre", "unite", "lieu", "date", "contenant"])
    
    df_raw['nombre'] = pd.to_numeric(df_raw['nombre'], errors='coerce').fillna(0).astype(int)
    # CORRECTION : On convertit en date et on enlève le fuseau horaire (tz=None) pour la comparaison
    df_raw['date_dt'] = pd.to_datetime(df_raw['date'], errors='coerce').dt.tz_localize(None)
    return df_raw

def load_simple_table(table_name):
    res = supabase.table(table_name).select("*").execute()
    df_raw = pd.DataFrame(res.data)
    if df_raw.empty:
        return pd.DataFrame({"nom": []})
    return df_raw

# Chargement initial
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
    liste_lieux_form = sorted(df_lieux["nom"].tolist()) if not df_lieux.empty else []
    cont_list = sorted(df_cont["nom"].tolist()) if not df_cont.empty else []

    with st.expander("➕ Nouveau produit"):
        with st.form("ajout", clear_on_submit=True):
            n = st.text_input("Nom")
            c1, c2 = st.columns(2)
            cat_a = c1.selectbox("Catégorie", liste_categories if liste_categories else ["Divers"])
            loc_a = c2.selectbox("Lieu", liste_lieux_form if liste_lieux_form else ["Principal"])
            c3, c4, c5 = st.columns([2, 1, 2])
            cont_a = c3.selectbox("Contenant", cont_list if cont_list else ["Sachet"])
            q_a = c4.number_input("Qté", min_value=1, step=1)
            u_a = c5.selectbox("Unité", UNITES)
            if st.form_submit_button("Ajouter"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = {"nom": n, "categorie": cat_a, "contenant": cont_a, "lieu": loc_a, "nombre": int(q_a), "unite": u_a, "date": ts}
                res = supabase.table("stock").insert(new_row).execute()
                if res.data: st.session_state.last_added_id = res.data[0]['id']
                st.rerun()

    c_s, c_sort, c_reset = st.columns([4, 1, 1])
    search = c_s.text_input("🔍 Rechercher", key="search_val", label_visibility="collapsed")
    if c_sort.button("⌛"):
        modes = ["alpha", "newest", "oldest"]
        st.session_state.sort_mode = modes[(modes.index(st.session_state.sort_mode) + 1) % 3]
    c_reset.button("🔄", on_click=reset_filters)

    f1, f2 = st.columns(2)
    f_cat = f1.selectbox("Filtrer par catégorie", ["Toutes"] + liste_categories, key="cat_val")
    f_loc = f2.selectbox("Filtrer par lieu", ["Tous"] + liste_lieux_form, key="loc_val")

    working_df = df.copy()
    if not working_df.empty:
        if search: working_df = working_df[working_df['nom'].str.contains(search, case=False, na=False)]
        if f_cat != "Toutes": working_df = working_df[working_df['categorie'] == f_cat]
        if f_loc != "Tous": working_df = working_df[working_df['lieu'] == f_loc]
        working_df['is_last'] = working_df['id'] == st.session_state.last_added_id
        if st.session_state.sort_mode == "alpha": working_df = working_df.sort_values(by=['is_last', 'nom'], ascending=[False, True])
        elif st.session_state.sort_mode == "oldest": working_df = working_df.sort_values(by=['is_last', 'date_dt', 'nom'], ascending=[False, True, True])
        elif st.session_state.sort_mode == "newest": working_df = working_df.sort_values(by=['is_last', 'date_dt', 'nom'], ascending=[False, False, True])

    if working_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        now_naive = datetime.now()
        for _, row in working_df.iterrows():
            status_color = "#ddd"
            if pd.notna(row['date_dt']):
                diff = (now_naive - row['date_dt']).days
                if diff >= 180: status_color = "#ff4b4b"
                elif diff >= 90: status_color = "#ffa500"
            if row['is_last']: status_color = "#2e7d32"

            with st.container(border=True):
                st.markdown(f'<div style="height: 5px; background-color: {status_color}; border-radius: 5px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.caption(f"📍 {row['lieu']}")
                with c2.popover("📝 Éditer"):
                    with st.form(f"ed_{row['id']}"):
                        n_n = st.text_input("Nom", value=row['nom'])
                        n_c = st.selectbox("Catégorie", liste_categories, index=liste_categories.index(row['categorie']) if row['categorie'] in liste_categories else 0)
                        n_l = st.selectbox("Lieu", liste_lieux_form, index=liste_lieux_form.index(row['lieu']) if row['lieu'] in liste_lieux_form else 0)
                        if st.form_submit_button("OK"):
                            supabase.table("stock").update({"nom": n_n, "categorie": n_c, "lieu": n_l}).eq("id", row['id']).execute()
                            st.rerun()
                st.subheader(row['nom'])
                st.caption(f"🏷️ {row['categorie']} | 📦 {row['contenant']}")
                col1, col2, col3, col4 = st.columns([1, 1.5, 1, 2])
                if col1.button("➖", key=f"m_{row['id']}") and row['nombre'] > 1:
                    supabase.table("stock").update({"nombre": int(row['nombre']) - 1}).eq("id", row['id']).execute()
                    st.rerun()
                col2.markdown(f"<div class='qty-text'>{row['nombre']} <small>{row['unite']}</small></div>", unsafe_allow_html=True)
                if col3.button("➕", key=f"p_{row['id']}"):
                    supabase.table("stock").update({"nombre": int(row['nombre']) + 1}).eq("id", row['id']).execute()
                    st.rerun()
                if col4.button("🍽️ Fini", key=f"f_{row['id']}"):
                    supabase.table("stock").delete().eq("id", row['id']).execute()
                    st.rerun()

# --- RÉCAPITULATIF (CORRIGÉ) ---
with tab_recap:
    st.subheader("📋 Liste par lieu")
    if not liste_lieux_form:
        st.warning("Configurez vos lieux.")
    else:
        lieu_recap = st.radio("Lieu :", liste_lieux_form, horizontal=True)
        recap_df = df[df['lieu'] == lieu_recap].copy() if not df.empty else pd.DataFrame()
        if not recap_df.empty:
            now_naive = datetime.now()
            # Calcul sécurisé sans timezone
            recap_df['diff_days'] = (now_naive - recap_df['date_dt']).dt.days
            nb_rouge = len(recap_df[recap_df['diff_days'] >= 180])
            nb_orange = len(recap_df[(recap_df['diff_days'] >= 90) & (recap_df['diff_days'] < 180)])
            
            if nb_rouge > 0 or nb_orange > 0:
                msg = [f"🔴 **{nb_rouge}** de +6 mois" if nb_rouge > 0 else "", f"🟠 **{nb_orange}** de +3 mois" if nb_orange > 0 else ""]
                st.markdown(f"<div class='stats-box'>⚠️ À consommer : {' / '.join(filter(None, msg))}</div>", unsafe_allow_html=True)

            for _, row in recap_df.sort_values('date_dt').iterrows():
                icon = "🔴" if row['diff_days'] >= 180 else "🟠" if row['diff_days'] >= 90 else "⚪"
                date_str = row['date_dt'].strftime('%d/%m/%Y') if pd.notna(row['date_dt']) else "Pas de date"
                st.text(f"{icon} {row['nom']} - {row['nombre']} {row['unite']} ({date_str})")
        else: st.info("Vide.")

# --- ONGLET LIEUX / CATS / CONT ---
def render_config_tab(df_config, table_name, label):
    st.subheader(f"Gestion des {label}")
    with st.form(f"add_{table_name}", clear_on_submit=True):
        new_val = st.text_input(f"Ajouter {label}")
        if st.form_submit_button("Valider") and new_val:
            supabase.table(table_name).insert({"nom": new_val}).execute()
            st.rerun()
    for i, r in df_config.sort_values("nom").iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"• {r['nom']}")
        with c2.popover("✏️"):
            new_n = st.text_input("Nom", value=r['nom'], key=f"ed_{table_name}_{i}")
            if st.button("OK", key=f"btn_{table_name}_{i}"):
                supabase.table(table_name).update({"nom": new_n}).eq("nom", r['nom']).execute()
                # On met à jour le stock aussi si le nom change
                col_name = "categorie" if table_name == "categories" else "contenant" if table_name == "contenants" else "lieu"
                supabase.table("stock").update({col_name: new_n}).eq(col_name, r['nom']).execute()
                st.rerun()
        if c3.button("🗑️", key=f"del_{table_name}_{i}"):
            supabase.table(table_name).delete().eq("nom", r['nom']).execute()
            st.rerun()

with tab_lieux: render_config_tab(df_lieux, "lieux", "Lieux")
with tab_cats: render_config_tab(df_cats, "categories", "Catégories")
with tab_cont: render_config_tab(df_cont, "contenants", "Contenants")
