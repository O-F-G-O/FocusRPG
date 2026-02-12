import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- CSS (CORRECTIFS V29 - ALIGNEMENT & BOUTONS CUSTOM) ---
st.markdown("""
    <style>
    /* Fond global */
    .stApp { background-color: #f4f6f9; color: #333; }
    /* Supprimer marge haut */
    .block-container { padding-top: 1rem !important; }

    /* === HEADER HUD ALIGNÉ === */
    /* On s'assure que les éléments du header sont centrés verticalement */
    [data-testid="stHorizontalBlock"] > div {
        display: flex;
        align-items: center;
    }
    h2 { margin-bottom: 0px !important; } /* Remonte le titre */
    .stCaption { margin-top: 0px !important; margin-bottom: 5px !important; }

    /* === BARRES PROGRESSION CUSTOM === */
    .bar-container {
        background-color: #e0e0e0; border-radius: 10px;
        width: 100%; height: 18px; /* Un peu plus fin pour l'élégance */
        margin-top: 2px; margin-bottom: 8px;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.2); overflow: hidden;
    }
    .bar-fill {
        height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out;
        display: flex; align-items: center; justify-content: flex-end;
        padding-right: 5px; color: white; font-size: 0.7em; font-weight: bold;
    }
    .xp-fill { background-color: #8A2BE2; }
    .mana-fill { background-color: #0056b3; }
    .chaos-fill { background-color: #800000; }

    /* === UI GÉNÉRALE === */
    .section-header {
        font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444;
        border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px;
    }
    /* Boutons standards */
    .stButton>button {
        width: 100%; min-height: 42px; /* Hauteur forcée pour uniformité */
        border: 1px solid #bbb; border-radius: 6px;
        background-color: white; color: #333;
        font-weight: 600; text-transform: uppercase; font-size: 0.85em;
        transition: all 0.2s;
    }
    .stButton>button:hover { 
        border-color: #333; background-color: #333; color: white; transform: translateY(-1px);
    }
    .timer-box {
        font-family: 'Courier New', monospace; font-size: 2.2em; font-weight: bold;
        color: #d9534f; text-align: center; 
        background-color: #fff; border: 2px solid #d9534f; border-radius: 8px;
        padding: 15px; margin: 10px 0;
    }

    /* === BOUTONS CUSTOM (RENT & SOBER) === */
    /* Technique : on cible le bouton qui suit un span invisible spécifique */
    
    /* 1. Bouton URGENT (Rouge pulse) */
    @keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }
    .urgent-marker + div > button {
        background: linear-gradient(135deg, #d9534f, #c9302c) !important;
        color: white !important; border: 2px solid #a94442 !important;
        font-weight: 900 !important; letter-spacing: 1px !important; font-size: 1em !important;
        animation: pulse-red 1.5s infinite !important; height: 50px !important;
    }
    
    /* 2. Bouton WARNING (Orange) */
    .warning-marker + div > button {
        background: linear-gradient(135deg, #f0ad4e, #ec971f) !important;
        color: white !important; border: 2px solid #d58512 !important;
        font-weight: 800 !important; font-size: 0.95em !important; height: 45px !important;
    }
    
    /* 3. Bouton SOBRE (Annuler gris petit) */
    .sober-marker + div > button {
         background-color: transparent !important; color: #999 !important;
         border: 1px solid #ddd !important; font-size: 0.75em !important; 
         height: 30px !important; min-height: 30px !important; 
         margin-top: -10px !important; /* Remonte un peu */
    }
    .sober-marker + div > button:hover {
         background-color: #eee !important; color: #333 !important; border-color: #aaa !important;
    }

    /* Bannière Loyer Payé (Non cliquable) */
    .rent-gold-banner {
        background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7);
        color: #5c4004; padding: 15px; text-align: center; border-radius: 8px;
        font-weight: 900; text-transform: uppercase; letter-spacing: 2px;
        border: 2px solid #d4af37; box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        text-shadow: 1px 1px 0px rgba(255,255,255,0.2); margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION HTML PROGRESS BAR ---
def draw_bar(label, value, color_class, max_val=100):
    pct = min(100, max(0, (value / max_val) * 100))
    st.markdown(f"""
    <div style="margin-bottom: 2px; font-weight:bold; font-size:0.8em; color:#555;">
        {label} <span style="float:right;">{int(value)}%</span>
    </div>
    <div class="bar-container">
        <div class="bar-fill {color_class}" style="width: {pct}%;"></div>
    </div>
    """, unsafe_allow_html=True)

# --- TRADUCTION MOIS ---
MOIS_FR = {1: "JANVIER", 2: "FÉVRIER", 3: "MARS", 4: "AVRIL", 5: "MAI", 6: "JUIN",
           7: "JUILLET", 8: "AOÛT", 9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DÉCEMBRE"}

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

# --- LOGIQUE METIER ---
def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: st.error("Erreur Save")

def undo_rent_payment():
    try:
        ws = get_db().worksheet("Data")
        current_month = datetime.now().strftime("%Y-%m")
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        mask = df['Date'].astype(str).str.contains(current_month) & df['Commentaire'].astype(str).str.contains("Loyer")
        if mask.any():
            idx_to_drop = df[mask].index[-1]
            ws.delete_rows(int(idx_to_drop + 2))
            st.toast("Annulé.")
            return True
    except: pass
    return False

def check_rent_paid(df):
    try:
        current_month = datetime.now().strftime("%Y-%m")
        rent_logs = df[df['Date'].str.contains(current_month, na=False) & df['Commentaire'].str.contains("Loyer", case=False, na=False)]
        return not rent_logs.empty
    except: return False

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100, 0, False
        
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
current_month_name = MOIS_FR[datetime.now().month]

# ==============================================================================
# HEADER (HUD) ALIGNÉ
# ==============================================================================
c_av, c_main, c_sec = st.columns([0.12, 0.58, 0.3]) # Ratios ajustés pour l'alignement

with c_av:
    st.image("avatar.png", use_container_width=True)

with c_main:
    st.markdown(f"<h2 style='margin:0; padding:0;'>NIVEAU {niveau} | SELECTA</h2>", unsafe_allow_html=True)
    st.caption(f"{xp_needed} XP requis pour le niveau suivant")
    draw_bar("EXPÉRIENCE", progress_pct, "xp-fill")

with c_sec:
    # L'alignement vertical est géré par le CSS flexbox sur les colonnes
    draw_bar("MÉMOIRE (MANA)", current_mana, "mana-fill")
    draw_bar("CHAOS (ADMIN)", current_chaos, "chaos-fill")

st.write("---")


# ==============================================================================
# CORPS DE PAGE (2 Colonnes)
# ==============================================================================
col_left, col_right = st.columns([1, 1.2], gap="large")

# === COLONNE GAUCHE : QUÊTES & GOUVERNANCE ===
with col_left:
    
    # 1. QUÊTES DU JOUR
    st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
    new_t = st.text_input("Ajouter une tâche...", label_visibility="collapsed")
    if st.button("AJOUTER TÂCHE", key="add_t"):
        if new_t: add_task(new_t, 1); st.rerun()
    
    tasks = load_tasks(1) 
    for i, t in enumerate(tasks):
        c1, c2, c3 = st.columns([0.75, 0.12, 0.13])
        with c1: st.write(f"• {t}")
        with c2: 
            if st.button("✓", key=f"vp_{i}"):
                save_xp(5, "Gestion", t); del_task(t, 1); st.rerun()
        with c3:
            if st.button("×", key=f"xp_{i}"):
                del_task(t, 1); st.rerun()
    
    st.write("")
    
    # 2. GESTION DU ROYAUME
    st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)

    # A. LOYER (BOUTONS CUSTOMISÉS)
    st.markdown("**LOYER**")
    if rent_paid_status:
        st.markdown(f'<div class="rent-gold-banner">✨ LOYER {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
        # Marqueur pour bouton sobre
        st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
        if st.button("annuler paiement (erreur)", key="undo_rent"):
             undo_rent_payment(); st.rerun()
    else:
        day = datetime.now().day
        if day >= 29:
            # Marqueur Urgent (Rouge Pulse)
            st.markdown('<span class="urgent-marker"></span>', unsafe_allow_html=True)
            if st.button(f"⚠️ PAYER LOYER {current_month_name} !", key="rent_btn"): 
                save_xp(50, "Gestion", "Loyer"); st.rerun()
        elif day >= 20:
            # Marqueur Warning (Orange)
            st.markdown('<span class="warning-marker"></span>', unsafe_allow_html=True)
            if st.button(f"RAPPEL : LOYER {current_month_name}", key="rent_btn"):
                save_xp(50, "Gestion", "Loyer"); st.rerun()
        else:
            # Bouton Normal (Gris par défaut)
            if st.button(f"PAYER LOYER {current_month_name} (EN ATTENTE)", key="rent_btn"):
                save_xp(50, "Gestion", "Loyer"); st.rerun()

    st.write("")

    # B. COMMUNICATIONS (TAILLE UNIFORME VIA CSS)
    st.markdown("**COMMUNICATIONS**")
    c_mail1, c_mail2, c_mail3 = st.columns(3)
    with c_mail1:
        if st.button("🧹 TRIER"): save_xp(5, "Gestion", "Tri Mails"); st.rerun()
    with c_mail2:
        if st.button("✍️ REPONDRE"): save_xp(10, "Gestion", "Reponse Mails"); st.rerun()
    with c_mail3:
        if st.button("📅 AGENDA"): save_xp(5, "Gestion", "Agenda"); st.rerun()

    st.write("")

    # C. FACTURES
    st.markdown("**FACTURES**")
    c_fac1, c_fac2 = st.columns([0.7, 0.3])
    with c_fac1:
        facture_name = st.text_input("Nom facture...", label_visibility="collapsed")
    with c_fac2:
        if st.button("PAYER", key="pay_btn"):
            if facture_name:
                save_xp(15, "Gestion", f"Facture: {facture_name}"); st.toast("Payé !"); time.sleep(1); st.rerun()


# === COLONNE DROITE : ETUDES & SPORT ===
with col_right:
    
    # 3. ETUDES
    st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
    
    c_create, c_combat = st.columns(2, gap="medium")
    
    with c_create:
        st.caption("📜 **GRIMOIRE (COURS)**")
        with st.expander("📥 IMPORTER TXT"):
            uploaded_file = st.file_uploader("Un cours par ligne", type="txt")
            if uploaded_file and st.button("IMPORTER"):
                stringio = uploaded_file.getvalue().decode("utf-8")
                for line in stringio.splitlines():
                    if line.strip(): add_task(line.strip(), 2)
                st.rerun()
        
        c_in, c_btn = st.columns([0.7, 0.3])
        with c_in: new_anki = st.text_input("Ajouter cours...", label_visibility="collapsed")
        with c_btn: 
            if st.button("AJOUTER", key="add_anki"):
                if new_anki: add_task(new_anki, 2); st.rerun()

        anki_tasks = load_tasks(2)
        if not anki_tasks: st.caption("_Grimoire vide._")
        else:
            for i, t in enumerate(anki_tasks):
                c1, c2 = st.columns([0.85, 0.15])
                c1.markdown(f"**{t}**")
                if c2.button("✓", key=f"va_{i}"):
                    save_xp(30, "Intellect", f"Création: {t}"); del_task(t, 2); st.rerun()

    with c_combat:
        st.caption("⚔️ **COMBAT (ANKI)**")
        if st.session_state['anki_start_time'] is None:
            # Plus de st.info ici, juste du texte
            st.write("Prêt à réviser ?")
            if st.button("⚔️ LANCER LE COMBAT", type="primary"):
                st.session_state['anki_start_time'] = datetime.now(); st.rerun()
        else:
            start_t = st.session_state['anki_start_time']
            placeholder = st.empty()
            
            if st.button("🏁 TERMINER SESSION"):
                end_t = datetime.now()
                duration = end_t - start_t
                minutes = int(duration.total_seconds() // 60)
                xp_gain = max(1, minutes)
                if minutes >= 25: xp_gain += 5
                save_xp(xp_gain, "Intellect", f"Combat Anki ({minutes}m)"); st.session_state['anki_start_time'] = None; st.rerun()

            while True:
                delta = datetime.now() - start_t
                mm, ss = divmod(int(delta.total_seconds()), 60)
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
            # Plus de st.info ici, markdown simple
            st.markdown(f"**{n}**")
            for l in d.split('\n'): st.markdown(f"- {l}")
            
            if st.button("VALIDER SALLE (+50 XP)"):
                save_xp(50, "Force", n); st.session_state['gym_current_prog']=None; st.rerun()
