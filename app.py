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

# --- SCRIPT ANTI-AUTOCOMPLETE ---
components.html(
    """<script>
    function cleanInputs() {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            input.setAttribute('autocomplete', 'new-password');
            input.setAttribute('spellcheck', 'false');
        });
    }
    setTimeout(cleanInputs, 500);
    </script>""", height=0
)

# --- CSS (V42 - CLEAN & ÉQUILIBRÉ) ---
st.markdown("""
    <style>
    /* SUPPRESSION HEADER */
    header { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 1rem !important; margin-top: -2rem !important; }
    
    /* Fond global */
    .stApp { background-color: #f4f6f9; color: #333; }

    /* === BARRES === */
    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    /* === UI === */
    .section-header { font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px; }
    
    .stButton>button, .stFormSubmitButton>button {
        width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px;
        background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover { border-color: #333; background-color: #333; color: white; }
    
    .timer-box { font-family: 'Courier New', monospace; font-size: 2.2em; font-weight: bold; color: #d9534f; text-align: center; background-color: #fff; border: 2px solid #d9534f; border-radius: 8px; padding: 15px; margin: 10px 0; }

    /* === MOBILE === */
    @media (max-width: 768px) {
        .bar-label { font-size: 0.65em; }
        .bar-container { height: 12px; }
        [data-testid="column"] { min-width: 0px !important; }
        .stButton button { font-size: 0.75em !important; padding: 0px !important; }
    }

    /* === SPECIAL === */
    .comm-btn > div > div > button { height: 45px !important; }
    @keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }
    .urgent-marker + div > button { background: linear-gradient(135deg, #d9534f, #c9302c) !important; color: white !important; animation: pulse-red 1.5s infinite !important; height: 55px !important; border: none !important; }
    .warning-marker + div > button { background: linear-gradient(135deg, #f0ad4e, #ec971f) !important; color: white !important; height: 48px !important; border: none !important; }
    .gold-banner { background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7); color: #5c4004; padding: 15px; text-align: center; border-radius: 8px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; border: 2px solid #d4af37; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .sober-marker + div > button { background-color: transparent !important; color: #888 !important; border: 1px solid #ccc !important; font-size: 0.7em !important; height: 28px !important; min-height: 28px !important; text-transform: none !important; width: auto !important; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(secrets, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_url(secrets["spreadsheet"])

def load_tasks_v2(col_idx):
    try:
        ws = get_db().worksheet("Tasks")
        data = ws.get_all_values()
        if not data or len(data) < 2: return []
        return [row[col_idx-1] for row in data[1:] if len(row) >= col_idx and row[col_idx-1].strip() != ""]
    except: return []

def add_task(t, col_idx):
    try:
        ws = get_db().worksheet("Tasks")
        col_vals = ws.col_values(col_idx)
        ws.update_cell(len(col_vals) + 1, col_idx, t)
    except: st.error("Erreur GSheets")

def del_task(t, col_idx):
    try:
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=col_idx)
        ws.update_cell(cell.row, col_idx, "")
    except: pass

def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: pass

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

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100, 0, False, False, df
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
        anki = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
        mana = 100 if anki.empty else max(0, 100 - ((datetime.now() - datetime.strptime(anki.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 10))
        admin = df[df['Type'].str.contains("Gestion", case=False, na=False)]
        chaos = 0 if admin.empty else min(100, (datetime.now() - datetime.strptime(admin.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 3)
        cur_m = datetime.now().strftime("%Y-%m")
        rent = not df[df['Date'].str.contains(cur_m, na=False) & df['Commentaire'].str.contains("Loyer", na=False)].empty
        salt = not df[df['Date'].str.contains(cur_m, na=False) & df['Commentaire'].str.contains("Salt", na=False)].empty
        return xp, mana, chaos, rent, salt, df
    except: return 0, 100, 0, False, False, pd.DataFrame()

# --- INIT ---
if 'gym_current_prog' not in st.session_state: st.session_state['gym_current_prog'] = None
if 'anki_start_time' not in st.session_state: st.session_state['anki_start_time'] = None
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Dashboard"

total_xp, current_mana, current_chaos, rent_paid, salt_paid, df_full = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
current_month_name = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"][datetime.now().month-1]

# ==============================================================================
# HEADER
# ==============================================================================
c_av, c_main, c_nav = st.columns([0.15, 0.65, 0.2])
with c_av: st.image("avatar.png", width=70)
with c_main:
    st.markdown(f"<h3 style='margin:0; padding-top:10px;'>NIVEAU {niveau} | SELECTA</h3>", unsafe_allow_html=True)
    st.caption(f"{100 - progress_pct} XP requis pour le niveau {niveau+1}")
with c_nav:
    st.write("")
    n1, n2, n3, n4 = st.columns(4)
    if n1.button("🏰"): st.session_state['current_page'] = "Histoire"; st.rerun()
    if n2.button("🏆"): st.session_state['current_page'] = "HautsFaits"; st.rerun()
    if n3.button("⚔️"): st.session_state['current_page'] = "Donjon"; st.rerun()
    if n4.button("🏠"): st.session_state['current_page'] = "Dashboard"; st.rerun()

st.write("") 
c_b1, c_b2, c_b3 = st.columns(3, gap="medium")
def draw_bar(l, v, c):
    st.markdown(f'<div class="bar-label"><span>{l}</span><span>{int(v)}%</span></div><div class="bar-container"><div class="bar-fill {c}" style="width:{v}%"></div></div>', unsafe_allow_html=True)
with c_b1: draw_bar("EXPÉRIENCE", progress_pct, "xp-fill")
with c_b2: draw_bar("MÉMOIRE", current_mana, "mana-fill")
with c_b3: draw_bar("CHAOS", current_chaos, "chaos-fill")
st.markdown("---")

# ==============================================================================
# PAGES LOGIC
# ==============================================================================

if st.session_state['current_page'] == "Dashboard":
    col_l, col_r = st.columns([1, 1.2], gap="large")
    
    with col_l:
        st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
        with st.form("t_f", clear_on_submit=True):
            nt = st.text_input("Quête...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER TÂCHE") and nt: add_task(nt, 1); st.rerun()
        
        for i, t in enumerate(load_tasks_v2(1)):
            cl1, cl2, cl3 = st.columns([0.75, 0.12, 0.13])
            cl1.write(f"• {t}")
            if cl2.button("✓", key=f"q_{i}"): save_xp(10, "Gestion", t); del_task(t, 1); st.rerun()
            if cl3.button("×", key=f"d_{i}"): del_task(t, 1); st.rerun()

        st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)
        st.markdown("**LOYER**")
        if rent_paid: st.markdown(f'<div class="gold-banner">✨ LOYER {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
        else:
            day = datetime.now().day
            if day >= 29: st.markdown('<span class="urgent-marker"></span>', unsafe_allow_html=True)
            elif day >= 20: st.markdown('<span class="warning-marker"></span>', unsafe_allow_html=True)
            if st.button(f"🏠 PAYER LOYER {current_month_name}", key="r_b"): save_xp(30, "Gestion", "Loyer"); st.rerun()
        if rent_paid:
             st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
             if st.button("↺ Annuler", key="undo_r"): undo_payment("Loyer"); st.rerun()
        
        st.write(""); st.markdown("**SALT**")
        if salt_paid: st.markdown(f'<div class="gold-banner">✨ SALT {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
        else:
            if st.button(f"🏠 PAYER SALT {current_month_name}", key="s_b"): save_xp(30, "Gestion", "Facture: Salt"); st.rerun()
        if salt_paid:
             st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
             if st.button("↺ Annuler", key="undo_s"): undo_payment("Salt"); st.rerun()

        st.write(""); st.markdown("**COMMUNICATIONS**")
        c1, c2, c3 = st.columns(3)
        with c1: st.button("🧹 TRIER", key="m1", on_click=save_xp, args=(10, "Gestion", "Tri Mails"))
        with c2: st.button("✍️ RÉPONDRE", key="m2", on_click=save_xp, args=(10, "Gestion", "Réponse Mails"))
        with c3: st.button("📅 AGENDA", key="m3", on_click=save_xp, args=(10, "Gestion", "Agenda"))

        st.write(""); st.markdown("**AUTRES FACTURES**")
        with st.form("b_f", clear_on_submit=True):
            f1, f2 = st.columns([0.7, 0.3]); fn = f1.text_input("Nom...", label_visibility="collapsed")
            if f2.form_submit_button("PAYER") and fn: save_xp(10, "Gestion", f"Facture: {fn}"); st.rerun()

    with col_r:
        st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2, gap="medium")
        with cc1:
            st.caption("📜 **GRIMOIRE**")
            with st.expander("📥 IMPORTER"):
                up = st.file_uploader("Txt", type="txt")
                if up and st.button("OK"):
                    for l in up.getvalue().decode("utf-8").splitlines():
                        if l.strip(): add_task(l.strip(), 2)
                    st.rerun()
            with st.form("a_f", clear_on_submit=True):
                na = st.text_input("Cours...", label_visibility="collapsed")
                if st.form_submit_button("AJOUTER"): add_task(na, 2); st.rerun()
            for i, t in enumerate(load_tasks_v2(2)):
                st.write(f"**{t}**"); st.button("✓", key=f"v_{i}", on_click=save_xp, args=(30, "Intellect", f"Création: {t}"))
        
        with cc2:
            st.caption("⚔️ **COMBAT**")
            if 'anki_start_time' not in st.session_state or st.session_state['anki_start_time'] is None:
                if st.button("⚔️ LANCER COMBAT", type="primary"): st.session_state['anki_start_time'] = datetime.now(); st.rerun()
            else:
                if st.button("🏁 TERMINER"):
                    mins = int((datetime.now() - st.session_state['anki_start_time']).total_seconds() // 60)
                    save_xp(max(1, mins), "Intellect", "Anki Combat"); st.session_state['anki_start_time'] = None; st.rerun()
                while True:
                    mm, ss = divmod(int((datetime.now() - st.session_state['anki_start_time']).total_seconds()), 60)
                    st.markdown(f'<div class="timer-box">{mm:02d}:{ss:02d}</div>', unsafe_allow_html=True); time.sleep(1); st.rerun()

        st.markdown('<div class="section-header">⚡ ENTRAÎNEMENT</div>', unsafe_allow_html=True)
        cs1, cs2 = st.columns(2, gap="medium")
        FULL_BODY_PROGRAMS = {
            "FB1. STRENGTH": "SQUAT 3x5\nBENCH 3x5\nROWING 3x6\nRDL 3x8\nPLANK 3x1min",
            "FB2. HYPERTROPHY": "PRESSE 3x12\nTIRAGE 3x12\nCHEST PRESS 3x12\nLEG CURL 3x15\nELEVATIONS 3x15",
            "FB3. POWER": "CLEAN 5x3\nJUMP LUNGE 3x8\nPULLUPS 4xMAX\nDIPS 4xMAX\nSWING 3x20",
            "FB4. DUMBBELLS": "GOBLET SQUAT 4x10\nINCLINE PRESS 3x10\nROWING 3x12\nLUNGES 3x10\nARMS 3x12",
            "FB7. CIRCUIT": "THRUSTERS x10\nRENEGADE ROW x8\nCLIMBERS x20\nPUSHUPS xMAX\nJUMPS x15"
        }
        with cs1:
            st.markdown("**🏠 MAISON**")
            if st.button("⏱️ TIMER 20 MIN"):
                ph = st.empty()
                for s in range(1200, -1, -1):
                    m, sec = divmod(s, 60)
                    ph.markdown(f'<div class="timer-box">{m:02d}:{sec:02d}</div>', unsafe_allow_html=True)
                    time.sleep(1)
            if st.button("VALIDER MAISON (+20 XP)"): save_xp(20, "Force", "Maison"); st.rerun()
        with cs2: 
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

elif st.session_state['current_page'] == "Histoire":
    st.markdown('<div class="section-header">📜 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    if df_full.empty: st.write("Aucun exploit enregistré.")
    else:
        for _, r in df_full.iloc[::-1].head(20).iterrows():
            st.markdown(f'<div class="history-card"><b>{r["Date"]}</b> | {r["Type"]} | <b>+{r["XP"]} XP</b><br><small>{r["Commentaire"]}</small></div>', unsafe_allow_html=True)

elif st.session_state['current_page'] == "HautsFaits":
    st.markdown('<div class="section-header">🏆 SALLE DES HAUTS FAITS</div>', unsafe_allow_html=True)
    if df_full.empty: st.info("Continue tes quêtes pour débloquer des trophées !")
    else:
        h1, h2, h3 = st.columns(3)
        with h1: 
            if niveau >= 2: st.markdown('<div class="achievement-card">🎖️<br><b>PREMIER PAS</b><br><small>Atteindre le Niv. 2</small></div>', unsafe_allow_html=True)
        with h2:
            if any(df_full['Commentaire'].str.contains("Loyer", na=False)): st.markdown('<div class="achievement-card">💰<br><b>INTENDANT</b><br><small>Payer son premier loyer</small></div>', unsafe_allow_html=True)
        with h3:
            if len(df_full[df_full['Commentaire'].str.contains("Anki", na=False)]) >= 10: st.markdown('<div class="achievement-card">🔥<br><b>ASSIDUITÉ</b><br><small>10 sessions Anki</small></div>', unsafe_allow_html=True)

elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    st.write("Le donjon est vide. Tes futurs examens apparaîtront ici.")
