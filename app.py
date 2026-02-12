import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- CSS (STYLE ÉPURÉ & RPG) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #333; }
    
    /* Barres */
    .stProgress > div > div > div > div { background-color: #333; } 
    .mana-bar .stProgress > div > div > div > div { background-color: #00A8E8 !important; }

    /* Boutons */
    .stButton>button {
        width: 100%; min-height: 38px;
        border: 1px solid #333; border-radius: 4px;
        background-color: transparent; color: #333;
        font-weight: 600; text-transform: uppercase; font-size: 0.85em;
        display: flex; justify-content: center; align-items: center;
    }
    .stButton>button:hover { background-color: #333; color: white; }

    /* Headers */
    .section-header {
        border-bottom: 2px solid #333;
        padding-bottom: 5px; margin-bottom: 15px;
        font-weight: 900; font-size: 1.1em;
    }
    
    /* Boite spéciale pour la liste Anki */
    .anki-box {
        background-color: #fff;
        border: 1px dashed #333;
        padding: 10px;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INIT SESSION ---
if 'gym_current_prog' not in st.session_state: st.session_state['gym_current_prog'] = None

# --- G-SHEETS (LOGIQUE À 2 COLONNES) ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(secrets["spreadsheet"])

# --- GESTION TÂCHES PERSO (COLONNE 1) ---
def load_tasks():
    try: return get_db().worksheet("Tasks").col_values(1)[1:] # Colonne A
    except: return []

def add_task(t): 
    try: 
        ws = get_db().worksheet("Tasks")
        # On trouve la première ligne vide de la Col A
        col_values = ws.col_values(1)
        ws.update_cell(len(col_values) + 1, 1, t)
    except: pass

def del_task(t):
    try: 
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=1)
        ws.update_cell(cell.row, 1, "") # On efface juste le contenu pour pas décaler la col B
    except: pass

# --- GESTION COURS ANKI (COLONNE 2) ---
def load_anki_tasks():
    try: return get_db().worksheet("Tasks").col_values(2)[1:] # Colonne B
    except: return []

def add_anki_task(t): 
    try: 
        ws = get_db().worksheet("Tasks")
        col_values = ws.col_values(2)
        ws.update_cell(len(col_values) + 1, 2, t)
    except: pass

def del_anki_task(t):
    try: 
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=2)
        ws.update_cell(cell.row, 2, "") 
    except: pass

# --- XP SYSTEM ---
def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: st.error("Erreur Save")

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100
        
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
        
        # MANA CALCUL (Basé sur dernière session 'COMBAT')
        anki_logs = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
        
        if anki_logs.empty: mana = 50 
        else:
            last_date = datetime.strptime(anki_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")
            days_diff = (datetime.now() - last_date).days
            mana = max(0, 100 - (days_diff * 15)) 
            
        return xp, mana
    except: return 0, 50

# --- DATA SPORT ---
FULL_BODY_PROGRAMS = {
    "FB1. STRENGTH": "SQUAT 3x5\nBENCH 3x5\nROWING 3x6\nRDL 3x8\nPLANK 3x1min",
    "FB2. HYPERTROPHY": "PRESSE 3x12\nTIRAGE 3x12\nCHEST PRESS 3x12\nLEG CURL 3x15\nELEVATIONS 3x15",
    "FB3. POWER": "CLEAN 5x3\nJUMP LUNGE 3x8\nPULLUPS 4xMAX\nDIPS 4xMAX\nSWING 3x20",
    "FB4. DUMBBELLS": "GOBLET SQUAT 4x10\nINCLINE PRESS 3x10\nROWING 3x12\nLUNGES 3x10\nARMS 3x12",
    "FB7. CIRCUIT": "THRUSTERS x10\nRENEGADE ROW x8\nCLIMBERS x20\nPUSHUPS xMAX\nJUMPS x15"
}

# --- LOGIQUE ---
total_xp, current_mana = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
xp_needed = 100 - progress_pct

# === EN-TÊTE ===
c_avatar, c_infos = st.columns([0.15, 0.85])
with c_avatar:
    st.image("avatar.png", width=90)
with c_infos:
    st.markdown(f"### NIV. {niveau} | SELECTA")
    st.caption(f"**XP : {total_xp}** (Prochain : {xp_needed})")
    st.progress(progress_pct / 100)
    st.caption(f"**MÉMOIRE (MANA) : {current_mana}%**")
    st.progress(current_mana / 100)

st.write("---")

# === LAYOUT ===
col_left, col_right = st.columns([1, 2], gap="large")

# === GAUCHE : TÂCHES QUOTIDIENNES (Admin/Perso) ===
with col_left:
    st.markdown('<p class="section-header">📌 QUÊTES DU JOUR</p>', unsafe_allow_html=True)
    
    new_t = st.text_input("Tâche perso...", label_visibility="collapsed")
    if st.button("AJOUTER TÂCHE"):
        if new_t: add_task(new_t); st.rerun()
    
    st.write("")
    tasks = load_tasks()
    for i, t in enumerate(tasks):
        if t: # On n'affiche pas les cellules vides
            c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
            with c1: st.text(t)
            with c2: 
                if st.button("✓", key=f"vp_{i}"):
                    save_xp(5, "Gestion", t); del_task(t); st.rerun()
            with c3:
                if st.button("×", key=f"xp_{i}"):
                    del_task(t); st.rerun()

# === DROITE : SPORT & ETUDES ===
with col_right:
    
    # --- 01. ETUDES (LE GRIMOIRE) ---
    st.markdown('<p class="section-header">🧠 FORGE DU SAVOIR (ANKI)</p>', unsafe_allow_html=True)
    
    c_create, c_combat = st.columns(2, gap="medium")
    
    # COLONNE CRÉATION (Liste des cours)
    with c_create:
        st.caption("📜 **BACKLOG DES COURS À FICHER**")
        
        # Import Fichier
        with st.expander("📥 IMPORTER LISTE (TXT)"):
            uploaded_file = st.file_uploader("Un cours par ligne", type="txt")
            if uploaded_file and st.button("IMPORTER DANS LE GRIMOIRE"):
                stringio = uploaded_file.getvalue().decode("utf-8")
                count = 0
                for line in stringio.splitlines():
                    if line.strip(): add_anki_task(line.strip()); count += 1
                st.success(f"{count} cours ajoutés !")
                time.sleep(1); st.rerun()
        
        # Ajout Manuel
        new_anki = st.text_input("Nouveau cours...", label_visibility="collapsed", key="anki_input")
        if st.button("AJOUTER AU GRIMOIRE"):
            if new_anki: add_anki_task(new_anki); st.rerun()

        # Liste des Cours
        st.write("")
        anki_tasks = load_anki_tasks()
        if not anki_tasks or all(x == "" for x in anki_tasks):
            st.info("Aucun cours en attente.")
        else:
            for i, t in enumerate(anki_tasks):
                if t:
                    c1, c2 = st.columns([0.8, 0.2])
                    c1.markdown(f"**{t}**")
                    # Ici on valide la CREATION
                    if c2.button("✓", key=f"va_{i}", help="J'ai fini de ficher ce cours"):
                        save_xp(30, "Intellect", f"Création: {t}")
                        del_anki_task(t)
                        st.rerun()

    # COLONNE COMBAT (Révision)
    with c_combat:
        st.caption("⚔️ **CHAMP DE BATAILLE**")
        st.info(f"Mana actuel : **{current_mana}%**")
        
        st.markdown("""
        <div style="text-align:center; margin-bottom:10px; color:#555; font-size:0.8em;">
        Lance Anki et bats-toi contre l'oubli.
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("LANCER LE COMBAT (+20 XP)"):
            save_xp(20, "Intellect", "Combat Anki")
            st.rerun()

    st.write("---")

    # --- 02. SPORT ---
    st.markdown('<p class="section-header">⚡ ENTRAÎNEMENT PHYSIQUE</p>', unsafe_allow_html=True)
    c_home, c_gym = st.columns(2, gap="medium")
    
    with c_home:
        if st.button("⏱️ TIMER 20 MIN"):
            ph = st.empty()
            for s in range(1200, -1, -1):
                m, sec = divmod(s, 60)
                ph.markdown(f'<h3 style="text-align:center;">{m:02d}:{sec:02d}</h3>', unsafe_allow_html=True)
                time.sleep(1)
        if st.button("VALIDER MAISON (+20 XP)"): save_xp(20, "Force", "Maison"); st.rerun()

    with c_gym:
        if st.button("🎲 GÉNÉRER SÉANCE"):
            n, d = random.choice(list(FULL_BODY_PROGRAMS.items()))
            st.session_state['gym_current_prog'] = (n, d)
            st.rerun()
        
        if st.session_state['gym_current_prog']:
            n, d = st.session_state['gym_current_prog']
            st.markdown(f"**{n}**")
            for l in d.split('\n'): st.markdown(f"- {l}")
            if st.button("VALIDER SALLE (+50 XP)"):
                save_xp(50, "Force", n); st.session_state['gym_current_prog']=None; st.rerun()
