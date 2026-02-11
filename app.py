import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Mon RPG Vie", page_icon="🎮", layout="centered")

# --- CONNEXION DIRECTE (MÉTHODE ROBUSTE) ---
# On contourne le wrapper Streamlit pour parler directement à Google
def get_worksheet():
    # 1. On récupère tes secrets
    secrets = st.secrets["connections"]["gsheets"]
    
    # 2. On s'identifie
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    
    # 3. On ouvre la feuille
    sheet_url = secrets["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    return sh.worksheet("Data")

# Fonction pour sauvegarder (Ajoute juste une ligne, ne casse pas tout)
def save_action(xp_amount, type_stat, comment=""):
    try:
        ws = get_worksheet()
        # On ajoute la ligne à la fin
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            type_stat, 
            xp_amount, 
            comment
        ])
        st.toast(f"Sauvegardé ! (+{xp_amount} XP)", icon="💾")
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

# Fonction pour charger les données
def load_data():
    try:
        ws = get_worksheet()
        # On lit tout le contenu
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # Si le tableau est vide mais existe, on renvoie un vide propre
        if df.empty:
            return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])
        return df
    except Exception:
        # Si erreur (ex: première fois), on renvoie vide
        return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])

# --- CALCUL DU NIVEAU ---
df = load_data()
if not df.empty and "XP" in df.columns:
    # On s'assure que XP est bien un nombre
    df["XP"] = pd.to_numeric(df["XP"], errors='coerce').fillna(0)
    
    total_xp = df["XP"].sum()
    xp_intellect = df[df["Type"] == "Intellect"]["XP"].sum()
    xp_force = df[df["Type"] == "Force"]["XP"].sum()
    xp_gestion = df[df["Type"] == "Gestion"]["XP"].sum()
else:
    total_xp, xp_intellect, xp_force, xp_gestion = 0, 0, 0, 0

niveau = 1 + (int(total_xp) // 100)
xp_restant = 100 - (int(total_xp) % 100)

# --- INTERFACE ---
col_av, col_txt = st.columns([1, 4])
with col_av:
    st.image("https://api.dicebear.com/7.x/notionists/svg?seed=Felix", width=80)
with col_txt:
    st.title(f"Héros Niveau {niveau}")
    st.progress((int(total_xp) % 100) / 100)
    st.caption(f"XP Total : {int(total_xp)} | Prochain niveau : {xp_restant} XP")

# --- QUÊTES ---
tab1, tab2, tab3 = st.tabs(["⚡ Action", "📜 Historique", "📊 Stats"])

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.header("🧠")
        if st.button("Anki (+10 XP)"):
            save_action(10, "Intellect", "Révision")
            st.rerun()
    with col2:
        st.header("💪")
        if st.button("Sport (+20 XP)"):
            save_action(20, "Force", "Séance")
            st.rerun()
    with col3:
        st.header("🛡️")
        if st.button("Admin (+5 XP)"):
            save_action(5, "Gestion", "Tâche Admin")
            st.rerun()

    st.divider()
    with st.expander("Quête Personnalisée"):
        task = st.text_input("Description de la tâche :")
        xp_val = st.slider("Valeur XP", 5, 50, 10)
        if st.button("Valider la quête"):
            if task:
                save_action(xp_val, "Gestion", task)
                st.rerun()

with tab2:
    st.subheader("Dernières actions")
    if not df.empty:
        # On affiche les 5 dernières lignes (inversées pour voir les récentes en haut)
        st.dataframe(df.tail(5).iloc[::-1], use_container_width=True)

with tab3:
    if total_xp > 0:
        st.bar_chart({"Intellect": xp_intellect, "Force": xp_force, "Gestion": xp_gestion})
    else:
        st.info("Fais une première action pour voir tes stats !")
