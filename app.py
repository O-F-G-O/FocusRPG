import streamlit as st
import time
import random

# --- CONFIGURATION ---
st.set_page_config(page_title="Mon RPG Vie", page_icon="🎮", layout="centered")

# --- CSS POUR LE LOOK "JEU VIDÉO" ---
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .big-stat {
        font-size: 30px !important;
        font-weight: bold;
    }
    .xp-gain {
        color: green;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION DES STATS (SAUVEGARDE TEMPORAIRE) ---
# Note : Pour l'instant, si tu fermes l'onglet, ça revient à zéro. 
# On connectera une "Base de données" (Google Sheet) à l'étape d'après pour que ça reste tout le temps.
if 'xp_intellect' not in st.session_state: st.session_state.xp_intellect = 0
if 'xp_force' not in st.session_state: st.session_state.xp_force = 0
if 'xp_gestion' not in st.session_state: st.session_state.xp_gestion = 0
if 'niveau' not in st.session_state: st.session_state.niveau = 1

# --- FONCTION POUR GAGNER DE L'XP ---
def gain_xp(amount, type_stat):
    if type_stat == "Intellect":
        st.session_state.xp_intellect += amount
    elif type_stat == "Force":
        st.session_state.xp_force += amount
    elif type_stat == "Gestion":
        st.session_state.xp_gestion += amount
    
    # Vérifier le Level Up (tous les 100 XP au total)
    total_xp = st.session_state.xp_intellect + st.session_state.xp_force + st.session_state.xp_gestion
    new_level = 1 + (total_xp // 100)
    if new_level > st.session_state.niveau:
        st.session_state.niveau = new_level
        st.balloons()
        st.toast(f"🎉 LEVEL UP ! Tu es maintenant niveau {new_level} !", icon="🆙")
    else:
        st.toast(f"+{amount} XP ({type_stat})", icon="✨")

# --- HEADER : TON PERSONNAGE ---
col1, col2 = st.columns([1, 3])
with col1:
    st.image("https://api.dicebear.com/7.x/avataaars/svg?seed=Felix", width=100) # Avatar généré
with col2:
    st.title(f"Héros Niveau {st.session_state.niveau}")
    total_xp = st.session_state.xp_intellect + st.session_state.xp_force + st.session_state.xp_gestion
    xp_restant = 100 - (total_xp % 100)
    st.caption(f"XP Total : {total_xp} | Prochain niveau dans {xp_restant} XP")
    st.progress((total_xp % 100) / 100)

st.divider()

# --- LES QUÊTES DU JOUR ---
st.subheader("📜 Quêtes du Jour")

col_int, col_for, col_ges = st.tabs(["🧠 Intellect (Anki)", "💪 Force (Sport)", "🛡️ Gestion (Admin)"])

with col_int:
    st.write("Objectif : Ne pas se laisser dépasser par les cartes.")
    if st.button("J'ai créé 5 nouvelles cartes Anki (+10 XP)"):
        gain_xp(10, "Intellect")
        st.rerun()
    if st.button("J'ai fait ma révision Anki du jour (+20 XP)"):
        gain_xp(20, "Intellect")
        st.rerun()
    st.metric("Niveau Intellect", f"{st.session_state.xp_intellect} XP")

with col_for:
    st.write("Objectif : Bouger, même un peu.")
    sport_choice = st.selectbox("Quelle activité ?", ["Marche rapide (15min)", "Muscu / Gym", "Gros sport"])
    if st.button("Valider la séance (+30 XP)"):
        gain_xp(30, "Force")
        st.success(f"Bien joué pour la séance : {sport_choice}")
        time.sleep(1)
        st.rerun()
    st.metric("Niveau Force", f"{st.session_state.xp_force} XP")

with col_ges:
    st.write("Objectif : Dompter le chaos.")
    if st.button("✅ J'ai checké mon Agenda pour demain (+5 XP)"):
        gain_xp(5, "Gestion")
        st.rerun()
    if st.button("📧 J'ai répondu à un mail chiant (+15 XP)"):
        gain_xp(15, "Gestion")
        st.rerun()
    if st.button("📝 J'ai mis à jour ma checklist (+5 XP)"):
        gain_xp(5, "Gestion")
        st.rerun()
    st.metric("Niveau Gestion", f"{st.session_state.xp_gestion} XP")

st.divider()

# --- VISUALISATION DU PERSONNAGE ---
st.subheader("📊 Stats du Personnage")
chart_data = {
    "Stat": ["🧠 Intellect", "💪 Force", "🛡️ Gestion"],
    "XP": [st.session_state.xp_intellect, st.session_state.xp_force, st.session_state.xp_gestion]
}
st.bar_chart(chart_data, x="Stat", y="XP")

if st.button("Réinitialiser (Attention !)"):
    st.session_state.xp_intellect = 0
    st.session_state.xp_force = 0
    st.session_state.xp_gestion = 0
    st.session_state.niveau = 1
    st.rerun()
