import streamlit as st
import pandas as pd
import gspread
import time
import random
import streamlit.components.v1 as components
import urllib.parse
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

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

# --- CSS (V53 - STABLE) ---
st.markdown("""
    <style>
    header { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 1rem !important; margin-top: -2rem !important; }
    .stApp { background-color: #f4f6f9; color: #333; }

    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    .boss-hp-container { background-color: #222; border: 3px solid #000; height: 35px; border-radius: 5px; overflow: hidden; margin: 10px 0 20px 0; position: relative; }
    .boss-hp-fill { background: linear-gradient(90deg, #ff0000, #990000); height: 100%; transition: width 1s ease-out; }
    .boss-hp-text { position: absolute; width: 100%; text-align: center; color: #fff; font-weight: 900; line-height: 35px; text-transform: uppercase; text-shadow: 2px 2px 4px #000; }

    .section-header { font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px; }
    .stButton>button { width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px; background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em; }
    .stButton>button:hover { border-color: #333; background-color: #333; color: white; }
    
    .buff-badge { display: inline-block; background: #e3f2fd; color: #0d47a1; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; margin-right: 5px; border: 1px solid #90caf9; }
    .streak-fire { font-size: 1.2em; font-weight: bold; color: #ff5722; text-shadow: 0 0 5px rgba(255, 87, 34, 0.4); }

    .atk-btn > div > button { background: linear-gradient(135deg, #ffffff, #f0f0f0) !important; color: #444 !important; border: 1px solid #ccc !important; text-transform: none !important; }
    .atk-btn > div > button:hover { background: #333 !important; color: #fff !important; transform: scale(1.02); }

    @media (max-width: 768px) {
        .bar-label { font-size: 0.65em; }
        .bar-container { height: 12px; }
        [data-testid="column"] { min-width: 0px !important; }
    }
    .gold-banner { background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7); color: #5c4004; padding: 15px; text-align: center; border-radius: 8px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; border: 2px solid #d4af37; }
    .timer-box { font-family: 'Courier New', monospace; font-size: 2.2em; font-weight: bold; color: #d9534f; text-align: center; background-color: #fff; border: 2px solid #d9534f; border-radius: 8px; padding: 15px; margin: 10px 0; }
    .history-card { background: white; padding: 12px; border-radius: 8px; border-left: 5px solid #8A2BE2; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- DB ENGINE ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(secrets, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_url(secrets["spreadsheet"])

# --- LEVEL & STREAK ---
def get_level_data(total_xp):
    level, xp_needed = 1, 100
    while total_xp >= xp_needed:
        total_xp -= xp_needed
        level += 1
        xp_needed = 100 * level
    return level, total_xp, xp_needed

def calculate_streak(df):
    if df.empty: return 0
    df['D'] = pd.to_datetime(df['Date']).dt.date
    dates = sorted(df['D'].unique(), reverse=True)
    today = datetime.now().date()
    if not dates or (dates[0] != today and dates[0] != today - timedelta(days=1)): return 0
    streak, check = 0, dates[0]
    for d in dates:
        if d == check: streak += 1; check -= timedelta(days=1)
        else: break
    return streak

# --- XP & TASKS ---
def save_xp(amt, type_s, cmt=""):
    try:
        db = get_db().worksheet("Data")
        df = pd.DataFrame(db.get_all_records())
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum()) if not df.empty else 0
        lvl, _, _ = get_level_data(xp)
        if lvl >= 5 and type_s == "Intellect": amt = int(amt * 1.1)
        if lvl >= 20 and type_s == "Force": amt = int(amt * 1.2)
        db.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"⚔️ +{amt} XP")
        if get_level_data(xp + amt)[0] > lvl: st.balloons()
    except: pass

def load_tasks_v2(col_idx):
    try:
        data = get_db().worksheet("Tasks").get_all_values()
        return [row[col_idx-1] for row in data[1:] if len(row) >= col_idx and row[col_idx-1].strip() != ""]
    except: return []

def del_task(t, col_idx):
    try:
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=col_idx)
        if cell: ws.update_cell(cell.row, col_idx, "")
    except: pass

def add_multiple_tasks(tasks, col_idx):
    try:
        ws = get_db().worksheet("Tasks")
        start = len(ws.col_values(col_idx)) + 1
        cells = ws.range(start, col_idx, start + len(tasks) - 1, col_idx)
        for i, c in enumerate(cells): c.value = tasks[i]
        ws.update_cells(cells)
    except: pass

# --- BOSS ENGINE ---
def attack_boss(b_name, chap, dmg):
    db = get_db()
    ws_t = db.worksheet("Boss_Tasks"); cell = ws_t.find(chap)
    if cell: ws_t.delete_rows(cell.row)
    ws_b = db.worksheet("Bosses"); b_cell = ws_b.find(b_name)
    pv = max(0, float(ws_b.cell(b_cell.row, 4).value) - dmg)
    ws_b.update_cell(b_cell.row, 4, pv)

# --- INIT ---
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Dashboard"
try:
    df_raw = pd.DataFrame(get_db().worksheet("Data").get_all_records())
    total_xp = int(pd.to_numeric(df_raw["XP"], errors='coerce').sum()) if not df_raw.empty else 0
    lvl, xp_in, xp_req = get_level_data(total_xp)
    streak = calculate_streak(df_raw)
    loss = 8 if lvl >= 10 else 10
    anki = df_raw[df_raw['Commentaire'].str.contains("Combat", na=False)]
    mana = 100 if anki.empty else max(0, 100 - ((datetime.now() - datetime.strptime(anki.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * loss))
    chaos = 0 if df_raw[df_raw['Type'].str.contains("Gestion", na=False)].empty else min(100, (datetime.now() - datetime.strptime(df_raw[df_raw['Type'].str.contains("Gestion", na=False)].iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 3)
    cur_m = datetime.now().strftime("%Y-%m")
    rent = not df_raw[df_raw['Date'].str.contains(cur_m, na=False) & df_raw['Commentaire'].str.contains("Loyer", na=False)].empty
    salt = not df_raw[df_raw['Date'].str.contains(cur_m, na=False) & df_raw['Commentaire'].str.contains("Salt", na=False)].empty
except: total_xp, lvl, xp_in, xp_req, streak, mana, chaos, rent, salt, df_raw = 0, 1, 0, 100, 0, 100, 0, False, False, pd.DataFrame()

# ==============================================================================
# HEADER
# ==============================================================================
c_av, c_main, c_nav = st.columns([0.15, 0.60, 0.25])
with c_av: st.image("avatar.png", width=70)
with c_main:
    st.markdown(f"<h3 style='margin:0;'>NIVEAU {lvl} | SELECTA <span class='streak-fire'>🔥 {streak}</span></h3>", unsafe_allow_html=True)
    if lvl >= 5: st.markdown("<span class='buff-badge'>🧠 Érudit (+10% Intellect)</span>", unsafe_allow_html=True)
    if lvl >= 10: st.markdown("<span class='buff-badge'>🛡️ Mémoire d'Or (-8% Decay)</span>", unsafe_allow_html=True)
    st.caption(f"{int(xp_req - xp_in)} XP requis pour le niveau {lvl+1}")
with c_nav:
    n1, n2, n3, n4 = st.columns(4)
    if n1.button("🏰"): st.session_state['current_page'] = "Histoire"; st.rerun()
    if n2.button("🏆"): st.session_state['current_page'] = "HautsFaits"; st.rerun()
    if n3.button("⚔️"): st.session_state['current_page'] = "Donjon"; st.rerun()
    if n4.button("🏠"): st.session_state['current_page'] = "Dashboard"; st.rerun()

st.write("") 
c_b1, c_b2, c_b3 = st.columns(3)
def draw_bar(l, v, c):
    st.markdown(f'<div class="bar-label"><span>{l}</span><span>{int(v)}%</span></div><div class="bar-container"><div class="bar-fill {c}" style="width:{v}%"></div></div>', unsafe_allow_html=True)
draw_bar("EXPÉRIENCE", (xp_in/xp_req)*100, "xp-fill")
draw_bar("MÉMOIRE", mana, "mana-fill")
draw_bar("CHAOS", chaos, "chaos-fill")
st.markdown("---")

# ==============================================================================
# PAGES
# ==============================================================================
if st.session_state['current_page'] == "Dashboard":
    col_l, col_r = st.columns([1, 1.2], gap="large")
    with col_l:
        st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
        with st.form("t_f", clear_on_submit=True):
            nt = st.text_input("Quête...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER"):
                try: ws=get_db().worksheet("Tasks"); ws.update_cell(len(ws.col_values(1))+1, 1, nt); st.rerun()
                except: pass
        for i, t in enumerate(load_tasks_v2(1)):
            cl1, cl2, cl3 = st.columns([0.7, 0.15, 0.15])
            cl1.write(f"• {t}")
            if cl2.button("✓", key=f"q_{i}"): save_xp(10, "Gestion", t); del_task(t, 1); st.rerun()
            if cl3.button("×", key=f"d_{i}"): del_task(t, 1); st.rerun()

        st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)
        for name, xp_v, paid, k in [("LOYER", 30, rent, "r"), ("SALT", 30, salt, "s")]:
            if paid: st.markdown(f'<div class="gold-banner">✨ {name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
            else:
                if st.button(f"🏠 PAYER {name}", key=f"btn_{k}"): save_xp(xp_v, "Gestion", name); st.rerun()
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.button("🧹 TRIER", on_click=save_xp, args=(10, "Gestion", "Tri"))
        with c2: st.button("✍️ RÉPONDRE", on_click=save_xp, args=(10, "Gestion", "Réponse"))
        with c3: st.button("📅 AGENDA", on_click=save_xp, args=(10, "Gestion", "Agenda"))

    with col_r:
        st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            st.caption("📜 **GRIMOIRE**")
            with st.expander("📥 IMPORTER"):
                up = st.file_uploader(".txt", type="txt", key="gup")
                if up and st.button("GO"):
                    ls = [l.strip() for l in up.getvalue().decode().splitlines() if l.strip()]
                    if ls: add_multiple_tasks(ls, 2)
                    st.rerun()
            for i, t in enumerate(load_tasks_v2(2)):
                st.write(f"**{t}**")
                # FIX V53: Ajout de del_task(t, 2) pour faire disparaître le cours
                if st.button("✓", key=f"v_{i}"):
                    save_xp(30, "Intellect", t)
                    del_task(t, 2)
                    st.rerun()
        with cc2:
            st.caption("⚔️ **COMBAT**")
            if 'anki_start_time' not in st.session_state:
                if st.button("⚔️ LANCER COMBAT", type="primary"): st.session_state['anki_start_time'] = datetime.now(); st.rerun()
            else:
                if st.button("🏁 TERMINER"):
                    m = int((datetime.now() - st.session_state['anki_start_time']).total_seconds() // 60)
                    save_xp(max(1, m), "Intellect", "Anki"); del st.session_state['anki_start_time']; st.rerun()

elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    with st.expander("➕ INVOQUER UN BOSS"):
        with st.form("nb"):
            n = st.text_input("Nom"); d = st.date_input("Date")
            if st.form_submit_button("SCELLER"):
                get_db().worksheet("Bosses").append_row([n, d.strftime("%Y-%m-%d"), 0, 100]); st.rerun()
    try:
        for _, b in pd.DataFrame(get_db().worksheet("Bosses").get_all_records()).iterrows():
            pv = b['PV_Restants']
            try: days = (pd.to_datetime(b['Date']).date() - datetime.now().date()).days
            except: days = "?"
            st.markdown(f"## 👹 {b['Nom']} <span style='font-size:0.5em;color:#d9534f;margin-left:15px;'>⏳ J-{days}</span>", unsafe_allow_html=True)
            st.markdown(f'<div class="boss-hp-container"><div class="boss-hp-text">{int(pv)}% PV</div><div class="boss-hp-fill" style="width:{pv}%"></div></div>', unsafe_allow_html=True)
            df_c = load_boss_chapters(b['Nom'])
            if df_c.empty and pv > 0:
                up = st.file_uploader(f"Munitions {b['Nom']}", type="txt", key=f"u{b['Nom']}")
                if up:
                    content = [l.strip() for l in up.getvalue().decode().splitlines() if l.strip()]
                    ws_t = get_db().worksheet("Boss_Tasks"); ws_t.append_rows([[b['Nom'], c] for c in content])
                    ws_b = get_db().worksheet("Bosses"); row = ws_b.find(b['Nom']).row; ws_b.update_cell(row, 3, len(content)); st.rerun()
            elif pv > 0:
                dmg = 100 / b['Total_Initial']
                cols = st.columns(2)
                for i, row in enumerate(df_c.iterrows()):
                    with cols[i%2]:
                        if st.button(f"🔥 {row[1]['Chapitre']}", key=f"a{b['Nom']}{i}"):
                            attack_boss(b['Nom'], row[1]['Chapitre'], dmg); save_xp(10, "Combat Boss", b['Nom']); st.rerun()
            else:
                st.success("VAINCU !"); st.button("💎 TRÉSOR (+200 XP)", on_click=save_xp, args=(200, "Victoire", b['Nom']))
    except: pass

elif st.session_state['current_page'] == "Histoire":
    st.markdown('<div class="section-header">📜 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    if not df_raw.empty:
        for _, r in df_raw.iloc[::-1].head(15).iterrows():
            st.markdown(f'<div class="history-card"><b>{r["Date"]}</b> | {r["Type"]} | <b>+{r["XP"]} XP</b><br>{r["Commentaire"]}</div>', unsafe_allow_html=True)
