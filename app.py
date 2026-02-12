import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- CSS (STYLE V33 - CLEAN & FORMS) ---
st.markdown("""
    <style>
    /* Fond global */
    .stApp { background-color: #f4f6f9; color: #333; }
    
    /* FIX TOP PADDING */
    .block-container { padding-top: 1.2rem !important; }

    /* === HEADER HUD === */
    .hud-box {
        background-color: white; padding: 20px; border-radius: 12px;
        border-bottom: 3px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 30px; margin-top: -0.5rem;
    }

    /* === BARRES === */
    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    /* === UI & BOUTONS STANDARDS + FORMS === */
    .section-header {
        font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444;
        border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px;
    }
    
    /* Style uniforme pour stButton et stFormSubmitButton */
    .stButton>button, .stFormSubmitButton>button {
        width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px;
        background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em; transition: all 0.2s;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover { 
        border-color: #333; background-color: #333; color: white; transform: translateY(-1px); 
    }
    
    .timer-box {
        font-family: 'Courier New', monospace; font-size: 2.2em; font-weight: bold;
        color: #d9534f; text-align: center; background-color: #fff; border: 2px solid #d9534f; border-radius: 8px; padding: 15px; margin: 10px 0;
    }

    /* === BOUTONS CUSTOM === */
    .comm-btn > div > div > button { height: 45px !important; font-size: 0.8em !important; }

    /* Bouton Annuler Sobre */
    .sober-marker + div > button {
         background-color: transparent !important; color: #888 !important; border: 1px solid #ccc !important;
         font-size: 0.7em !important; height: 28px !important; min-height: 28px !important; text-transform: none !important;
         padding: 0px !important; width: auto !important; margin-top: 5px;
    }
    .sober-marker + div > button:hover { color: #333 !important; border-color: #888 !important; }

    /* Boutons Urgents (Rouge) */
    @keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }
    .urgent-marker + div > button {
        background: linear-gradient(135deg, #d9534f, #c9302c) !important; color: white !important; border: none !important;
        font-weight: 900 !important; letter-spacing: 1px !important; font-size: 1em !important;
        animation: pulse-red 1.5s infinite !important; height: 55px !important;
    }
    /* Boutons Warning (Orange) */
    .warning-marker + div > button {
        background: linear-gradient(135deg, #f0ad4e, #ec971f) !important; color: white !important; border: none !important;
        font-weight: 800 !important; height: 48px !important;
    }

    /* Bannière Payé (Or) */
    .gold-banner {
        background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7);
        color: #5c4004; padding: 15px; text-align: center; border-radius: 8px;
        font-weight: 900; text-transform: uppercase; letter-spacing: 2px;
        border: 2px solid #d4af37; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-shadow: 1px 1px 0px rgba(255,255,255,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION BARRE ---
def draw_bar(label, value, color_class, max_val=100):
    pct = min(100, max(0, (value / max_val) * 100))
    st.markdown(f"""
    <div class="bar-label"><span>{label}</span><span>{int(value)}%</span></div>
    <div class="bar-container"><div class="bar-fill {color_class}" style="width: {pct}%;"></div></div>
    """, unsafe_allow_html=True)

# --- MOIS ---
MOIS_FR = {1: "JANVIER", 2: "FÉVRIER", 3: "MARS", 4: "AVRIL", 5: "MAI", 6: "JUIN",
           7: "JUILLET", 8: "AOÛT", 9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DÉCEMBRE"}

# --- INIT ---
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
    try: return [x for x in get_db().worksheet("Tasks").col_values(col_idx)[1:] if x.strip() != ""] 
    except: return []

def add_task(t, col_idx): 
    try: 
        ws = get_db().worksheet("Tasks"); col_values = ws.col_values(col_idx)
        ws.update_cell(len(col_values) + 1, col_idx, t)
    except: pass

def del_task(t, col_idx):
    try: ws = get_db().worksheet("Tasks"); cell = ws.find(t, in_column=col_idx); ws.update_cell(cell.row, col_idx, "") 
    except: pass

# --- LOGIQUE METIER ---
def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: st.error("Erreur Save")

def undo_payment(keyword):
    try:
        ws = get_db().worksheet("Data")
        current_month = datetime.now().strftime("%Y-%m")
        df = pd.DataFrame(ws.get_all_records())
        mask = df['Date'].astype(str).str.contains(current_month) & df['Commentaire'].astype(str).str.contains(keyword)
        if mask.any():
            ws.delete_rows(int(df[mask].index[-1] + 2))
            st.toast("Annulé.")
            return True
    except: pass
    return False

def check_paid(df, keyword):
    try:
        current_month = datetime.now().strftime("%Y-%m")
        logs = df[df['Date'].str.contains(current_month, na=False) & df['Commentaire'].str.contains(keyword, case=False, na=False)]
        return not logs.empty
    except: return False

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100, 0, False, False
        
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
        
        anki_logs = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
        if anki_logs.empty: mana = 50 
        else:
            last_anki = datetime.strptime(anki_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")
            days_anki = (datetime.now() - last_anki).days
            mana = max(0, 100 - (days_anki * 10))
        
        admin_logs = df[df['Type'].str.contains("Gestion", case=False, na=False)]
        if admin_logs.empty: chaos = 20
        else:
            last_admin = datetime.strptime(admin_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")
            days_admin = (datetime.now() - last_admin).days
            chaos = min(100, days_admin * 3) 
            
        is_rent_paid = check_paid(df, "Loyer")
        is_salt_paid = check_paid(df, "Facture: Salt")
        
        return xp, mana, chaos, is_rent_paid, is_salt_paid
    except: return 0, 50, 50, False, False

# --- SPORT DATA ---
FULL_BODY_PROGRAMS = {
    "FB1. STRENGTH": "SQUAT 3x5\nBENCH 3x5\nROWING 3x6\nRDL 3x8\nPLANK 3x1min",
    "FB2. HYPERTROPHY": "PRESSE 3x12\nTIRAGE 3x12\nCHEST PRESS 3x12\nLEG CURL 3x15\nELEVATIONS 3x15",
    "FB3. POWER": "CLEAN 5x3\nJUMP LUNGE 3x8\nPULLUPS 4xMAX\nDIPS 4xMAX\nSWING 3x20",
    "FB4. DUMBBELLS": "GOBLET SQUAT 4x10\nINCLINE PRESS 3x10\nROWING 3x12\nLUNGES 3x10\nARMS 3x12",
    "FB7. CIRCUIT": "THRUSTERS x10\nRENEGADE ROW x8\nCLIMBERS x20\nPUSHUPS xMAX\nJUMPS x15"
}

# --- CALCULS INITIAUX ---
total_xp, current_mana, current_chaos, rent_paid_status, salt_paid_status = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
xp_needed = 100 - progress_pct
current_month_name = MOIS_FR[datetime.now().month]

# ==============================================================================
# HUD HEADER (CORRECTIF : 2 COLONNES HAUT, 3 COLONNES BAS)
# ==============================================================================
st.markdown('<div class="hud-box">', unsafe_allow_html=True)

# Ligne 1 : Avatar et Titre (2 colonnes seulement !)
c_av, c_main = st.columns([0.1, 0.9])
with c_av: st.image("avatar.png", width=80)
with c_main:
    st.markdown(f"<h2 style='margin:0; border:none;'>NIVEAU {niveau} | SELECTA</h2>", unsafe_allow_html=True)
    st.caption(f"{xp_needed} XP requis pour le niveau suivant")

st.write("") 

# Ligne 2 : Les Barres (3 colonnes)
c_bar1, c_bar2, c_bar3 = st.columns(3, gap="medium")
with c_bar1: draw_bar("EXPÉRIENCE", progress_pct, "xp-fill")
with c_bar2: draw_bar("MÉMOIRE (MANA)", current_mana, "mana-fill")
with c_bar3: draw_bar("CHAOS (ADMIN)", current_chaos, "chaos-fill")

st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# CORPS DE PAGE
# ==============================================================================
col_left, col_right = st.columns([1, 1.2], gap="large")

# === GAUCHE ===
with col_left:
    # 1. QUÊTES (FORMULAIRE POUR NETTOYER L'INPUT)
    st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
    with st.form("task_form", clear_on_submit=True):
        new_t = st.text_input("Ajouter une tâche...", label_visibility="collapsed")
        submitted = st.form_submit_button("AJOUTER TÂCHE")
        if submitted and new_t:
            add_task(new_t, 1)
            st.rerun()
    
    tasks = load_tasks(1) 
    for i, t in enumerate(tasks):
        c1, c2, c3 = st.columns([0.75, 0.12, 0.13])
        with c1: st.write(f"• {t}")
        with c2: 
            if st.button("✓", key=f"vp_{i}"): save_xp(5, "Gestion", t); del_task(t, 1); st.rerun()
        with c3:
            if st.button("×", key=f"xp_{i}"): del_task(t, 1); st.rerun()
    
    st.write("")
    
    # 2. GESTION DU ROYAUME
    st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)

    # A. LOYER
    st.markdown("**LOYER**")
    if rent_paid_status:
        st.markdown(f'<div class="gold-banner">✨ LOYER {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
        st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
        if st.button("↺ Annuler", key="undo_rent"): undo_payment("Loyer"); st.rerun()
    else:
        day = datetime.now().day
        if day >= 29:
            st.markdown('<span class="urgent-marker"></span>', unsafe_allow_html=True)
            if st.button(f"⚠️ PAYER LOYER {current_month_name} !", key="rent_btn"): save_xp(50, "Gestion", "Loyer"); st.rerun()
        elif day >= 20:
            st.markdown('<span class="warning-marker"></span>', unsafe_allow_html=True)
            if st.button(f"RAPPEL : LOYER {current_month_name}", key="rent_btn"): save_xp(50, "Gestion", "Loyer"); st.rerun()
        else:
            if st.button(f"PAYER LOYER {current_month_name} (EN ATTENTE)", key="rent_btn"): save_xp(50, "Gestion", "Loyer"); st.rerun()

    st.write("")

    # B. SALT
    st.markdown("**SALT (INTERNET/TV)**")
    if salt_paid_status:
        st.markdown(f'<div class="gold-banner">✨ SALT {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
        st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
        if st.button("↺ Annuler", key="undo_salt"): undo_payment("Facture: Salt"); st.rerun()
    else:
        day = datetime.now().day
        if day >= 29:
            st.markdown('<span class="urgent-marker"></span>', unsafe_allow_html=True)
            if st.button(f"⚠️ PAYER SALT {current_month_name} !", key="salt_btn"): save_xp(25, "Gestion", "Facture: Salt"); st.rerun()
        elif day >= 20:
            st.markdown('<span class="warning-marker"></span>', unsafe_allow_html=True)
            if st.button(f"RAPPEL : SALT {current_month_name}", key="salt_btn"): save_xp(25, "Gestion", "Facture: Salt"); st.rerun()
        else:
            if st.button(f"PAYER SALT {current_month_name} (EN ATTENTE)", key="salt_btn"): save_xp(25, "Gestion", "Facture: Salt"); st.rerun()


    st.write("")

    # C. COMMUNICATIONS
    st.markdown("**COMMUNICATIONS**")
    c_mail1, c_mail2, c_mail3 = st.columns(3)
    with c_mail1:
        st.markdown('<div class="comm-btn">', unsafe_allow_html=True)
        if st.button("🧹 TRIER"): save_xp(5, "Gestion", "Tri Mails"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_mail2:
        st.markdown('<div class="comm-btn">', unsafe_allow_html=True)
        if st.button("✍️ RÉPONDRE"): save_xp(10, "Gestion", "Reponse Mails"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_mail3:
        st.markdown('<div class="comm-btn">', unsafe_allow_html=True)
        if st.button("📅 AGENDA"): save_xp(5, "Gestion", "Agenda"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    # D. AUTRES FACTURES (FORMULAIRE)
    st.markdown("**AUTRES FACTURES**")
    with st.form("bills_form", clear_on_submit=True):
        c_fac1, c_fac2 = st.columns([0.7, 0.3])
        with c_fac1: facture_name = st.text_input("Nom facture...", label_visibility="collapsed")
        with c_fac2: 
            if st.form_submit_button("PAYER") and facture_name:
                save_xp(15, "Gestion", f"Facture: {facture_name}")
                st.toast("Payé !"); time.sleep(1); st.rerun()

# === DROITE ===
with col_right:
    # 3. ETUDES
    st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
    c_create, c_combat = st.columns(2, gap="medium")
    with c_create:
        st.caption("📜 **GRIMOIRE**")
        with st.expander("📥 IMPORTER TXT"):
            uploaded_file = st.file_uploader("Fichier", type="txt")
            if uploaded_file and st.button("IMPORTER"):
                for l in uploaded_file.getvalue().decode("utf-8").splitlines():
                    if l.strip(): add_task(l.strip(), 2)
                st.rerun()
        
        # Formulaire cours
        with st.form("anki_form", clear_on_submit=True):
            new_anki = st.text_input("Ajouter cours...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER") and new_anki:
                add_task(new_anki, 2); st.rerun()

        anki_tasks = load_tasks(2)
        if not anki_tasks: st.caption("_Grimoire vide._")
        else:
            for i, t in enumerate(anki_tasks):
                c1, c2 = st.columns([0.85, 0.15])
                c1.markdown(f"**{t}**")
                if c2.button("✓", key=f"va_{i}"): save_xp(30, "Intellect", f"Création: {t}"); del_task(t, 2); st.rerun()

    with c_combat:
        st.caption("⚔️ **COMBAT (ANKI)**")
        if st.session_state['anki_start_time'] is None:
            st.write("Prêt à réviser ?")
            if st.button("⚔️ LANCER LE COMBAT", type="primary"): st.session_state['anki_start_time'] = datetime.now(); st.rerun()
        else:
            start_t = st.session_state['anki_start_time']
            placeholder = st.empty()
            if st.button("🏁 TERMINER SESSION"):
                duration = datetime.now() - start_t
                mins = int(duration.total_seconds() // 60)
                xp = max(1, mins) + (5 if mins >= 25 else 0)
                save_xp(xp, "Intellect", f"Combat Anki ({mins}m)"); st.session_state['anki_start_time'] = None; st.rerun()
            while True:
                mm, ss = divmod(int((datetime.now() - start_t).total_seconds()), 60)
                placeholder.markdown(f'<div class="timer-box">{mm:02d}:{ss:02d}</div>', unsafe_allow_html=True)
                time.sleep(1)

    st.write("")
    st.write("")

    # 4. SPORT
    st.markdown('<div class="section-header">⚡ ENTRAÎNEMENT</div>', unsafe_allow_html=True)
    c_home, c_gym = st.columns(2, gap="medium")
    with c_home:
        st.markdown("**🏠 MAISON**")
        if st.button("⏱️ TIMER 20 MIN"):
            ph = st.empty()
            for s in range(1200, -1, -1):
                m, sec = divmod(s, 60)
                ph.markdown(f'<div class="timer-box">{m:02d}:{sec:02d}</div>', unsafe_allow_html=True)
                time.sleep(1)
        if st.button("VALIDER MAISON (+20 XP)"): save_xp(20, "Force", "Maison"); st.rerun()
    with c_gym:
        st.markdown("**🏋️ SALLE**")
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
