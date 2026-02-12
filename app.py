import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- CSS AVANCÉ (ANIMATIONS & COULEURS) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #333; }
    
    /* Barres de progression */
    .stProgress > div > div > div > div { background-color: #333; } 
    .mana-bar .stProgress > div > div > div > div { background-color: #00A8E8 !important; }
    .chaos-bar .stProgress > div > div > div > div { background-color: #D9534F !important; }

    /* Boutons standards */
    .stButton>button {
        width: 100%; min-height: 38px;
        border: 1px solid #333; border-radius: 4px;
        background-color: transparent; color: #333;
        font-weight: 600; text-transform: uppercase; font-size: 0.85em;
        display: flex; justify-content: center; align-items: center;
    }
    .stButton>button:hover { background-color: #333; color: white; }
    
    /* === LOYER : STYLES DYNAMIQUES === */
    
    /* 1. Loyer Payé (Vert Zen) */
    .rent-paid {
        background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;
        padding: 15px; text-align: center; border-radius: 4px; font-weight: 800;
        text-transform: uppercase; letter-spacing: 1px;
    }

    /* 2. Loyer Critique (Animation Pulse Rouge) */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(217, 83, 79, 0.7); transform: scale(1); }
        70% { box-shadow: 0 0 0 10px rgba(217, 83, 79, 0); transform: scale(1.02); }
        100% { box-shadow: 0 0 0 0 rgba(217, 83, 79, 0); transform: scale(1); }
    }
    
    /* On cible le bouton spécifique du loyer critique via CSS hack si besoin, 
       mais ici on utilisera une classe markdown pour l'alerte visuelle */
    .critical-alert {
        animation: pulse-red 2s infinite;
        background-color: #D9534F; color: white;
        padding: 10px; border-radius: 4px; text-align: center; font-weight: bold;
        margin-bottom: 5px; border: 2px solid #c9302c;
    }
    
    .rent-warning { color: #f0ad4e; font-weight: bold; }
    .rent-danger { color: #d9534f; font-weight: bold; }

    /* Headers */
    .section-header {
        border-bottom: 2px solid #333;
        padding-bottom: 5px; margin-bottom: 15px;
        font-weight: 900; font-size: 1.1em;
    }
    
    /* Timer Anki */
    .timer-display {
        font-family: 'Courier New', monospace; font-size: 2em; font-weight: bold;
        color: #d9534f; text-align: center; border: 2px solid #d9534f;
        border-radius: 5px; padding: 10px; margin: 10px 0; background-color: #fff5f5;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INIT SESSION ---
if 'gym_current_prog' not in st.session_state: st.session_state['gym_current_prog'] = None
if 'anki_start_time' not in st.session_state: st.session_state['anki_start_time'] = None

# --- G-SHEETS ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(secrets["spreadsheet"])

def load_tasks(col_idx):
    try: 
        raw = get_db().worksheet("Tasks").col_values(col_idx)[1:]
        return [x for x in raw if x.strip() != ""] 
    except: return []

def add_task(t, col_idx): 
    try: 
        ws = get_db().worksheet("Tasks")
        col_values = ws.col_values(col_idx)
        ws.update_cell(len(col_values) + 1, col_idx, t)
    except: pass

def del_task(t, col_idx):
    try: 
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=col_idx)
        ws.update_cell(cell.row, col_idx, "") 
    except: pass

# --- XP & LOGIQUE MÉTIER ---
def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: st.error("Erreur Save")

def check_rent_paid(df):
    # Logique de renouvellement : On checke uniquement le mois courant (ex: "2023-10")
    try:
        current_month = datetime.now().strftime("%Y-%m")
        # Si on trouve "Loyer" avec la date du mois courant, c'est payé.
        # Le mois prochain, la date changera, donc ça retournera False -> Reset auto.
        rent_logs = df[df['Date'].str.contains(current_month, na=False) & df['Commentaire'].str.contains("Loyer", case=False, na=False)]
        return not rent_logs.empty
    except: return False

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100, 0, False
        
        # XP
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
        
        # MANA
        anki_logs = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
        if anki_logs.empty: mana = 50 
        else:
            last_anki = datetime.strptime(anki_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")
            days_anki = (datetime.now() - last_anki).days
            mana = max(0, 100 - (days_anki * 10))
        
        # CHAOS (3% par jour)
        admin_logs = df[df['Type'].str.contains("Gestion", case=False, na=False)]
        if admin_logs.empty: chaos = 20
        else:
            last_admin = datetime.strptime(admin_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")
            days_admin = (datetime.now() - last_admin).days
            chaos = min(100, days_admin * 3) 
            
        is_rent_paid = check_rent_paid(df)
            
        return xp, mana, chaos, is_rent_paid
    except: return 0, 50, 50, False

# --- DATA SPORT ---
FULL_BODY_PROGRAMS = {
    "FB1. STRENGTH": "SQUAT 3x5\nBENCH 3x5\nROWING 3x6\nRDL 3x8\nPLANK 3x1min",
    "FB2. HYPERTROPHY": "PRESSE 3x12\nTIRAGE 3x12\nCHEST PRESS 3x12\nLEG CURL 3x15\nELEVATIONS 3x15",
    "FB3. POWER": "CLEAN 5x3\nJUMP LUNGE 3x8\nPULLUPS 4xMAX\nDIPS 4xMAX\nSWING 3x20",
    "FB4. DUMBBELLS": "GOBLET SQUAT 4x10\nINCLINE PRESS 3x10\nROWING 3x12\nLUNGES 3x10\nARMS 3x12",
    "FB7. CIRCUIT": "THRUSTERS x10\nRENEGADE ROW x8\nCLIMBERS x20\nPUSHUPS xMAX\nJUMPS x15"
}

# --- LOGIQUE ---
total_xp, current_mana, current_chaos, rent_paid_status = get_stats()
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
    
    cm1, cm2 = st.columns(2)
    with cm1:
        st.caption(f"**MÉMOIRE : {current_mana}%**")
        st.markdown(f'<div class="mana-bar">', unsafe_allow_html=True)
        st.progress(current_mana / 100)
        st.markdown('</div>', unsafe_allow_html=True)
    with cm2:
        st.caption(f"**CHAOS : {current_chaos}%**")
        st.markdown(f'<div class="chaos-bar">', unsafe_allow_html=True)
        st.progress(current_chaos / 100)
        st.markdown('</div>', unsafe_allow_html=True)

st.write("---")

# === LAYOUT ===
col_left, col_right = st.columns([1, 2], gap="large")

# === GAUCHE : QUÊTES -> PUIS ADMIN ===
with col_left:
    
    # --- 1. QUÊTES DU JOUR (TO DO) ---
    st.markdown('<p class="section-header">📌 QUÊTES DU JOUR</p>', unsafe_allow_html=True)
    new_t = st.text_input("Tâche perso...", label_visibility="collapsed")
    if st.button("AJOUTER TÂCHE"):
        if new_t: add_task(new_t, 1); st.rerun()
    
    tasks = load_tasks(1) 
    for i, t in enumerate(tasks):
        c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
        with c1: st.text(t)
        with c2: 
            if st.button("✓", key=f"vp_{i}"):
                save_xp(5, "Gestion", t); del_task(t, 1); st.rerun()
        with c3:
            if st.button("×", key=f"xp_{i}"):
                del_task(t, 1); st.rerun()
    
    st.write("---") 

    # --- 2. CENTRE DE COMMANDEMENT (ADMIN) ---
    st.markdown('<p class="section-header">🛡️ CENTRE DE COMMANDEMENT (ADMIN)</p>', unsafe_allow_html=True)
    
    # A. GESTION DU LOYER (LE GROS MORCEAU)
    if rent_paid_status:
        st.markdown(f'<div class="rent-paid">✅ LOYER {datetime.now().strftime("%B").upper()} RÉGLÉ</div>', unsafe_allow_html=True)
        st.write("")
    else:
        # Calcul de l'urgence selon le jour du mois
        day = datetime.now().day
        rent_btn_label = "🏠 PAYER LOYER"
        rent_help = "Payer maintenant"
        
        if day >= 29:
            # MODE PANIQUE (FIN DE MOIS)
            st.markdown('<div class="critical-alert">⚠️ IL RESTE 2 JOURS ! PAYE LE LOYER ! ⚠️</div>', unsafe_allow_html=True)
            if st.button(rent_btn_label, type="primary"): # Bouton Rouge
                save_xp(50, "Gestion", "Loyer"); st.rerun()
                
        elif day >= 20:
            # MODE URGENCE (ROUGE)
            st.caption(f"📅 Nous sommes le {day}. **C'est urgent.**")
            if st.button(rent_btn_label, type="primary"): # Bouton Rouge
                save_xp(50, "Gestion", "Loyer"); st.rerun()
                
        elif day >= 10:
             # MODE ATTENTION (ORANGE - Simulée par texte car pas de btn orange natif)
            st.caption(f"📅 Nous sommes le {day}. Pense au loyer.")
            if st.button(rent_btn_label): # Bouton Normal
                save_xp(50, "Gestion", "Loyer"); st.rerun()
        else:
            # MODE ZEN (DÉBUT DE MOIS)
            st.caption(f"📅 Nous sommes le {day}. Tu as le temps.")
            if st.button(rent_btn_label):
                save_xp(50, "Gestion", "Loyer"); st.rerun()

    st.write("") 

    # B. MAILS & AGENDA (TRIÉ)
    st.markdown("##### 📨 COMMUNICATIONS")
    c_mail1, c_mail2, c_mail3 = st.columns(3)
    
    with c_mail1:
        if st.button("🧹 TRI RAPIDE", help="Supprimer les spams, archiver (-5% Chaos)"):
            save_xp(5, "Gestion", "Tri Mails"); st.rerun()
    with c_mail2:
        if st.button("✍️ RÉPONDRE", help="Ecrire les mails importants (-10% Chaos)"):
            save_xp(10, "Gestion", "Réponse Mails"); st.rerun()
    with c_mail3:
        if st.button("📅 AGENDA", help="Organiser la semaine (-5% Chaos)"):
            save_xp(5, "Gestion", "Agenda"); st.rerun()

    # C. FINANCES & PAPIERS
    st.markdown("##### 💸 FACTURES & PAPIERS")
    c_fac1, c_fac2 = st.columns([0.65, 0.35])
    with c_fac1:
        facture_name = st.text_input("Nom facture (ex: Salt)...", label_visibility="collapsed")
    with c_fac2:
        if st.button("PAYER"):
            if facture_name:
                save_xp(15, "Gestion", f"Facture: {facture_name}")
                st.toast(f"Payé : {facture_name}")
                time.sleep(1); st.rerun()
    
    if st.button("📞 APPELS / ADMINISTRATIF"):
        save_xp(10, "Gestion", "Appels/Admin"); st.rerun()


# === DROITE : SPORT & ETUDES ===
with col_right:
    
    # --- 01. ETUDES ---
    st.markdown('<p class="section-header">🧠 FORGE DU SAVOIR (ANKI)</p>', unsafe_allow_html=True)
    
    c_create, c_combat = st.columns(2, gap="medium")
    
    with c_create:
        st.caption("📜 **GRIMOIRE**")
        with st.expander("📥 IMPORTER"):
            uploaded_file = st.file_uploader("Un cours par ligne", type="txt")
            if uploaded_file and st.button("IMPORTER"):
                stringio = uploaded_file.getvalue().decode("utf-8")
                for line in stringio.splitlines():
                    if line.strip(): add_task(line.strip(), 2)
                st.rerun()
        
        new_anki = st.text_input("Nouveau cours...", label_visibility="collapsed", key="anki_input")
        if st.button("AJOUTER AU GRIMOIRE"):
            if new_anki: add_task(new_anki, 2); st.rerun()

        anki_tasks = load_tasks(2)
        if not anki_tasks: st.caption("_Grimoire vide._")
        else:
            for i, t in enumerate(anki_tasks):
                c1, c2 = st.columns([0.8, 0.2])
                c1.markdown(f"**{t}**")
                if c2.button("✓", key=f"va_{i}"):
                    save_xp(30, "Intellect", f"Création: {t}"); del_task(t, 2); st.rerun()

    with c_combat:
        st.caption("⚔️ **CHAMP DE BATAILLE**")
        if st.session_state['anki_start_time'] is None:
            st.write("") 
            st.markdown("Prêt à réviser ?")
            if st.button("⚔️ COMMENCER"):
                st.session_state['anki_start_time'] = datetime.now(); st.rerun()
        else:
            start_t = st.session_state['anki_start_time']
            placeholder = st.empty()
            
            if st.button("🏁 TERMINER"):
                end_t = datetime.now()
                duration = end_t - start_t
                minutes = int(duration.total_seconds() // 60)
                seconds = int(duration.total_seconds() % 60)
                xp_gain = max(1, minutes)
                if minutes >= 25: xp_gain += 5
                save_xp(xp_gain, "Intellect", f"Combat Anki ({minutes}m)"); st.session_state['anki_start_time'] = None; st.rerun()

            while True:
                delta = datetime.now() - start_t
                mm, ss = divmod(int(delta.total_seconds()), 60)
                placeholder.markdown(f'<div class="timer-display">{mm:02d}:{ss:02d}</div>', unsafe_allow_html=True)
                time.sleep(1)

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
