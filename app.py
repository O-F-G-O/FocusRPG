import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Dashboard", page_icon="⚫", layout="wide")

# --- CSS MINIMALISTE ---
st.markdown("""
    <style>
    .stApp { background-color: #FAFAFA; }
    .stButton>button {
        width: 100%;
        border: 1px solid #444;
        border-radius: 4px;
        background-color: white;
        color: #333;
        font-weight: 500;
    }
    .stButton>button:hover { background-color: #333; color: white; }
    .digital-clock {
        font-family: 'Courier New', Courier, monospace;
        font-size: 80px;
        font-weight: bold;
        color: #333;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR DE CONNEXION ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(secrets["spreadsheet"])

# --- FONCTIONS TACHES (PERSISTANTES) ---
def load_tasks():
    try:
        sh = get_db()
        ws = sh.worksheet("Tasks")
        # Récupère tout sauf l'entête
        records = ws.col_values(1)[1:]
        return records
    except:
        return []

def add_task_to_db(task_name):
    try:
        sh = get_db()
        ws = sh.worksheet("Tasks")
        ws.append_row([task_name])
    except:
        st.error("Erreur d'ajout")

def delete_task_from_db(task_name):
    try:
        sh = get_db()
        ws = sh.worksheet("Tasks")
        cell = ws.find(task_name)
        if cell:
            ws.delete_rows(cell.row)
    except:
        pass

# --- FONCTIONS XP ---
def save_xp(amount, type_stat, comment=""):
    try:
        sh = get_db()
        ws = sh.worksheet("Data")
        ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), type_stat, amount, comment])
        st.toast(f"XP Sauvegardé (+{amount})")
    except:
        st.error("Erreur XP")

def load_xp_total():
    try:
        sh = get_db()
        ws = sh.worksheet("Data")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return 0, pd.DataFrame()
        df["XP"] = pd.to_numeric(df["XP"], errors='coerce').fillna(0)
        return int(df["XP"].sum()), df
    except:
        return 0, pd.DataFrame()

# --- CHARGEMENT ---
total_xp, df_xp = load_xp_total()
niveau = 1 + (total_xp // 100)
active_tasks = load_tasks()

# --- LAYOUT ---
col_side, col_main = st.columns([1, 2.5], gap="large")

with col_side:
    st.caption(f"NIVEAU {niveau} • {total_xp} XP")
    st.progress((total_xp % 100) / 100)
    st.write("---")
    
    st.subheader("TACHES")
    
    # Antidote autocomplete : on change la clé à chaque fois
    new_task = st.text_input("Saisir...", key=f"input_{len(active_tasks)}", label_visibility="collapsed")
    if st.button("Ajouter"):
        if new_task and new_task not in active_tasks:
            add_task_to_db(new_task)
            st.rerun()
    
    st.write("")
    for i, task in enumerate(active_tasks):
        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
        with c1: st.markdown(f"{task}")
        with c2: # Bouton Valider
            if st.button("✓", key=f"v_{i}"):
                save_xp(10, "Gestion", task)
                delete_task_from_db(task)
                st.rerun()
        with c3: # Bouton Poubelle (Supprimer sans XP)
            if st.button("×", key=f"d_{i}"):
                delete_task_from_db(task)
                st.rerun()

with col_main:
    mode = st.radio("NAV", ["SPORT", "ADMIN"], horizontal=True, label_visibility="collapsed")
    st.write("---")

    if mode == "SPORT":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### MAISON (20 MIN)")
            if st.button("LANCER TIMER"):
                spot = st.empty()
                for s in range(20*60, -1, -1):
                    m, sec = divmod(s, 60)
                    spot.markdown(f'<div class="digital-clock">{m:02d}:{sec:02d}</div>', unsafe_allow_html=True)
                    time.sleep(1)
                st.success("Fini")
            if st.button("Valider Maison (+20)"):
                save_xp(20, "Force", "Maison")
                st.rerun()
        with c2:
            st.markdown("##### SALLE (1H)")
            if st.button("Programme"):
                st.session_state.workout = "Squat / DC / Rowing / Presse / Gainage"
            if 'workout' in st.session_state:
                st.info(st.session_state.workout)
                if st.button("Valider Salle (+50)"):
                    save_xp(50, "Force", "Salle")
                    del st.session_state.workout
                    st.rerun()
    
    else: # Mode ADMIN
        ca, cb = st.columns(2)
        with ca:
            if st.button("Agenda / Mail (+5)"):
                save_xp(5, "Gestion", "Admin")
                st.rerun()
        with cb:
            if st.button("Session Anki (+15)"):
                save_xp(15, "Intellect", "Anki")
                st.rerun()
