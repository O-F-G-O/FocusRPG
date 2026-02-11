import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta Dash", page_icon="⚫", layout="wide")

# --- CSS (STYLE ÉPURÉ & BOUTONS) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    
    /* Boutons Outline */
    .stButton>button {
        width: 100%;
        border: 1px solid #333;
        border-radius: 2px;
        background-color: white;
        color: #333;
        font-family: 'Inter', sans-serif;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 1px;
    }
    .stButton>button:hover { background-color: #333; color: white; }

    /* Barres de progression */
    .stProgress > div > div > div > div { background-color: #333; }

    /* Section Headers */
    .section-header {
        border-bottom: 1px solid #DDD;
        padding-bottom: 5px;
        margin-bottom: 15px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Timer Style */
    .digital-clock {
        font-family: 'Courier New', monospace;
        font-size: 60px;
        text-align: center;
        color: #333;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR G-SHEETS ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(secrets["spreadsheet"])

def load_tasks():
    try:
        sh = get_db(); ws = sh.worksheet("Tasks")
        return ws.col_values(1)[1:]
    except: return []

def add_task_to_db(task):
    try: sh = get_db(); ws = sh.worksheet("Tasks"); ws.append_row([task])
    except: pass

def delete_task_from_db(task):
    try:
        sh = get_db(); ws = sh.worksheet("Tasks")
        cell = ws.find(task)
        if cell: ws.delete_rows(cell.row)
    except: pass

def save_xp(amount, stat, comment=""):
    try:
        sh = get_db(); ws = sh.worksheet("Data")
        ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), stat, amount, comment])
        st.toast(f"LOGGED: +{amount} XP")
    except: st.error("DATABASE ERROR")

def load_xp_total():
    try:
        sh = get_db(); ws = sh.worksheet("Data")
        df = pd.DataFrame(ws.get_all_records())
        if df.empty: return 0
        return int(pd.to_numeric(df["XP"], errors='coerce').sum())
    except: return 0

# --- DATA SPORT (8 PROGRAMMES OPTIMISÉS) ---
GYM_PROGRAMS = {
    "1. PUSH (PECS/EPAULES)": "BANC HORIZONTAL : 4 x 8 (Repos: 2min)\nDEVELOPPÉ MILITAIRE : 3 x 10 (Repos: 90s)\nECARTÉS HALTÈRES : 3 x 12 (Repos: 60s)\nDIPIES : 3 x MAX (Repos: 90s)\nEXTENSIONS TRICEPS : 3 x 12 (Repos: 60s)",
    "2. PULL (DOS/BICEPS)": "SOULEVÉ DE TERRE : 3 x 5 (Repos: 3min)\nTIRAGE VERTICAL : 4 x 10 (Repos: 90s)\nROWING HALTÈRE : 3 x 12 (Repos: 90s)\nFACEPULL : 3 x 15 (Repos: 60s)\nCURL BICEPS : 3 x 12 (Repos: 60s)",
    "3. LEGS (QUAD/FESSIERS)": "SQUAT BARRE : 4 x 8 (Repos: 3min)\nFENTES BULGARES : 3 x 10 (Repos: 90s)\nPRESSE A CUISSES : 3 x 12 (Repos: 90s)\nLEG CURL : 3 x 15 (Repos: 60s)\nMOLLETS DEBOUT : 4 x 15 (Repos: 60s)",
    "4. FULL BODY A (FORCE)": "SQUAT : 3 x 5\nBENCH PRESS : 3 x 5\nROWING BARRE : 3 x 5\nREST : 3min entre chaque série",
    "5. FULL BODY B (HYPERTROPHIE)": "PRESSE CUISSES : 3 x 12\nTIRAGE DOS : 3 x 12\nDEVELOPPÉ HALTÈRES : 3 x 12\nISCHIOS MACHINE : 3 x 15\nREST : 90s entre chaque série",
    "6. UPPER BODY FOCUS": "TRACTIONS : 3 x MAX\nPOMPES LESTÉES : 3 x 15\nOISEAU HALTÈRES : 3 x 15\nCURL BARRE : 3 x 10\nREST : 60s entre chaque série",
    "7. LOWER BODY PUMP": "SOULEVÉ TERRE JAMBES TENDUES : 3 x 12\nHIP THRUST : 4 x 10\nLEG EXTENSION : 3 x 15\nABDUCTEURS : 3 x 20\nREST : 60s entre chaque série",
    "8. ATHLETIC / FONCTIONNEL": "KETTLEBELL SWINGS : 4 x 20\nBURPEES : 4 x 15\nTRAINER GAINAGE : 3 x 1min\nBOX JUMPS : 4 x 10\nREST : 45s (Intensité haute)"
}

# --- LOGIQUE ---
total_xp = load_xp_total()
level = 1 + (total_xp // 100)
progress = (total_xp % 100) / 100
active_tasks = load_tasks()

# --- TOP BAR (XP SELECTA) ---
st.markdown(f"#### HEROS : SELECTA | NIVEAU {level}")
st.progress(progress)
st.caption(f"{total_xp} XP TOTAL • ENCORE {100 - (total_xp % 100)} XP AVANT LE PROCHAIN NIVEAU")
st.write("---")

# --- LAYOUT DASHBOARD ---
col_left, col_right = st.columns([1, 2], gap="large")

# === COLONNE GAUCHE : TO-DO LIST ===
with col_left:
    st.markdown('<p class="section-header">LISTE DES TACHES</p>', unsafe_allow_html=True)
    
    t_input = st.text_input("ADD_TASK", key="task_in", label_visibility="collapsed")
    if st.button("ENREGISTRER TACHE"):
        if t_input: add_task_to_db(t_input); st.rerun()
    
    st.write("")
    for i, t in enumerate(active_tasks):
        # Ratios : Texte (70%), Valider (20%), Supprimer (10%)
        c1, c2, c3 = st.columns([0.7, 0.2, 0.1])
        with c1: st.text(t)
        with c2: 
            if st.button("✓", key=f"v_{i}"):
                save_xp(10, "Gestion", t); delete_task_from_db(t); st.rerun()
        with c3:
            if st.button("×", key=f"x_{i}"):
                delete_task_from_db(t); st.rerun()

# === COLONNE DROITE : SUPERPOSITION ACTIONS ===
with col_right:
    
    # 1. SPORT
    st.markdown('<p class="section-header">01. SPORT & PERFORMANCE</p>', unsafe_allow_html=True)
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        if st.button("TIMER MAISON (20 MIN)"):
            placeholder = st.empty()
            for s in range(20*60, -1, -1):
                m, sec = divmod(s, 60)
                placeholder.markdown(f'<div class="digital-clock">{m:02d}:{sec:02d}</div>', unsafe_allow_html=True)
                time.sleep(1)
            st.success("SESSION TERMINEE")
        if st.button("LOG MAISON (+20 XP)"):
            save_xp(20, "Force", "Home Workout"); st.rerun()
            
    with c_s2:
        choice = st.selectbox("CHOISIR PROGRAMME GYM", list(GYM_PROGRAMS.keys()))
        if st.button("AFFICHER EXERCICES"):
            st.info(GYM_PROGRAMS[choice])
        if st.button("LOG SALLE (+50 XP)"):
            save_xp(50, "Force", f"Gym: {choice}"); st.rerun()

    st.write("---")

    # 2. ETUDES
    st.markdown('<p class="section-header">02. ETUDES & FOCUS</p>', unsafe_allow_html=True)
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("SESSION ANKI (+15 XP)"):
            save_xp(15, "Intellect", "Anki"); st.rerun()
    with ce2:
        if st.button("REDACTION / COURS (+20 XP)"):
            save_xp(20, "Intellect", "Etudes"); st.rerun()

    st.write("---")

    # 3. ADMIN
    st.markdown('<p class="section-header">03. ADMINISTRATION</p>', unsafe_allow_html=True)
    if st.button("GESTION MAILS & AGENDA (+5 XP)"):
        save_xp(5, "Gestion", "Admin"); st.rerun()
