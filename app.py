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

# --- NAVIGATION STATE ---
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Dashboard"

# --- SCRIPT ANTI-AUTOCOMPLETE ---
components.html(
    """<script>
    const inputs = window.parent.document.querySelectorAll('input[type="text"]');
    inputs.forEach(input => { input.setAttribute('autocomplete', 'off'); });
    </script>""", height=0
)

# --- CSS (RESTAURATION V34 + FIX PAGES) ---
st.markdown("""
    <style>
    /* Fond global */
    .stApp { background-color: #f4f6f9; color: #333; }
    
    /* FIX TOP : On colle en haut */
    .block-container { padding-top: 1.2rem !important; }

    /* === HEADER HUD (V34 STYLE) === */
    .hud-box {
        background-color: white; padding: 20px; border-radius: 12px;
        border-bottom: 3px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 30px; margin-top: -3rem; 
    }

    /* === BARRES (V34 COLORS) === */
    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    /* === UI GÉNÉRALE === */
    .section-header {
        font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444;
        border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px;
    }
    .stButton>button, .stFormSubmitButton>button {
        width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px;
        background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em; transition: all 0.2s;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover { 
        border-color: #333; background-color: #333; color: white; transform: translateY(-1px); 
    }
    .timer-box { font-family: 'Courier New', monospace; font-size: 2.2em; font-weight: bold; color: #d9534f; text-align: center; background-color: #fff; border: 2px solid #d9534f; border-radius: 8px; padding: 15px; margin: 10px 0; }

    /* === BOUTONS COMMUNICATIONS === */
    .comm-btn > div > div > button { height: 45px !important; font-size: 0.8em !important; }

    /* === LOYER / SALT / GOLD === */
    @keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }
    .urgent-marker + div > button { background: linear-gradient(135deg, #d9534f, #c9302c) !important; color: white !important; border: none !important; animation: pulse-red 1.5s infinite !important; height: 55px !important; font-weight: 900 !important; }
    .warning-marker + div > button { background: linear-gradient(135deg, #f0ad4e, #ec971f) !important; color: white !important; border: none !important; height: 48px !important; font-weight: 800 !important; }
    .gold-banner { background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7); color: #5c4004; padding: 15px; text-align: center; border-radius: 8px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; border: 2px solid #d4af37; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .sober-marker + div > button { background-color: transparent !important; color: #888 !important; border: 1px solid #ccc !important; font-size: 0.7em !important; height: 28px !important; min-height: 28px !important; text-transform: none !important; width: auto !important; margin-top: 5px; }

    /* === PAGES ANNEXES === */
    .history-card { background: white; padding: 12px; border-radius: 8px; border-left: 5px solid #8A2BE2; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .achievement-card { background: white; padding: 20px; border-radius: 12px; border: 2px solid #FFD700; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS BARRE & G-SHEETS ---
def draw_bar(l, v, c):
    st.markdown(f'<div class="bar-label"><span>{l}</span><span>{int(v)}%</span></div><div class="bar-container"><div class="bar-fill {c}" style="width:{v}%"></div></div>', unsafe_allow_html=True)

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

def undo_payment(keyword):
    try:
        ws = get_db().worksheet("Data"); df = pd.DataFrame(ws.get_all_records()); current_month = datetime.now().strftime("%Y-%m")
        mask = df['Date'].astype(str).str.contains(current_month) & df['Commentaire'].astype(str).str.contains(keyword)
        if mask.any(): ws.delete_rows(int(df[mask].index[-1] + 2)); st.toast("Annulé."); return True
    except: pass
    return False

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100, 0, False, False, df
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
        anki_logs = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
        mana = 100 if anki_logs.empty else max(0, 100 - ((datetime.now() - datetime.strptime(anki_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 10))
        admin_logs = df[df['Type'].str.contains("Gestion", case=False, na=False)]
        chaos = 0 if admin_logs.empty else min(100, (datetime.now() - datetime.strptime(admin_logs.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 3)
        current_m = datetime.now().strftime("%Y-%m")
        rent = not df[df['Date'].str.contains(current_m) & df['Commentaire'].str.contains("Loyer")].empty
        salt = not df[df['Date'].str.contains(current_m) & df['Commentaire'].str.contains("Salt")].empty
        return xp, mana, chaos, rent, salt, df
    except: return 0, 100, 0, False, False, pd.DataFrame()

# --- LOGIQUE ---
total_xp, current_mana, current_chaos, rent_paid, salt_paid, df_full = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100
current_month_name = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"][datetime.now().month-1]

# ==============================================================================
# HUD HEADER (V34 ALIGNMENT)
# ==============================================================================
st.markdown('<div class="hud-box">', unsafe_allow_html=True)
c_av, c_main, c_nav = st.columns([0.1, 0.7, 0.2])

with c_av: st.image("avatar.png", width=80)
with c_main:
    st.markdown(f"<h2 style='margin:0; border:none;'>NIVEAU {niveau} | SELECTA</h2>", unsafe_allow_html=True)
    st.caption(f"{100 - progress_pct} XP requis pour le niveau suivant")

with c_nav:
    st.write("")
    nc1, nc2, nc3, nc4 = st.columns(4)
    if nc1.button("🏰", help="Histoire"): st.session_state['current_page'] = "Histoire"; st.rerun()
    if nc2.button("🏆", help="Hauts Faits"): st.session_state['current_page'] = "HautsFaits"; st.rerun()
    if nc3.button("⚔️", help="Donjon"): st.session_state['current_page'] = "Donjon"; st.rerun()
    if nc4.button("🏠", help="Dashboard"): st.session_state['current_page'] = "Dashboard"; st.rerun()

st.write("") 
c_bar1, c_bar2, c_bar3 = st.columns(3, gap="medium")
with c_bar1: draw_bar("EXPÉRIENCE", progress_pct, "xp-fill")
with c_bar2: draw_bar("MÉMOIRE", current_mana, "mana-fill")
with c_bar3: draw_bar("CHAOS", current_chaos, "chaos-fill")
st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# PAGES LOGIC
# ==============================================================================

if st.session_state['current_page'] == "Dashboard":
    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
        with st.form("task_f", clear_on_submit=True):
            nt = st.text_input("Ajouter tâche...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER TÂCHE") and nt: add_task(nt, 1); st.rerun()
        for i, t in enumerate(load_tasks(1)):
            cl1, cl2, cl3 = st.columns([0.75, 0.12, 0.13]); cl1.write(f"• {t}")
            if cl2.button("✓", key=f"q_{i}"): save_xp(5, "Gestion", t); del_task(t, 1); st.rerun()
            if cl3.button("×", key=f"d_{i}"): del_task(t, 1); st.rerun()

        st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)
        st.markdown("**LOYER**")
        if rent_paid:
            st.markdown(f'<div class="gold-banner">✨ LOYER {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
            st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
            if st.button("↺ Annuler", key="undo_r"): undo_payment("Loyer"); st.rerun()
        else:
            day = datetime.now().day
            if day >= 29: st.markdown('<span class="urgent-marker"></span>', unsafe_allow_html=True)
            elif day >= 20: st.markdown('<span class="warning-marker"></span>', unsafe_allow_html=True)
            if st.button(f"🏠 PAYER LOYER {current_month_name}", key="rent_b"): save_xp(50, "Gestion", "Loyer"); st.rerun()

        st.write(""); st.markdown("**SALT**")
        if salt_paid:
            st.markdown(f'<div class="gold-banner">✨ SALT {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
            st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
            if st.button("↺ Annuler", key="undo_s"): undo_payment("Salt"); st.rerun()
        else:
            if st.button(f"🏠 PAYER SALT {current_month_name}", key="salt_b"): save_xp(25, "Gestion", "Facture: Salt"); st.rerun()

        st.write(""); st.markdown("**COMMUNICATIONS**")
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown('<div class="comm-btn">', unsafe_allow_html=True); st.button("🧹 TRIER", on_click=save_xp, args=(5, "Gestion", "Tri Mails")); st.markdown('</div>', unsafe_allow_html=True)
        with c2: st.markdown('<div class="comm-btn">', unsafe_allow_html=True); st.button("✍️ RÉPONDRE", on_click=save_xp, args=(10, "Gestion", "Réponse Mails")); st.markdown('</div>', unsafe_allow_html=True)
        with c3: st.markdown('<div class="comm-btn">', unsafe_allow_html=True); st.button("📅 AGENDA", on_click=save_xp, args=(5, "Gestion", "Agenda")); st.markdown('</div>', unsafe_allow_html=True)

        st.write(""); st.markdown("**AUTRES FACTURES**")
        with st.form("bill_f", clear_on_submit=True):
            f1, f2 = st.columns([0.7, 0.3]); fn = f1.text_input("Nom...", label_visibility="collapsed")
            if f2.form_submit_button("PAYER") and fn: save_xp(15, "Gestion", f"Facture: {fn}"); st.rerun()

    with col_right:
        st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2, gap="medium")
        with cc1:
            st.caption("📜 **GRIMOIRE**")
            with st.expander("📥 IMPORTER TXT"):
                up = st.file_uploader("Fichier", type="txt")
                if up and st.button("IMPORTER"):
                    for l in up.getvalue().decode("utf-8").splitlines():
                        if l.strip(): add_task(l.strip(), 2)
                    st.rerun()
            with st.form("anki_f", clear_on_submit=True):
                na = st.text_input("Cours...", label_visibility="collapsed")
                if st.form_submit_button("AJOUTER") and na: add_task(na, 2); st.rerun()
            for i, t in enumerate(load_tasks(2)):
                st.write(f"**{t}**"); st.button("✓", key=f"v_{i}", on_click=save_xp, args=(30, "Intellect", f"Création: {t}"))
        with cc2:
            st.caption("⚔️ **COMBAT**")
            if 'anki_start_time' not in st.session_state or st.session_state['anki_start_time'] is None:
                st.write("Prêt à réviser ?")
                if st.button("⚔️ LANCER LE COMBAT", type="primary"): st.session_state['anki_start_time'] = datetime.now(); st.rerun()
            else:
                st.write("En combat...")
                if st.button("🏁 TERMINER"):
                    mins = int((datetime.now() - st.session_state['anki_start_time']).total_seconds() // 60)
                    save_xp(max(1, mins) + (5 if mins >= 25 else 0), "Intellect", "Anki Combat"); st.session_state['anki_start_time'] = None; st.rerun()
                while True:
                    mm, ss = divmod(int((datetime.now() - st.session_state['anki_start_time']).total_seconds()), 60)
                    st.markdown(f'<div class="timer-box">{mm:02d}:{ss:02d}</div>', unsafe_allow_html=True); time.sleep(1); st.rerun()

        st.markdown('<div class="section-header">⚡ ENTRAÎNEMENT</div>', unsafe_allow_html=True)
        cs1, cs2 = st.columns(2, gap="medium")
        with cs1:
            st.markdown("**🏠 MAISON**")
            st.button("VALIDER MAISON (+20 XP)", on_click=save_xp, args=(20, "Force", "Maison"))
        with cs2:
            st.markdown("**🏋️ SALLE**")
            st.button("VALIDER SALLE (+50 XP)", on_click=save_xp, args=(50, "Force", "Salle"))

elif st.session_state['current_page'] == "Histoire":
    st.markdown('<div class="section-header">📜 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    if df_full.empty: st.write("Aucune donnée.")
    else:
        for _, r in df_full.iloc[::-1].head(15).iterrows():
            st.markdown(f'<div class="history-card"><b>{r["Date"]}</b> | {r["Type"]} | <b>+{r["XP"]} XP</b><br><small>{r["Commentaire"]}</small></div>', unsafe_allow_html=True)

elif st.session_state['current_page'] == "HautsFaits":
    st.markdown('<div class="section-header">🏆 SALLE DES HAUTS FAITS</div>', unsafe_allow_html=True)
    ha1, ha2, ha3 = st.columns(3)
    # Protection contre DataFrame vide pour éviter le crash
    has_rent = not df_full.empty and any(df_full['Commentaire'].str.contains("Loyer", na=False))
    has_anki = not df_full.empty and len(df_full[df_full['Commentaire'].str.contains("Anki", na=False)]) >= 10

    with ha1:
        if niveau >= 2: st.markdown('<div class="achievement-card">🎖️<br><b>PREMIER PAS</b><br><small>Atteindre le Niv. 2</small></div>', unsafe_allow_html=True)
    with ha2:
        if has_rent: st.markdown('<div class="achievement-card">💰<br><b>INTENDANT</b><br><small>Payer son premier loyer</small></div>', unsafe_allow_html=True)
    with ha3:
        if has_anki: st.markdown('<div class="achievement-card">🔥<br><b>ASSIDUITÉ</b><br><small>10 sessions Anki</small></div>', unsafe_allow_html=True)

elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    st.write("Le donjon est vide. Tes futurs examens apparaîtront ici.")
