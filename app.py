import streamlit as st
import pandas as pd
import gspread
import time
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- CSS (RETOUR AU STYLE CLAIR & BRUT V9) ---
st.markdown("""
    <style>
    /* Fond clair */
    .stApp { background-color: #F8F9FA; color: #333; }
    
    /* Boîte de l'Avatar (Style V1 amélioré) */
    .avatar-box {
        background-color: white;
        border: 3px solid #333;
        border-radius: 4px;
        padding: 15px;
        text-align: center;
        box-shadow: 3px 3px 0px #333; /* Petit effet d'ombre "brut" */
    }
    .avatar-img {
        width: 100%;
        max-width: 150px;
        border-radius: 4px;
        border: 2px solid #333;
        margin-bottom: 10px;
    }
    .avatar-stat { font-weight: bold; font-size: 1.1em; }

    /* Barre d'XP 'Brute' */
    .stProgress > div > div > div > div { background-color: #333; }

    /* Boutons Outline (Style V9) */
    .stButton>button {
        width: 100%;
        border: 2px solid #333;
        border-radius: 2px;
        background-color: white;
        color: #333;
        font-weight: 700;
        text-transform: uppercase;
    }
    .stButton>button:hover { background-color: #333; color: white; }

    /* Headers de section */
    .section-header {
        border-bottom: 2px solid #333;
        padding-bottom: 5px; margin-bottom: 15px;
        font-weight: 900; letter-spacing: -0.5px; font-size: 1.2em;
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
    try: return get_db().worksheet("Tasks").col_values(1)[1:]
    except: return []

def add_task(t): 
    try: get_db().worksheet("Tasks").append_row([t])
    except: pass

def del_task(t):
    try: ws = get_db().worksheet("Tasks"); cell = ws.find(t); ws.delete_rows(cell.row)
    except: pass

def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP ! 🔥")
    except: st.error("Erreur Save")

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0
        return int(pd.to_numeric(df["XP"], errors='coerce').sum())
    except: return 0

# --- DATA SPORT : 8 PROGRAMMES FULL BODY (OPTIMISÉS 1H) ---
FULL_BODY_PROGRAMS = {
    "FB1. STRENGTH FOUNDATION (Lourd)": "SQUAT BARRE : 3 x 5 (Repos 3min)\nDEVELOPPÉ COUCHÉ : 3 x 5 (Repos 3min)\nROWING BARRE (Pendlay) : 3 x 6 (Repos 2min)\nSOULEVÉ DE TERRE ROUMAIN : 3 x 8 (Repos 2min)\nGAINAGE PLANCHE : 3 x 1min",
    "FB2. HYPERTROPHY MACHINES (Volume)": "PRESSE À CUISSES : 3 x 12 (Repos 90s)\nTIRAGE POULIE HAUTE : 3 x 12 (Repos 90s)\nCHEST PRESS MACHINE : 3 x 12 (Repos 90s)\nLEG CURL ASSIS : 3 x 15 (Repos 60s)\nELEVATIONS LATERALES MACHINE : 3 x 15 (Repos 60s)",
    "FB3. ATHLETIC & POWER": "POWER CLEAN (Épaulé) : 5 x 3 (Repos 2min)\nFENTES SAUTÉES : 3 x 8/jambe (Repos 90s)\nTRACTIONS (ou assistées) : 4 x MAX (Repos 90s)\nDIPS (ou assistés) : 4 x MAX (Repos 90s)\nKETTLEBELL SWING : 3 x 20 (Repos 60s)",
    "FB4. DUMBBELL ONLY (Haltères)": "GOBLET SQUAT HALTERE : 4 x 10 (Repos 90s)\nDEVELOPPÉ HALTERES INCLINÉ : 3 x 10 (Repos 90s)\nROWING HALTERE UNILATERAL : 3 x 12/bras (Repos 60s)\nFENTES ARRIERES HALTERES : 3 x 10/jambe (Repos 90s)\nCURL MARTEAU + EXT TRICEPS HALTERE : 3 x 12 (Super-set, Repos 60s)",
    "FB5. POSTERIOR CHAIN FOCUS (Dos/Ischios)": "SOULEVÉ DE TERRE CLASSIQUE : 3 x 5 (Repos 3min)\nTRACTIONS PRISE NEUTRE : 3 x 8 (Repos 2min)\nHIP THRUST BARRE : 3 x 10 (Repos 2min)\nINVERTED ROW (Poids du corps) : 3 x 12 (Repos 90s)\nFACE PULLS POULIE : 3 x 15 (Repos 60s)",
    "FB6. ANTERIOR FOCUS (Quad/Pecs)": "FRONT SQUAT (ou Goblet lourd) : 3 x 8 (Repos 2min)\nDEVELOPPÉ MILITAIRE DEBOUT : 3 x 8 (Repos 2min)\nFENTES BULGARES : 3 x 10/jambe (Repos 90s)\nPOMPES LESTÉES (ou machine pecs) : 3 x 12 (Repos 90s)\nAB WHEEL (Roulette abdos) : 3 x 10 (Repos 90s)",
    "FB7. METABOLIC CIRCUIT (Intensité)": "Circuit - 4 tours - 60s repos entre tours :\n1. THRUSTERS (Haltères) x 10\n2. RENEGADE ROW x 8/bras\n3. MOUNTAIN CLIMBERS x 20/jambe\n4. PUSH-UPS x MAX\n5. JUMP SQUATS x 15",
    "FB8. 'THE GRIND' (Densité)": "SQUAT : 10min AMRAP (As Many Reps As Possible) avec un poids de 10RM.\nRepos 5min.\nBENCH PRESS : 10min AMRAP avec un poids de 10RM.\nRepos 5min.\nTRACTIONS : 10min AMRAP (poids du corps).\n(Objectif : faire le max de volume en 10min par exo)"
}

# --- LOGIQUE & LVL ---
total_xp = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
xp_needed = 100 - progress_pct

# --- INTERFACE ---

# EN-TÊTE : AVATAR À GAUCHE, STATS À DROITE
col_head1, col_head2 = st.columns([1, 3])

with col_head1:
    # La boîte Avatar simple et efficace
    st.markdown(f"""
        <div class="avatar-box">
            <img src="avatar.png" class="avatar-img" onerror="this.style.display='none'">
            <div style="margin-top:10px;">
                <span style="font-size:0.9em; color:#555;">HÉROS</span><br>
                <span class="avatar-stat">SELECTA</span>
            </div>
            <div style="margin-top:10px; border-top: 2px solid #eee; padding-top:5px;">
                <span style="font-size:0.9em; color:#555;">NIVEAU</span><br>
                <span class="avatar-stat" style="font-size:2em;">{niveau}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head2:
    # Stats et Barre d'XP
    st.markdown(f"### PROCHAIN NIVEAU : {xp_needed} XP")
    st.progress(progress_pct / 100)
    st.caption(f"TOTAL XP ACQUIS : {total_xp} • Objectif : 100 XP")

st.write("---")

# LAYOUT PRINCIPAL (1/3 Tâches, 2/3 Actions)
col_left, col_right = st.columns([1, 2], gap="large")

# === GAUCHE : TO-DO LIST ===
with col_left:
    st.markdown('<p class="section-header">📌 TÂCHES DU JOUR</p>', unsafe_allow_html=True)
    
    new_t = st.text_input("Ajouter une tâche...", label_visibility="collapsed")
    if st.button("AJOUTER TÂCHE"):
        if new_t: add_task(new_t); st.rerun()
    
    st.write("")
    tasks = load_tasks()
    for i, t in enumerate(tasks):
        # Ratios : Texte (65%), Valider (25%), Supprimer (10% - moitié taille)
        c1, c2, c3 = st.columns([0.65, 0.25, 0.1])
        with c1: st.text(t)
        with c2: 
            if st.button("✓", key=f"v_{i}"):
                save_xp(10, "Gestion", t); del_task(t); st.rerun()
        with c3:
            if st.button("×", key=f"x_{i}"):
                del_task(t); st.rerun()

# === DROITE : ACTIONS SUPERPOSÉES ===
with col_right:
    
    # 1. SPORT (Avec les 8 FB Programs)
    st.markdown('<p class="section-header">⚡ 01. SPORT & FULL BODY</p>', unsafe_allow_html=True)
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        if st.button("CHRONO 20 MIN (MAISON)"):
            ph = st.empty()
            for s in range(20*60, -1, -1):
                m, sec = divmod(s, 60)
                ph.markdown(f'<h2 style="text-align:center; font-family:monospace;">{m:02d}:{sec:02d}</h2>', unsafe_allow_html=True)
                time.sleep(1)
            st.success("TERMINE !")
        if st.button("VALIDER MAISON (+20 XP)"):
            save_xp(20, "Force", "Maison"); st.rerun()
            
    with c_s2:
        choice = st.selectbox("CHOISIR SÉANCE FULL BODY", list(FULL_BODY_PROGRAMS.keys()))
        if st.button("VOIR LE PROGRAMME"):
            st.info(FULL_BODY_PROGRAMS[choice])
        if st.button("VALIDER SALLE (+50 XP)"):
            save_xp(50, "Force", f"FB: {choice}"); st.rerun()

    st.write("---")

    # 2. ETUDES
    st.markdown('<p class="section-header">🧠 02. ETUDES & FOCUS</p>', unsafe_allow_html=True)
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("SESSION ANKI (+15 XP)"): save_xp(15, "Intellect", "Anki"); st.rerun()
    with ce2:
        if st.button("REDACTION / COURS (+20 XP)"): save_xp(20, "Intellect", "Etudes"); st.rerun()

    st.write("---")

    # 3. ADMIN
    st.markdown('<p class="section-header">💼 03. ADMINISTRATION</p>', unsafe_allow_html=True)
    if st.button("GESTION MAILS & AGENDA (+5 XP)"):
        save_xp(5, "Gestion", "Admin"); st.rerun()
