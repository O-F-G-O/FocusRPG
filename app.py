import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Mon Cockpit", page_icon="🚀", layout="wide")

# --- CSS (STYLE POST-IT & TIMER) ---
st.markdown("""
    <style>
    .big-timer {
        font-size: 80px !important;
        font-weight: bold;
        color: #FF4B4B;
        text-align: center;
        margin-top: -20px;
    }
    .todo-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR (V4 ROBUSTE) ---
def get_worksheet():
    secrets = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_url = secrets["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    return sh.worksheet("Data")

def save_action(xp_amount, type_stat, comment=""):
    try:
        ws = get_worksheet()
        ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), type_stat, xp_amount, comment])
        st.toast(f"✅ Validé ! (+{xp_amount} XP)", icon="✨")
    except Exception as e:
        st.error(f"Erreur : {e}")

def load_data():
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])
        return df
    except:
        return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])

# --- DATA SPORT ---
SEANCES_GYM = {
    "A": "🏋️‍♂️ **Full Body A (Barres)**\n- Squat : 3x8\n- Développé Couché : 3x10\n- Rowing Barre : 3x10\n- Presse à cuisses : 3x12\n- Gainage : 3x1 min",
    "B": "🔥 **Full Body B (Haltères)**\n- Fentes marchées : 3x12\n- Développé Militaire : 3x10\n- Soulevé de terre jambes tendues : 3x10\n- Curl Biceps + Triceps : 3x12\n- Abdos : 3x20",
    "C": "⚙️ **Full Body C (Machines)**\n- Presse à cuisses : 4x10\n- Tirage Vertical : 4x10\n- Chest Press : 4x10\n- Leg Extension : 3x15\n- Elliptique : 10 min",
    "D": "⚡ **Full Body D (Hybride)**\n- Goblet Squat : 3x12\n- Pompes : 3xMax\n- Tirage Câble : 3x12\n- Kettlebell Swing : 3x15\n- Planche : 3x45 sec"
}

# --- INIT SESSION ---
if 'todos' not in st.session_state: st.session_state.todos = ["Vérifier Agenda", "Répondre Mails"]

# --- CALCUL NIVEAU ---
df = load_data()
if not df.empty and "XP" in df.columns:
    df["XP"] = pd.to_numeric(df["XP"], errors='coerce').fillna(0)
    total_xp = df["XP"].sum()
else:
    total_xp = 0
niveau = 1 + (int(total_xp) // 100)
xp_restant = 100 - (int(total_xp) % 100)

# --- LAYOUT PRINCIPAL (GAUCHE / DROITE) ---
col_left, col_right = st.columns([1, 2], gap="large")

# === COLONNE GAUCHE : TO-DO LIST (Le "Post-it") ===
with col_left:
    st.markdown(f"### Héros Niv. {niveau} 🛡️")
    st.progress((int(total_xp) % 100) / 100)
    st.caption(f"{int(total_xp)} XP Total")
    
    st.divider()
    
    st.markdown("### 📌 À Faire (Post-it)")
    
    # Zone d'ajout
    new_task = st.text_input("Ajouter une tâche rapide", placeholder="Ex: Appeler banque...")
    if st.button("Ajouter à la liste"):
        if new_task:
            st.session_state.todos.append(new_task)
            st.rerun()
    
    st.write("---")
    
    # La liste persistante
    if not st.session_state.todos:
        st.info("Rien à faire ! 🎉")
    
    for i, task in enumerate(st.session_state.todos):
        c1, c2 = st.columns([0.7, 0.3])
        with c1:
            st.write(f"**{task}**")
        with c2:
            if st.button("✅", key=f"done_{i}", help="Fait (+10 XP)"):
                save_action(10, "Gestion", f"Tâche : {task}")
                st.session_state.todos.pop(i)
                st.rerun()

# === COLONNE DROITE : ACTION (Sport & Focus) ===
with col_right:
    st.markdown("## ⚡ Centre d'Action")
    
    # 1. Mode Sport
    st.info("### 🏋️‍♂️ Session Sport")
    mode_sport = st.radio("Choisis ton mode :", ["🏠 Maison (20min)", "🏢 Salle de Sport (1h)"], horizontal=True)

    if "Maison" in mode_sport:
        st.write("Timer visuel pour ta séance rapide.")
        
        # Le Gros Bouton Timer
        if st.button("▶️ LANCER LE TIMER (20 MIN)"):
            timer_placeholder = st.empty()
            # Compte à rebours de 20 minutes (1200 secondes)
            # Pour le test, tu peux changer 1200 en 10 pour voir si ça marche vite
            total_time = 20 * 60 
            
            for seconds_left in range(total_time, -1, -1):
                mins, secs = divmod(seconds_left, 60)
                # Affichage Géant
                timer_placeholder.markdown(f'<p class="big-timer">{mins:02d}:{secs:02d}</p>', unsafe_allow_html=True)
                time.sleep(1)
            
            timer_placeholder.success("Temps écoulé ! Bien joué champion.")
            st.balloons()
        
        if st.button("Valider la séance (+20 XP)"):
            save_action(20, "Force", "Maison 20min")
            st.rerun()

    else: # Mode Salle
        st.write("Générateur de séance pour ne pas réfléchir.")
        if st.button("🎲 Générer un programme"):
            seance_id = random.choice(list(SEANCES_GYM.keys()))
            st.session_state.current_workout = SEANCES_GYM[seance_id]
        
        if 'current_workout' in st.session_state:
            st.success(st.session_state.current_workout)
            if st.button("J'ai terminé cette séance (+50 XP)"):
                save_action(50, "Force", "Salle Full Body")
                del st.session_state.current_workout
                st.rerun()

    st.divider()

    # 2. Boutons Rapides (Admin / Cerveau)
    st.write("### 🧠 Boost XP Rapide")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📚 Anki Fait (+15 XP)"):
            save_action(15, "Intellect", "Anki")
            st.rerun()
    with c2:
        if st.button("🧹 Rangement Rapide (+5 XP)"):
            save_action(5, "Gestion", "Rangement")
            st.rerun()
