import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- CSS (ALIGNEMENT PARFAIT & SOBRE) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #333; }
    
    /* Avatar Header */
    img.avatar-small { border-radius: 8px; border: 2px solid #333; }
    
    /* BOUTONS : CENTRAGE PARFAIT DU TEXTE/ICONE */
    .stButton>button {
        width: 100%;
        height: auto;
        min-height: 38px; /* Hauteur standard pour alignement */
        border: 1px solid #333;
        border-radius: 4px;
        background-color: transparent;
        color: #333;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.9em;
        margin-top: 0px;
        
        /* La magie pour centrer le ✓ et le × */
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 0px;
        line-height: 1;
    }
    
    .stButton>button:hover {
        background-color: #333; 
        color: white;
        border-color: #333;
    }
    
    /* Pour supprimer le décalage parfois causé par des paragraphes vides */
    .stButton p { margin: 0px; padding: 0px; }

    /* Headers */
    .section-header {
        border-bottom: 2px solid #333;
        padding-bottom: 5px; margin-bottom: 15px;
        font-weight: 900; letter-spacing: -0.5px; font-size: 1.1em;
    }
    
    /* Alignement vertical global des colonnes */
    div[data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INIT SESSION STATE ---
if 'gym_current_prog' not in st.session_state:
    st.session_state['gym_current_prog'] = None

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
        st.toast(f"+{amt} XP")
    except: st.error("Erreur Save")

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0
        return int(pd.to_numeric(df["XP"], errors='coerce').sum())
    except: return 0

# --- DATA SPORT : 8 PROGRAMMES FULL BODY ---
FULL_BODY_PROGRAMS = {
    "FB1. STRENGTH FOUNDATION": "SQUAT BARRE : 3 x 5 (Repos 3min)\nDEVELOPPÉ COUCHÉ : 3 x 5 (Repos 3min)\nROWING BARRE : 3 x 6 (Repos 2min)\nSOULEVÉ DE TERRE ROUMAIN : 3 x 8 (Repos 2min)\nGAINAGE PLANCHE : 3 x 1min",
    "FB2. HYPERTROPHY MACHINES": "PRESSE À CUISSES : 3 x 12 (Repos 90s)\nTIRAGE POULIE HAUTE : 3 x 12 (Repos 90s)\nCHEST PRESS MACHINE : 3 x 12 (Repos 90s)\nLEG CURL ASSIS : 3 x 15 (Repos 60s)\nELEVATIONS LATERALES : 3 x 15 (Repos 60s)",
    "FB3. ATHLETIC & POWER": "POWER CLEAN : 5 x 3 (Repos 2min)\nFENTES SAUTÉES : 3 x 8/jambe (Repos 90s)\nTRACTIONS : 4 x MAX (Repos 90s)\nDIPS : 4 x MAX (Repos 90s)\nKETTLEBELL SWING : 3 x 20 (Repos 60s)",
    "FB4. DUMBBELL ONLY": "GOBLET SQUAT : 4 x 10 (Repos 90s)\nDEVELOPPÉ HALTERES INCLINÉ : 3 x 10 (Repos 90s)\nROWING HALTERE : 3 x 12/bras (Repos 60s)\nFENTES ARRIERES : 3 x 10/jambe (Repos 90s)\nCURL + TRICEPS HALTERE : 3 x 12 (Super-set)",
    "FB5. POSTERIOR CHAIN": "SOULEVÉ DE TERRE : 3 x 5 (Repos 3min)\nTRACTIONS NEUTRES : 3 x 8 (Repos 2min)\nHIP THRUST : 3 x 10 (Repos 2min)\nINVERTED ROW : 3 x 12 (Repos 90s)\nFACE PULLS : 3 x 15 (Repos 60s)",
    "FB6. ANTERIOR FOCUS": "FRONT SQUAT : 3 x 8 (Repos 2min)\nDEVELOPPÉ MILITAIRE : 3 x 8 (Repos 2min)\nFENTES BULGARES : 3 x 10/jambe (Repos 90s)\nPOMPES LESTÉES : 3 x 12 (Repos 90s)\nAB WHEEL : 3 x 10 (Repos 90s)",
    "FB7. METABOLIC CIRCUIT": "Circuit - 4 tours - 60s repos :\nTHRUSTERS x 10\nRENEGADE ROW x 8/bras\nMOUNTAIN CLIMBERS x 20/jambe\nPUSH-UPS x MAX\nJUMP SQUATS x 15",
    "FB8. THE GRIND (DENSITÉ)": "SQUAT : 10min AMRAP (10RM)\nRepos 5min\nBENCH PRESS : 10min AMRAP (10RM)\nRepos 5min\nTRACTIONS : 10min AMRAP"
}

# --- LOGIQUE ---
total_xp = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
xp_needed = 100 - progress_pct

# === EN-TÊTE ===
c_avatar, c_infos = st.columns([0.1, 0.9])
with c_avatar:
    st.image("avatar.png", width=80)
with c_infos:
    st.markdown(f"### SELECTA | NIVEAU {niveau}")
    st.caption(f"**{total_xp} XP** ACQUIS • PROCHAIN : **{xp_needed} XP**")

st.progress(progress_pct / 100)
st.write("---")

# === LAYOUT PRINCIPAL ===
col_left, col_right = st.columns([1, 2], gap="large")

# GAUCHE : TÂCHES
with col_left:
    st.markdown('<p class="section-header">📌 TÂCHES</p>', unsafe_allow_html=True)
    new_t = st.text_input("Ajouter...", label_visibility="collapsed")
    if st.button("AJOUTER"):
        if new_t: add_task(new_t); st.rerun()
    
    st.write("")
    tasks = load_tasks()
    for i, t in enumerate(tasks):
        # Colonnes ajustées pour un rendu compact et centré
        c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
        
        with c1: 
            st.text(t)
        with c2: 
            if st.button("✓", key=f"v_{i}"):
                save_xp(10, "Gestion", t); del_task(t); st.rerun()
        with c3:
            if st.button("×", key=f"x_{i}"):
                del_task(t); st.rerun()

# DROITE : ACTIONS
with col_right:
    
    # --- SECTION SPORT ---
    st.markdown('<p class="section-header">⚡ 01. SPORT (FULL BODY)</p>', unsafe_allow_html=True)
    
    c_home, c_gym = st.columns(2, gap="medium")
    
    # COLONNE 1 : MAISON
    with c_home:
        st.markdown("##### 🏠 MAISON")
        if st.button("⏱️ TIMER (20 MIN)"):
            ph = st.empty()
            for s in range(20*60, -1, -1):
                m, sec = divmod(s, 60)
                ph.markdown(f'<h2 style="text-align:center;">{m:02d}:{sec:02d}</h2>', unsafe_allow_html=True)
                time.sleep(1)
        
        st.write("") 
        if st.button("VALIDER MAISON (+20 XP)"):
            save_xp(20, "Force", "Maison"); st.rerun()

    # COLONNE 2 : SALLE
    with c_gym:
        st.markdown("##### 🏋️ SALLE")
        
        if st.button("🎲 GÉNÉRER PROGRAMME"):
            prog_name, prog_details = random.choice(list(FULL_BODY_PROGRAMS.items()))
            st.session_state['gym_current_prog'] = (prog_name, prog_details)
            st.rerun() 

        # Logique simplifiée : plus de "else" avec le message bleu
        if st.session_state['gym_current_prog']:
            name, details = st.session_state['gym_current_prog']
            
            st.write("") # Petit espace
            st.markdown(f"**{name}**")
            for l in details.split('\n'):
                st.markdown(f"- {l}")

            if st.button("VALIDER SALLE (+50 XP)"):
                save_xp(50, "Force", f"FB: {name}"); st.session_state['gym_current_prog'] = None; st.rerun()

    st.write("---")

    # ETUDES
    st.markdown('<p class="section-header">🧠 02. ETUDES</p>', unsafe_allow_html=True)
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("ANKI (+15 XP)"): save_xp(15, "Intellect", "Anki"); st.rerun()
    with ce2:
        if st.button("COURS (+20 XP)"): save_xp(20, "Intellect", "Etudes"); st.rerun()

    st.write("---")

    # ADMIN
    st.markdown('<p class="section-header">💼 03. ADMIN</p>', unsafe_allow_html=True)
    if st.button("MAILS / AGENDA (+5 XP)"):
        save_xp(5, "Gestion", "Admin"); st.rerun()
