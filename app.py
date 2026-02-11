import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Mon RPG Vie", page_icon="🎮", layout="centered")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fonction pour charger les données
def load_data():
    try:
        # On lit la feuille. ttl=0 force la mise à jour immédiate.
        df = conn.read(worksheet="Data", ttl=0)
        return df
    except:
        return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])

# Fonction pour sauvegarder une action
def save_action(xp_amount, type_stat, comment=""):
    df = load_data()
    new_row = pd.DataFrame([{
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Type": type_stat,
        "XP": xp_amount,
        "Commentaire": comment
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="Data", data=updated_df)
    st.toast(f"Sauvegardé ! (+{xp_amount} XP)", icon="💾")

# --- CALCUL DU NIVEAU ---
try:
    df = load_data()
    if not df.empty:
        total_xp = df["XP"].sum()
        xp_intellect = df[df["Type"] == "Intellect"]["XP"].sum()
        xp_force = df[df["Type"] == "Force"]["XP"].sum()
        xp_gestion = df[df["Type"] == "Gestion"]["XP"].sum()
    else:
        total_xp, xp_intellect, xp_force, xp_gestion = 0, 0, 0, 0
except:
    st.error("Connexion à la base de données en cours... (ou erreur de config)")
    total_xp, xp_intellect, xp_force, xp_gestion = 0, 0, 0, 0

niveau = 1 + (int(total_xp) // 100)
xp_restant = 100 - (int(total_xp) % 100)

# --- INTERFACE ---
st.title(f"Héros Niveau {niveau} 🛡️")
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
    task = st.text_input("Quête perso terminée ?")
    if st.button("Valider (+15 XP)"):
        if task:
            save_action(15, "Gestion", task)
            st.rerun()

with tab2:
    st.subheader("Dernières actions")
    if not df.empty:
        st.dataframe(df.tail(5).sort_values("Date", ascending=False), use_container_width=True)

with tab3:
    st.bar_chart({"Intellect": xp_intellect, "Force": xp_force, "Gestion": xp_gestion})
