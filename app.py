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

# --- CSS (V52) ---
st.markdown("""
    <style>
    header { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 1rem !important; margin-top: -2rem !important; }
    .stApp { background-color: #f4f6f9; color: #333; }

    /* BARRES STATS */
    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    /* BOSS */
    .boss-hp-container { background-color: #222; border: 3px solid #000; height: 35px; border-radius: 5px; overflow: hidden; margin: 10px 0 20px 0; position: relative; }
    .boss-hp-fill { background: linear-gradient(90deg, #ff0000, #990000); height: 100%; transition: width 1s ease-out; }
    .boss-hp-text { position: absolute; width: 100%; text-align: center; color: #fff; font-weight: 900; line-height: 35px; text-transform: uppercase; text-shadow: 2px 2px 4px #000; }

    /* UI ELEMENTS */
    .section-header { font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px; }
    .stButton>button { width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px; background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em; }
    .stButton>button:hover { border-color: #333; background-color: #333; color: white; }
    
    .buff-badge { display: inline-block; background: #e3f2fd; color: #0d47a1; padding: 2px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; margin-right: 5px; border: 1px solid #90caf9; }
    .streak-fire { font-size: 1.2em; font-weight: bold; color: #ff5722; text-shadow: 0 0 5px rgba(255, 87, 34, 0.4); }

    /* ARSENAL */
    .atk-btn > div > button { background: linear-gradient(135deg, #ffffff, #f0f0f0) !important; color: #444 !important; border: 1px solid #ccc !important; text-transform: none !important; }
    .atk-btn > div > button:hover { background: #333 !important; color: #fff !important; transform: scale(1.02); }

    /* MOBILE */
    @media (max-width: 768px) {
        .bar-label { font-size: 0.65em; }
        .bar-container { height: 12px; }
        [data-testid="column"] { min-width: 0px !important; }
    }
    .gold-banner { background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7); color: #5c4004; padding: 15px; text-align: center; border-radius: 8px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; border: 2px solid #d4af37; }
    .timer-box { font-family: 'Courier New', monospace; font-size: 2.2em; font-weight: bold; color: #d9534f; text-align: center; background-color: #fff; border: 2px solid #d9534f; border-radius: 8px; padding: 15px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS ENGINE ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(secrets, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_url(secrets["spreadsheet"])

# --- LEVEL SCALING LOGIC (Nouveau) ---
def get_level_data(total_xp):
    level = 1
    xp_needed = 100
    while total_xp >= xp_needed:
        total_xp -= xp_needed
        level += 1
        xp_needed = 100 * level # Difficulté croissante (100, 200, 300...)
    return level, total_xp, xp_needed

# --- STREAK LOGIC (Nouveau) ---
def calculate_streak(df):
    if df.empty: return 0
    df['DateOnly'] = pd.to_datetime(df['Date']).dt.date
    dates = sorted(df['DateOnly'].unique(), reverse=True)
    if not dates: return 0
    
    streak = 0
    today = datetime.now().date()
    
    # Si pas d'activité aujourd'hui, on regarde hier pour ne pas casser la série
    if dates[0] == today:
        current_check = today
    elif dates[0] == today - timedelta(days=1):
        current_check = today - timedelta(days=1)
    else:
        return 0 # Série brisée

    for d in dates:
        if d == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        else:
            break
    return streak

# --- XP & BUFFS SYSTEM ---
def save_xp(amt, type_s, cmt=""):
    try:
        # Récupération niveau pour Buffs
        ws_data = get_db().worksheet("Data")
        df = pd.DataFrame(ws_data.get_all_records())
        current_xp = int(pd.to_numeric(df["XP"], errors='coerce').sum()) if not df.empty else 0
        lvl, _, _ = get_level_data(current_xp)
        
        # BUFFS PASSIFS
        bonus_msg = ""
        if lvl >= 5 and type_s == "Intellect":
            amt = int(amt * 1.1) # +10%
            bonus_msg = " (Buff Érudit ⭐)"
        if lvl >= 20 and type_s == "Force":
            amt = int(amt * 1.2) # +20%
            bonus_msg = " (Buff Titan 💪)"
            
        ws_data.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"⚔️ +{amt} XP{bonus_msg}")
        
        # Check Level Up pour effet visuel
        new_lvl, _, _ = get_level_data(current_xp + amt)
        if new_lvl > lvl: st.balloons()
            
    except: pass

def get_stats():
    try:
        df = pd.DataFrame(get_db().worksheet("Data").get_all_records())
        if df.empty: return 0, 100, 0, False, False, df, 0
        
        xp = int(pd.to_numeric(df["XP"], errors='coerce').sum())
        lvl, _, _ = get_level_data(xp)
        
        # STREAK
        streak = calculate_streak(df)
        
        # MANA (Buff Mémoire d'Or au Niv 10)
        loss_rate = 8 if lvl >= 10 else 10
        anki = df[df['Commentaire'].str.contains("Combat", case=False, na=False)]
        mana = 100 if anki.empty else max(0, 100 - ((datetime.now() - datetime.strptime(anki.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * loss_rate))
        
        admin = df[df['Type'].str.contains("Gestion", case=False, na=False)]
        chaos = 0 if admin.empty else min(100, (datetime.now() - datetime.strptime(admin.iloc[-1]['Date'], "%Y-%m-%d %H:%M")).days * 3)
        
        cur_m = datetime.now().strftime("%Y-%m")
        rent = not df[df['Date'].str.contains(cur_m, na=False) & df['Commentaire'].str.contains("Loyer", na=False)].empty
        salt = not df[df['Date'].str.contains(cur_m, na=False) & df['Commentaire'].str.contains("Salt", na=False)].empty
        
        return xp, mana, chaos, rent, salt, df, streak
    except: return 0, 100, 0, False, False, pd.DataFrame(), 0

# --- DATA LOADERS (Batch) ---
def load_tasks_v2(col_idx):
    try:
        ws = get_db().worksheet("Tasks"); data = ws.get_all_values()
        if not data or len(data) < 2: return []
        return [row[col_idx-1] for row in data[1:] if len(row) >= col_idx and row[col_idx-1].strip() != ""]
    except: return []

def add_task(t, col_idx):
    try:
        ws = get_db().worksheet("Tasks"); col_vals = ws.col_values(col_idx)
        ws.update_cell(len(col_vals) + 1, col_idx, t)
    except: pass

def add_multiple_tasks(tasks, col_idx):
    try:
        ws = get_db().worksheet("Tasks")
        col_vals = ws.col_values(col_idx)
        start_row = len(col_vals) + 1
        cell_list = ws.range(start_row, col_idx, start_row + len(tasks) - 1, col_idx)
        for i, cell in enumerate(cell_list): cell.value = tasks[i]
        ws.update_cells(cell_list)
    except: pass

def del_task(t, col_idx):
    try:
        ws = get_db().worksheet("Tasks"); cell = ws.find(t, in_column=col_idx)
        ws.update_cell(cell.row, col_idx, "")
    except: pass

# --- BOSS ENGINE ---
def load_bosses():
    try: return pd.DataFrame(get_db().worksheet("Bosses").get_all_records())
    except: return pd.DataFrame()

def load_boss_chapters(boss_name):
    try:
        df = pd.DataFrame(get_db().worksheet("Boss_Tasks").get_all_records())
        if df.empty: return pd.DataFrame()
        return df[df['Boss_Nom'] == boss_name]
    except: return pd.DataFrame()

def attack_boss(boss_name, chapter_name, damage):
    db = get_db()
    ws_tasks = db.worksheet("Boss_Tasks"); cell = ws_tasks.find(chapter_name)
    if cell: ws_tasks.delete_rows(cell.row)
    ws_boss = db.worksheet("Bosses"); b_cell = ws_boss.find(boss_name)
    current_pv = float(ws_boss.cell(b_cell.row, 4).value)
    ws_boss.update_cell(b_cell.row, 4, max(0, current_pv - damage))

# --- CALENDAR ---
def create_cal_link(title):
    base = "https://www.google.com/calendar/render?action=TEMPLATE"
    now = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0).strftime('%Y%m%dT%H%M00')
    end = (datetime.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0).strftime('%Y%m%dT%H%M00')
    return f"{base}&text={urllib.parse.quote('[RPG] '+title)}&dates={now}/{end}"

# --- INIT ---
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Dashboard"
if 'gym_current_prog' not in st.session_state: st.session_state['gym_current_prog'] = None

total_xp, current_mana, current_chaos, rent_paid, salt_paid, df_full, current_streak = get_stats()
niveau, xp_in_level, xp_needed = get_level_data(total_xp)
progress_pct = (xp_in_level / xp_needed) * 100
current_month_name = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"][datetime.now().month-1]

# ==============================================================================
# HEADER
# ==============================================================================
c_av, c_main, c_nav = st.columns([0.15, 0.60, 0.25])
with c_av: st.image("avatar.png", width=70)
with c_main:
    # Header avec Streak et Buffs
    st.markdown(f"<h3 style='margin:0; padding-top:10px;'>NIVEAU {niveau} | SELECTA <span class='streak-fire'>🔥 {current_streak}</span></h3>", unsafe_allow_html=True)
    
    # Affichage des Buffs Actifs
    buffs_html = ""
    if niveau >= 5: buffs_html += "<span class='buff-badge'>🧠 Érudit (+10% Intellect)</span>"
    if niveau >= 10: buffs_html += "<span class='buff-badge'>🛡️ Mémoire d'Or (-8% Decay)</span>"
    if niveau >= 20: buffs_html += "<span class='buff-badge'>💪 Titan (+20% Force)</span>"
    if buffs_html: st.markdown(buffs_html, unsafe_allow_html=True)
    
    st.caption(f"{int(xp_needed - xp_in_level)} XP requis pour le niveau {niveau+1}")

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
# PAGES
# ==============================================================================

if st.session_state['current_page'] == "Dashboard":
    col_l, col_r = st.columns([1, 1.2], gap="large")
    with col_l:
        st.markdown('<div class="section-header">📌 QUÊTES DU JOUR</div>', unsafe_allow_html=True)
        with st.form("t_f", clear_on_submit=True):
            nt = st.text_input("Quête...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER TÂCHE") and nt: add_task(nt, 1); st.rerun()
        for i, t in enumerate(load_tasks_v2(1)):
            cl1, cl2, cl3, cl4 = st.columns([0.65, 0.12, 0.12, 0.11])
            cl1.write(f"• {t}")
            cl2.link_button("📅", create_cal_link(t))
            if cl3.button("✓", key=f"q_{i}"): save_xp(10, "Gestion", t); del_task(t, 1); st.rerun()
            if cl4.button("×", key=f"d_{i}"): del_task(t, 1); st.rerun()

        st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)
        for name, xp_v, paid, k in [("LOYER", 30, rent_paid, "r"), ("SALT", 30, salt_paid, "s")]:
            st.markdown(f"**{name}**")
            if paid: 
                st.markdown(f'<div class="gold-banner">✨ {name} {current_month_name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
                st.markdown('<span class="sober-marker"></span>', unsafe_allow_html=True)
                if st.button(f"↺ Annuler {name}", key=f"undo_{k}"): st.toast("Action Excel requise."); st.rerun()
            else:
                if st.button(f"🏠 PAYER {name}", key=f"btn_{k}"): save_xp(xp_v, "Gestion", name); st.rerun()

        st.write(""); st.markdown("**COMMUNICATIONS**")
        c1, c2, c3 = st.columns(3)
        with c1: st.button("🧹 TRIER", on_click=save_xp, args=(10, "Gestion", "Tri"))
        with c2: st.button("✍️ RÉPONDRE", on_click=save_xp, args=(10, "Gestion", "Réponse"))
        with c3: st.button("📅 AGENDA", on_click=save_xp, args=(10, "Gestion", "Agenda"))

    with col_r:
        st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2, gap="medium")
        with cc1:
            st.caption("📜 **GRIMOIRE**")
            with st.expander("📥 IMPORTER TXT"):
                up = st.file_uploader("Fichier .txt", type="txt", key="grim_up")
                if up and st.button("IMPORTER"):
                    lines = [l.strip() for l in up.getvalue().decode("utf-8").splitlines() if l.strip()]
                    if lines: add_multiple_tasks(lines, 2)
                    st.rerun()
            with st.form("a_f", clear_on_submit=True):
                na = st.text_input("Cours...", label_visibility="collapsed")
                if st.form_submit_button("AJOUTER"): add_task(na, 2); st.rerun()
            for i, t in enumerate(load_tasks_v2(2)):
                st.write(f"**{t}**"); st.button("✓", key=f"v_{i}", on_click=save_xp, args=(30, "Intellect", t))
                
        with cc2:
            st.caption("⚔️ **COMBAT**")
            if 'anki_start_time' not in st.session_state or st.session_state['anki_start_time'] is None:
                if st.button("⚔️ LANCER COMBAT", type="primary"): st.session_state['anki_start_time'] = datetime.now(); st.rerun()
            else:
                if st.button("🏁 TERMINER"):
                    mins = int((datetime.now() - st.session_state['anki_start_time']).total_seconds() // 60)
                    save_xp(max(1, mins), "Intellect", "Anki"); st.session_state['anki_start_time'] = None; st.rerun()

        st.markdown('<div class="section-header">⚡ ENTRAÎNEMENT</div>', unsafe_allow_html=True)
        cs1, cs2 = st.columns(2, gap="medium")
        with cs1:
            if st.button("⏱️ TIMER 20 MIN"):
                p = st.empty()
                for s in range(1200, -1, -1):
                    m, sc = divmod(s, 60); p.markdown(f'<div class="timer-box">{m:02d}:{sc:02d}</div>', unsafe_allow_html=True); time.sleep(1)
            st.button("VALIDER MAISON (+20 XP)", on_click=save_xp, args=(20, "Force", "Maison"))
        with cs2:
            FULL_BODY_PROGRAMS = {
                "FB1. STRENGTH": "SQUAT 3x5\nBENCH 3x5\nROWING 3x6\nRDL 3x8\nPLANK 3x1min",
                "FB2. HYPERTROPHY": "PRESSE 3x12\nTIRAGE 3x12\nCHEST PRESS 3x12\nLEG CURL 3x15\nELEVATIONS 3x15",
                "FB3. POWER": "CLEAN 5x3\nJUMP LUNGE 3x8\nPULLUPS 4xMAX\nDIPS 4xMAX\nSWING 3x20",
                "FB4. DUMBBELLS": "GOBLET SQUAT 4x10\nINCLINE PRESS 3x10\nROWING 3x12\nLUNGES 3x10\nARMS 3x12",
                "FB7. CIRCUIT": "THRUSTERS x10\nRENEGADE ROW x8\nCLIMBERS x20\nPUSHUPS xMAX\nJUMPS x15"
            }
            if st.button("🎲 GÉNÉRER SÉANCE"):
                n, d = random.choice(list(FULL_BODY_PROGRAMS.items()))
                st.session_state['gym_current_prog'] = (n, d)
                st.rerun()
            if st.session_state['gym_current_prog']:
                n, d = st.session_state['gym_current_prog']
                st.markdown(f"**{n}**"); 
                for l in d.split('\n'): st.markdown(f"- {l}")
                if st.button("VALIDER SALLE (+50 XP)"):
                    save_xp(50, "Force", n); st.session_state['gym_current_prog'] = None; st.rerun()
            else:
                st.button("VALIDER SALLE (+50 XP)", on_click=save_xp, args=(50, "Force", "Salle"))

elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    with st.expander("➕ INVOQUER UN BOSS (EXAMEN)"):
        with st.form("nb", clear_on_submit=True):
            n = st.text_input("Nom de l'Examen"); d = st.date_input("Date de l'échéance")
            if st.form_submit_button("SCELLER LE PACTE"):
                try: get_db().worksheet("Bosses").append_row([n, d.strftime("%Y-%m-%d"), 0, 100]); st.rerun()
                except: st.error("Crée l'onglet 'Bosses' dans ton Google Sheets !")
    
    df_b = load_bosses()
    if df_b.empty: st.write("Donjon vide.")
    else:
        for _, b in df_b.iterrows():
            pv = b['PV_Restants']; b_name = b['Nom']; b_date_str = str(b['Date'])
            try:
                days_left = (datetime.strptime(b_date_str, "%Y-%m-%d").date() - datetime.now().date()).days
                timer_txt = f"⏳ {b_date_str} (J-{days_left})" if days_left > 0 else ("🔥 JOUR J !" if days_left == 0 else f"💀 DÉPASSÉ (J+{abs(days_left)})")
            except: timer_txt = ""

            st.markdown(f"## 👹 {b_name} <span style='font-size: 0.5em; color: #d9534f; margin-left: 15px;'>{timer_txt}</span>", unsafe_allow_html=True)
            st.markdown(f'<div class="boss-hp-container"><div class="boss-hp-text">{int(pv)}% PV</div><div class="boss-hp-fill" style="width:{pv}%"></div></div>', unsafe_allow_html=True)
            
            df_c = load_boss_chapters(b_name)
            if df_c.empty and pv > 0:
                up = st.file_uploader(f"Charge tes munitions pour {b_name} (.txt)", type="txt", key=f"up_{b_name}")
                if up:
                    content = up.getvalue().decode("utf-8").splitlines()
                    chapters = [line.strip() for line in content if line.strip()]
                    try:
                        ws_t = get_db().worksheet("Boss_Tasks"); rows = [[b_name, c] for c in chapters]
                        ws_t.append_rows(rows)
                        ws_b = get_db().worksheet("Bosses"); row_idx = ws_b.find(b_name).row
                        ws_b.update_cell(row_idx, 3, len(chapters)); st.rerun()
                    except: st.error("Onglet 'Boss_Tasks' manquant !")
            elif pv > 0:
                dmg = 100 / b['Total_Initial']
                st.write("### 🗡️ CHOISIS TON ATTAQUE (ARSENAL)")
                cols = st.columns(2)
                for i, row in enumerate(df_c.iterrows()):
                    with cols[i%2]:
                        st.markdown('<div class="atk-btn">', unsafe_allow_html=True)
                        if st.button(f"🔥 {row[1]['Chapitre']}", key=f"atk_{b_name}_{i}"):
                            attack_boss(b_name, row[1]['Chapitre'], dmg); save_xp(10, "Combat Boss", b_name); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success(f"🏆 {b_name} TERRASSÉ !"); 
                if st.button(f"💎 RÉCLAMER TRÉSOR (+200 XP)", key=f"win_{b_name}"):
                    save_xp(200, "Victoire", b_name); st.balloons(); st.rerun()

elif st.session_state['current_page'] == "Histoire":
    st.markdown('<div class="section-header">📜 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    if not df_full.empty:
        for _, r in df_full.iloc[::-1].head(15).iterrows():
            st.markdown(f'<div class="history-card"><b>{r["Date"]}</b> | {r["Type"]} | <b>+{r["XP"]} XP</b><br>{r["Commentaire"]}</div>', unsafe_allow_html=True)

elif st.session_state['current_page'] == "HautsFaits":
    st.markdown('<div class="section-header">🏆 SALLE DES HAUTS FAITS</div>', unsafe_allow_html=True)
    if df_full.empty: st.write("Aucun exploit enregistré.")
    else:
        h1, h2, h3 = st.columns(3)
        with h1: 
            if niveau >= 2: st.markdown('<div class="achievement-card">🎖️<br><b>PREMIER PAS</b><br><small>Atteindre le Niv. 2</small></div>', unsafe_allow_html=True)
        with h2:
            try: 
                if any(df_full['Commentaire'].str.contains("LOYER", na=False)): st.markdown('<div class="achievement-card">💰<br><b>INTENDANT</b></div>', unsafe_allow_html=True)
            except: pass
        with h3:
            try:
                if len(df_full[df_full['Commentaire'].str.contains("Anki", na=False)]) >= 10: st.markdown('<div class="achievement-card">🔥<br><b>ASSIDUITÉ</b></div>', unsafe_allow_html=True)
            except: pass
