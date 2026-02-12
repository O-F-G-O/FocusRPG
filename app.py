import streamlit as st
import pandas as pd
import gspread
import time
import random
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

# --- INIT SESSION STATE (NAVIGATION) ---
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Dashboard"

# --- SCRIPT ANTI-AUTOCOMPLETE ---
components.html(
    """<script>
    const inputs = window.parent.document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => { input.setAttribute('autocomplete', 'off'); });
    </script>""", height=0
)

# --- CSS (V36 - NAVIGATION & PAGES) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; color: #333; }
    .block-container { padding-top: 1.2rem !important; }

    /* === HUD === */
    .hud-box {
        background-color: white; padding: 20px; border-radius: 12px;
        border-bottom: 3px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 30px; margin-top: -0.5rem;
    }
    
    /* === NAVIGATION ICONS === */
    .nav-btn-container { display: flex; gap: 10px; align-items: center; }

    /* === BARRES === */
    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    /* === DESIGN PAGES === */
    .history-card {
        background: white; padding: 10px 15px; border-radius: 8px;
        border-left: 5px solid #6f42c1; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .achievement-card {
        background: linear-gradient(135deg, #ffffff, #f9f9f9);
        padding: 20px; border-radius: 12px; border: 1px solid #FFD700;
        text-align: center; margin-bottom: 15px;
    }
    .section-header {
        font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444;
        border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px;
    }

    /* === BUTTONS === */
    .stButton>button {
        width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px;
        background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em;
    }
    .stButton>button:hover { border-color: #333; background-color: #333; color: white; }
    
    /* Loyer / Salt / Gold */
    .gold-banner {
        background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7);
        color: #5c4004; padding: 15px; text-align: center; border-radius: 8px;
        font-weight: 900; text-transform: uppercase; letter-spacing: 2px;
        border: 2px solid #d4af37; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- G-SHEETS ENGINE ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(secrets, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_url(secrets["spreadsheet"])

def load_tasks(col_idx):
    try: return [x for x in get_db().worksheet("Tasks").col_values(col_idx)[1:] if x.strip() != ""] 
    except: return []

def add_task(t, col_idx):
    try: ws = get_db().worksheet("Tasks"); ws.update_cell(len(ws.col_values(col_idx)) + 1, col_idx, t)
    except: pass

def del_task(t, col_idx):
    try: ws = get_db().worksheet("Tasks"); ws.update_cell(ws.find(t, in_column=col_idx).row, col_idx, "")
    except: pass

def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: st.error("Erreur GSheets")

def get_full_data():
    try: return pd.DataFrame(get_db().worksheet("Data").get_all_records())
    except: return pd.DataFrame()

def get_stats(df):
    if df.empty: return 0, 100, 0, False, False
    xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
    
    anki_logs = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
    mana = 100 if anki_logs.empty else max(0, 100 - ((datetime.now() - datetime.strptime(anki_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 10))
    
    admin_logs = df[df['Type'].str.contains("Gestion", case=False, na=False)]
    chaos = 0 if admin_logs.empty else min(100, (datetime.now() - datetime.strptime(admin_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 3)
    
    current_m = datetime.now().strftime("%Y-%m")
    rent = not df[df['Date'].str.contains(current_m) & df['Commentaire'].str.contains("Loyer")].empty
    salt = not df[df['Date'].str.contains(current_m) & df['Commentaire'].str.contains("Salt")].empty
    return xp, mana, chaos, rent, salt

# --- DATA & LOGIQUE ---
df_data = get_full_data()
total_xp, current_mana, current_chaos, rent_paid, salt_paid = get_stats(df_data)
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
current_month_name = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"][datetime.now().month-1]

# ==============================================================================
# NAVIGATION HUD
# ==============================================================================
st.markdown('<div class="hud-box">', unsafe_allow_html=True)
c_av, c_main, c_nav = st.columns([0.1, 0.65, 0.25])

with c_av: st.image("avatar.png", width=80)
with c_main:
    st.markdown(f"<h2 style='margin:0; border:none;'>NIV. {niveau} | SELECTA</h2>", unsafe_allow_html=True)
    st.caption(f"{100 - progress_pct} XP avant le niveau {niveau+1}")

with c_nav:
    st.write("")
    nc1, nc2, nc3, nc4 = st.columns(4)
    if nc1.button("🏰", help="Histoire"): st.session_state['current_page'] = "Histoire"; st.rerun()
    if nc2.button("🏆", help="Hauts Faits"): st.session_state['current_page'] = "HautsFaits"; st.rerun()
    if nc3.button("⚔️", help="Donjon"): st.session_state['current_page'] = "Donjon"; st.rerun()
    if nc4.button("🏠", help="Dashboard"): st.session_state['current_page'] = "Dashboard"; st.rerun()

st.write("")
c_bar1, c_bar2, c_bar3 = st.columns(3, gap="medium")
def draw_bar(l, v, c):
    st.markdown(f'<div class="bar-label"><span>{l}</span><span>{int(v)}%</span></div><div class="bar-container"><div class="bar-fill {c}" style="width:{v}%"></div></div>', unsafe_allow_html=True)

with c_bar1: draw_bar("EXPÉRIENCE", progress_pct, "xp-fill")
with c_bar2: draw_bar("MÉMOIRE", current_mana, "mana-fill")
with c_bar3: draw_bar("CHAOS", current_chaos, "chaos-fill")
st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# PAGE : DASHBOARD
# ==============================================================================
if st.session_state['current_page'] == "Dashboard":
    col_left, col_right = st.columns([1, 1.2], gap="large")
    with col_left:
        st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
        with st.form("task_f", clear_on_submit=True):
            nt = st.text_input("Ajouter tâche...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER"): add_task(nt, 1); st.rerun()
        for i, t in enumerate(load_tasks(1)):
            cl1, cl2, cl3 = st.columns([0.75, 0.12, 0.13])
            cl1.write(f"• {t}")
            if cl2.button("✓", key=f"q_{i}"): save_xp(5, "Gestion", t); del_task(t, 1); st.rerun()
            if cl3.button("×", key=f"d_{i}"): del_task(t, 1); st.rerun()

        st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)
        def draw_rent(paid, name, xp_v, key_b):
            if paid: st.markdown(f'<div class="gold-banner">✨ {name} {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
            else:
                if st.button(f"🏠 PAYER {name} {current_month_name}", key=key_b): save_xp(xp_v, "Gestion", f"Loyer {name}"); st.rerun()

        draw_rent(rent_paid, "LOYER", 50, "rb")
        st.write("")
        draw_rent(salt_paid, "SALT", 25, "sb")
        
        st.write("")
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1: 
            if st.button("🧹 TRIER"): save_xp(5, "Gestion", "Tri Mails"); st.rerun()
        with c_m2:
            if st.button("✍️ RÉPONDRE"): save_xp(10, "Gestion", "Reponse Mails"); st.rerun()
        with c_m3:
            if st.button("📅 AGENDA"): save_xp(5, "Gestion", "Agenda"); st.rerun()

    with col_right:
        st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            st.caption("📜 **GRIMOIRE**")
            with st.form("anki_f", clear_on_submit=True):
                na = st.text_input("Cours...", label_visibility="collapsed")
                if st.form_submit_button("AJOUTER"): add_task(na, 2); st.rerun()
            for i, t in enumerate(load_tasks(2)):
                cl1, cl2 = st.columns([0.8, 0.2])
                cl1.write(f"**{t}**")
                if cl2.button("✓", key=f"a_{i}"): save_xp(30, "Intellect", f"Création: {t}"); del_task(t, 2); st.rerun()
        with cc2:
            st.caption("⚔️ **COMBAT (ANKI)**")
            if 'anki_start_time' not in st.session_state or st.session_state['anki_start_time'] is None:
                if st.button("⚔️ LANCER COMBAT", type="primary"): st.session_state['anki_start_time'] = datetime.now(); st.rerun()
            else:
                st.write("En combat...")
                if st.button("🏁 TERMINER"):
                    mins = int((datetime.now() - st.session_state['anki_start_time']).total_seconds() // 60)
                    save_xp(max(1, mins), "Intellect", "Combat Anki"); st.session_state['anki_start_time'] = None; st.rerun()

        st.markdown('<div class="section-header">⚡ ENTRAÎNEMENT</div>', unsafe_allow_html=True)
        cs1, cs2 = st.columns(2)
        with cs1:
            if st.button("🏠 MAISON (+20 XP)"): save_xp(20, "Force", "Maison"); st.rerun()
        with cs2:
            if st.button("🏋️ SALLE (+50 XP)"): save_xp(50, "Force", "Salle"); st.rerun()

# ==============================================================================
# PAGE : HISTOIRE (📜 Journal de bord)
# ==============================================================================
elif st.session_state['current_page'] == "Histoire":
    st.markdown('<div class="section-header">📜 LE JOURNAL DE L\'HISTOIRE</div>', unsafe_allow_html=True)
    if df_data.empty: st.write("Aucune archive trouvée.")
    else:
        for _, row in df_data.iloc[::-1].head(20).iterrows():
            st.markdown(f"""<div class="history-card"><b>{row['Date']}</b> | {row['Type']} | <b>+{row['XP']} XP</b><br><small>{row['Commentaire']}</small></div>""", unsafe_allow_html=True)

# ==============================================================================
# PAGE : HAUTS FAITS (🏆 Achievements)
# ==============================================================================
elif st.session_state['current_page'] == "HautsFaits":
    st.markdown('<div class="section-header">🏆 SALLE DES HAUTS FAITS</div>', unsafe_allow_html=True)
    ha1, ha2, ha3 = st.columns(3)
    
    with ha1:
        st.markdown('<div class="achievement-card">🎖️<br><b>PREMIER PAS</b><br><small>Atteindre le Niv. 2</small></div>', unsafe_allow_html=True) if niveau >= 2 else st.write("")
    with ha2:
        st.markdown('<div class="achievement-card">💰<br><b>INTENDANT</b><br><small>Payer son premier loyer</small></div>', unsafe_allow_html=True) if not df_data[df_data['Commentaire'].str.contains("Loyer")].empty else st.write("")
    with ha3:
        st.markdown('<div class="achievement-card">🔥<br><b>ASSIDUITÉ</b><br><small>10 sessions Anki</small></div>', unsafe_allow_html=True) if len(df_data[df_data['Commentaire'].str.contains("Anki")]) >= 10 else st.write("")

# ==============================================================================
# PAGE : DONJON (⚔️ Placeholder)
# ==============================================================================
elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    st.write("Le donjon est vide et silencieux pour le moment... Tes futurs examens et boss finaux apparaîtront ici.")
