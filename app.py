import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION SOBRE ---
st.set_page_config(page_title="Dashboard", page_icon="⚫", layout="wide")

# --- CSS MINIMALISTE (STYLE SUISSE) ---
st.markdown("""
    <style>
    /* Fond général plus doux */
    .stApp {
        background-color: #FAFAFA;
    }
    
    /* Style des boutons : Fin et élégant (Outline) */
    .stButton>button {
        width: 100%;
        border: 1px solid #444;
        border-radius: 4px;
        background-color: white;
        color: #333;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #333;
        color: white;
        border-color: #333;
    }

    /* Le Timer style "Horloge Digitale" */
    .digital-clock {
        font-family: 'Courier New', Courier, monospace;
        font-size: 80px;
        font-weight: bold;
        color: #333;
        text-align: center;
        letter-spacing: -2px;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    /* Titres sobres */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR (IDENTIQUE V4) ---
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
        st.toast(f"Sauvegardé. (+{xp_amount})")
    except Exception as e:
        st.error(f"Erreur : {e}")

def load_data():
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: 
            return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])
        return df
    except:
        return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])

# --- DATA SPORT (TEXTE SIMPLE) ---
SEANCES_GYM = {
    "A": "**SEANCE A (Barres)**\n\nSquat (3x8)\nDéveloppé Couché (3x10)\nRowing Barre (3x10)\nPresse cuisses (3x12)\nGainage (3x1min)",
    "B": "**SEANCE B (Haltères)**\n\nFentes (3x12)\nDéveloppé Militaire (3x10)\nSoulevé de terre (3x10)\nBiceps/Triceps (3x12)\nAbdos (3x20)",
    "C": "**SEANCE C (Machines)**\n\nPresse (4x10)\nTirage Vertical (4x10)\nChest Press (4x10)\nLeg Extension (3x15)\nElliptique (10min)",
    "D": "**SEANCE D (Hybride)**\n\nGoblet Squat (3x12)\nPompes (3xMax)\nTirage Câble (3x12)\nKettlebell Swing (3x15)\nPlanche (3x45s)"
}

# --- INIT SESSION ---
if 'todos' not in st.session_state: st.session_state.todos = ["Vérifier Agenda", "Répondre Mails"]

# --- CALCUL NIVEAU (DISCRET) ---
df = load_data()
if not df.empty and "XP" in df.columns:
    df["XP"] = pd.to_numeric(df["XP"], errors='coerce').fillna(0)
    total_xp = df["XP"].sum()
else:
    total_xp = 0
niveau = 1 + (int(total_xp) // 100)

# --- LAYOUT ---
col_sidebar, col_main = st.columns([1, 2.5], gap="large")

# === COLONNE GAUCHE : TO-DO LIST (STYLE NOTEPAD) ===
with col_sidebar:
    st.caption(f"NIVEAU {niveau} • {int(total_xp)} XP")
    st.progress((int(total_xp) % 100) / 100)
    st.write("---")
    
    st.subheader("TACHES")
    
    # Input discret
    new_task = st.text_input("Nouvelle entrée...", label_visibility="collapsed")
    if st.button("Ajouter"):
        if new_task:
            st.session_state.todos.append(new_task)
            st.rerun()
    
    st.write("") # Espace
    
    # Liste épurée
    if not st.session_state.todos:
        st.caption("Aucune tâche en cours.")
    
    for i, task in enumerate(st.session_state.todos):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"{task}")
        with c2:
            if st.button("✓", key=f"done_{i}"):
                save_action(10, "Gestion", f"Tâche : {task}")
                st.session_state.todos.pop(i)
                st.rerun()

# === COLONNE DROITE : ACTION CENTER ===
with col_main:
    # Navigation minimaliste par "Radio" au lieu de gros onglets
    mode = st.radio("NAVIGATION", ["SPORT", "FOCUS / ADMIN"], horizontal=True, label_visibility="collapsed")
    st.write("---")

    if mode == "SPORT":
        c1, c2 = st.columns(2)
        
        # BLOC 1 : MAISON
        with c1:
            st.markdown("##### HOME • 20 MIN")
            st.caption("Timer focus sans distraction.")
            
            if st.button("LANCER LE TIMER"):
                timer_spot = st.empty()
                # Décompte
                for seconds in range(20 * 60, -1, -1):
                    mins, secs = divmod(seconds, 60)
                    timer_spot.markdown(f'<div class="digital-clock">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
                    time.sleep(1)
                st.success("Terminé.")
            
            st.write("")
            if st.button("Valider Séance Maison"):
                save_action(20, "Force", "Maison 20min")
                st.rerun()

        # BLOC 2 : SALLE
        with c2:
            st.markdown("##### GYM • 1H")
            st.caption("Programme aléatoire.")
            
            if st.button("Générer Programme"):
                seance_id = random.choice(list(SEANCES_GYM.keys()))
                st.session_state.current_workout = SEANCES_GYM[seance_id]
            
            if 'current_workout' in st.session_state:
                st.info(st.session_state.current_workout)
                if st.button("Valider Séance Salle"):
                    save_action(50, "Force", "Salle Full Body")
                    del st.session_state.current_workout
                    st.rerun()

    elif mode == "FOCUS / ADMIN":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### ADMIN")
            if st.button("Rangement / Agenda (+5)"):
                save_action(5, "Gestion", "Admin rapide")
                st.rerun()
                
        with c2:
            st.markdown("##### INTELLECT")
            if st.button("Session Anki (+15)"):
                save_action(15, "Intellect", "Anki")
                st.rerun()
        
        st.write("---")
        st.caption("Dernières entrées :")
        st.dataframe(df.tail(3)[["Date", "Type", "XP"]].iloc[::-1], use_container_width=True, hide_index=True)
