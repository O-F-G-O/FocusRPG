import streamlit as st
import pandas as pd
import gspread
import time
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="⚔️", layout="wide")

# --- CSS PERSONNALISÉ (POUR L'ANIMATION) ---
st.markdown("""
    <style>
    .stApp { background-color: #202124; color: white; }
    
    /* Style de la boîte Avatar */
    .avatar-box {
        border: 4px solid #444;
        border-radius: 10px;
        padding: 10px;
        background-color: #1a1a1a;
        text-align: center;
    }
    
    /* La Barre d'XP Customisée */
    .xp-container {
        width: 100%;
        background-color: #333;
        border-radius: 15px;
        height: 25px;
        position: relative;
        margin-top: 40px;
        margin-bottom: 20px;
        box-shadow: inset 0 0 10px #000;
    }
    
    .xp-fill {
        background: linear-gradient(90deg, #FF4B4B, #FF914D);
        height: 100%;
        border-radius: 15px;
        transition: width 0.5s ease-in-out;
    }
    
    /* Le petit bonhomme qui marche */
    .walker {
        position: absolute;
        top: -35px; /* On le pose SUR la barre */
        height: 50px;
        transition: left 0.5s ease-in-out;
        transform: translateX(-50%); /* Pour centrer le bonhomme sur le curseur */
    }

    /* Boutons stylés */
    .stButton>button {
        background-color: #333;
        color: white;
        border: 1px solid #555;
    }
    .stButton>button:hover {
        border-color: #FF4B4B;
        color: #FF4B4B;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR (CONNEXION) ---
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
    try: 
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t)
        ws.delete_rows(cell.row)
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

# --- LOGIQUE D'ÉVOLUTION ---
total_xp = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100

# ICI : C'est là que tu mettras tes images plus tard
# Je mets des placeholders (liens web) pour que ça marche tout de suite
# Logique : Si niveau < 5, image 1, sinon image 2, etc.
if niveau < 5:
    # Petit bonhomme débutant
    avatar_img = "https://img.icons8.com/color/96/fantasy.png" 
elif niveau < 10:
    # Bonhomme un peu stuffé
    avatar_img = "https://img.icons8.com/color/96/warrior-male.png"
else:
    # Roi
    avatar_img = "https://img.icons8.com/color/96/king-clover.png"

# --- INTERFACE ---

# 1. EN-TÊTE : AVATAR + BARRE ANIMÉE
col_avatar, col_stats = st.columns([1, 4])

with col_avatar:
    # La boîte Avatar (comme V1)
    st.markdown(f"""
        <div class="avatar-box">
            <img src="{avatar_img}" width="100">
            <h3>Niveau {niveau}</h3>
            <p style="color:#aaa">Selecta</p>
        </div>
    """, unsafe_allow_html=True)

with col_stats:
    st.markdown(f"### PROCHAIN NIVEAU : {100 - progress_pct} XP")
    
    # LA MAGIE HTML : La barre avec le bonhomme qui marche dessus
    # On calcule la position 'left' en pourcentage
    st.markdown(f"""
        <div class="xp-container">
            <div class="xp-fill" style="width: {progress_pct}%;"></div>
            <img src="{avatar_img}" class="walker" style="left: {progress_pct}%;">
        </div>
    """, unsafe_allow_html=True)
    
    st.caption(f"XP TOTAL : {total_xp}")

st.write("---")

# 2. COLONNES ACTIONS (Ta disposition préférée)
c_left, c_right = st.columns([1, 2], gap="large")

# GAUCHE : TO-DO LIST
with c_left:
    st.subheader("📌 TÂCHES")
    new_t = st.text_input("Nouvelle...", label_visibility="collapsed")
    if st.button("Ajouter"):
        if new_t: add_task(new_t); st.rerun()
    
    tasks = load_tasks()
    for t in tasks:
        c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
        c1.text(t)
        if c2.button("✓", key=f"v_{t}"):
            save_xp(10, "Gestion", t); del_task(t); st.rerun()
        if c3.button("×", key=f"x_{t}"):
            del_task(t); st.rerun()

# DROITE : STACK D'ACTIONS
with c_right:
    # SPORT
    st.markdown("##### 01. SPORT")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⏱️ TIMER 20 MIN"):
            ph = st.empty()
            for s in range(20*60, -1, -1):
                m, sec = divmod(s, 60)
                ph.markdown(f'<h1 style="text-align:center">{m:02d}:{sec:02d}</h1>', unsafe_allow_html=True)
                time.sleep(1)
            st.success("Fini!")
        if st.button("Valider Maison (+20)"): save_xp(20, "Force", "Maison"); st.rerun()
    with c2:
        prog = st.selectbox("Programme", ["PUSH", "PULL", "LEGS", "FULL BODY"])
        if st.button("Valider Salle (+50)"): save_xp(50, "Force", prog); st.rerun()
    
    st.divider()
    
    # ETUDES
    st.markdown("##### 02. ETUDES")
    c1, c2 = st.columns(2)
    if c1.button("🧠 Anki (+15)"): save_xp(15, "Intellect", "Anki"); st.rerun()
    if c2.button("📝 Cours (+20)"): save_xp(20, "Intellect", "Cours"); st.rerun()

    st.divider()

    # ADMIN
    st.markdown("##### 03. ADMIN")
    if st.button("📧 Mails/Agenda (+5)"): save_xp(5, "Gestion", "Admin"); st.rerun()
