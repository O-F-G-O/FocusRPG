import streamlit as st
import pandas as pd
import gspread
import random
import time
import streamlit.components.v1 as components
import urllib.parse
import logging
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- LOGGING ---
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
st.set_page_config(page_title="Selecta RPG", page_icon="🛡️", layout="wide")

components.html("""<script>
    function cleanInputs() {
        const inputs = window.parent.document.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            input.setAttribute('autocomplete', 'new-password');
            input.setAttribute('spellcheck', 'false');
        });
    }
    setTimeout(cleanInputs, 500);
</script>""", height=0)

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

    /* Tâche bloquée */
    .task-blocked { color: #999; font-style: italic; text-decoration: none; }

    .gold-banner { background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7); color: #5c4004; padding: 15px; text-align: center; border-radius: 8px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; border: 2px solid #d4af37; margin-bottom: 15px; }
    .history-card { background: white; padding: 12px; border-radius: 8px; border-left: 5px solid #8A2BE2; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .achievement-card { background: white; padding: 20px; border-radius: 12px; border: 2px solid #FFD700; text-align: center; margin-bottom: 10px; }

    /* Bouton Anki / Sport = gros et visible */
    .big-action > div > button {
        background: linear-gradient(135deg, #8A2BE2, #9e47ff) !important;
        color: white !important;
        border: none !important;
        font-size: 1em !important;
        min-height: 56px !important;
        border-radius: 8px !important;
    }
    .big-action-green > div > button {
        background: linear-gradient(135deg, #1a7a3f, #28a745) !important;
        color: white !important;
        border: none !important;
        font-size: 1em !important;
        min-height: 56px !important;
        border-radius: 8px !important;
    }

    @media (max-width: 768px) {
        .bar-label { font-size: 0.65em; }
        .bar-container { height: 12px; }
        [data-testid="column"] { min-width: 0px !important; }
    }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# ENGINE
# ==============================================================================

@st.cache_resource(ttl=300)
def get_gspread_client():
    secrets = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(
        secrets,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds), secrets["spreadsheet"]

def get_db():
    client, url = get_gspread_client()
    return client.open_by_url(url)

@st.cache_data(ttl=30)
def load_sheet_data(sheet_name: str) -> pd.DataFrame:
    """Lecture avec 3 tentatives pour éviter le crash XP → 0."""
    for attempt in range(3):
        try:
            return pd.DataFrame(get_db().worksheet(sheet_name).get_all_records())
        except Exception as e:
            if attempt == 2:
                logger.error(f"load_sheet_data({sheet_name}) failed after 3 attempts: {e}")
                return pd.DataFrame()
            time.sleep(0.5)

def invalidate_cache():
    load_sheet_data.clear()

def get_level_data(total_xp: int):
    level, xp_needed = 1, 100
    while total_xp >= xp_needed:
        total_xp -= xp_needed
        level += 1
        xp_needed = 100 * level
    return level, total_xp, xp_needed

def calculate_streak(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    try:
        dates = pd.to_datetime(df['Date'], errors='coerce').dropna().dt.date.unique()
        dates = sorted(dates, reverse=True)
        today = datetime.now().date()
        if not dates:
            return 0
        if dates[0] == today:
            check = today
        elif dates[0] == today - timedelta(days=1):
            check = today - timedelta(days=1)
        else:
            return 0
        streak = 0
        for d in dates:
            if d == check:
                streak += 1
                check -= timedelta(days=1)
            else:
                break
        return streak
    except Exception as e:
        logger.warning(f"calculate_streak failed: {e}")
        return 0

def parse_last_date(df: pd.DataFrame, mask) -> datetime | None:
    try:
        sub = df[mask]
        if sub.empty:
            return None
        last = pd.to_datetime(sub.iloc[-1]['Date'], errors='coerce')
        return last if not pd.isnull(last) else None
    except Exception as e:
        logger.warning(f"parse_last_date failed: {e}")
        return None

def save_xp(amt: int, type_s: str, cmt: str = ""):
    try:
        df = load_sheet_data("Data")
        xp = int(pd.to_numeric(df["XP"], errors='coerce').fillna(0).sum()) if not df.empty else 0
        lvl, _, _ = get_level_data(xp)
        if lvl >= 5 and type_s == "Intellect":
            amt = int(amt * 1.1)
        if lvl >= 20 and type_s == "Force":
            amt = int(amt * 1.2)
        get_db().worksheet("Data").append_row(
            [datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt]
        )
        invalidate_cache()
        st.toast(f"⚔️ +{amt} XP")
        if get_level_data(xp + amt)[0] > lvl:
            st.balloons()
    except Exception as e:
        st.error(f"Erreur sauvegarde XP : {e}")
        logger.error(f"save_xp failed: {e}")

# --- TASKS ---
# Colonne 1 = tâches actives, colonne 3 = tâches bloquées (⏸)

def load_active_tasks() -> list[str]:
    try:
        data = get_db().worksheet("Tasks").get_all_values()
        return [row[0] for row in data[1:] if len(row) >= 1 and row[0].strip()]
    except Exception as e:
        logger.warning(f"load_active_tasks failed: {e}")
        return []

def load_blocked_tasks() -> list[str]:
    try:
        data = get_db().worksheet("Tasks").get_all_values()
        return [row[2] for row in data[1:] if len(row) >= 3 and row[2].strip()]
    except Exception as e:
        logger.warning(f"load_blocked_tasks failed: {e}")
        return []

def add_task(text: str):
    try:
        ws = get_db().worksheet("Tasks")
        ws.update_cell(len(ws.col_values(1)) + 1, 1, text)
        invalidate_cache()
    except Exception as e:
        st.error(f"Erreur ajout tâche : {e}")

def complete_task(t: str):
    """Valide une tâche active : +XP et suppression."""
    save_xp(10, "Gestion", t)
    _clear_cell_in_col(t, 1)

def block_task(t: str):
    """Déplace une tâche active → colonne bloquée."""
    try:
        ws = get_db().worksheet("Tasks")
        # Trouver la cellule dans col 1
        cell = ws.find(t, in_column=1)
        if cell:
            ws.update_cell(cell.row, 1, "")
        # Ajouter en col 3
        col3 = ws.col_values(3)
        ws.update_cell(len(col3) + 1, 3, t)
        invalidate_cache()
    except Exception as e:
        st.error(f"Erreur blocage tâche : {e}")

def unblock_task(t: str):
    """Remet une tâche bloquée → colonne active."""
    try:
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=3)
        if cell:
            ws.update_cell(cell.row, 3, "")
        col1 = ws.col_values(1)
        ws.update_cell(len(col1) + 1, 1, t)
        invalidate_cache()
    except Exception as e:
        st.error(f"Erreur déblocage tâche : {e}")

def _clear_cell_in_col(t: str, col_idx: int):
    try:
        ws = get_db().worksheet("Tasks")
        cell = ws.find(t, in_column=col_idx)
        if cell:
            ws.update_cell(cell.row, col_idx, "")
        invalidate_cache()
    except Exception as e:
        st.error(f"Erreur suppression : {e}")

def attack_boss(b_name: str, chap: str, dmg: float):
    try:
        db = get_db()
        ws_t = db.worksheet("Boss_Tasks")
        cell = ws_t.find(chap)
        if cell:
            ws_t.delete_rows(cell.row)
        ws_b = db.worksheet("Bosses")
        b_cell = ws_b.find(b_name)
        pv = max(0, float(ws_b.cell(b_cell.row, 4).value) - dmg)
        ws_b.update_cell(b_cell.row, 4, pv)
        invalidate_cache()
    except Exception as e:
        st.error(f"Erreur attaque boss : {e}")

def create_cal_link(title: str) -> str:
    base = "https://www.google.com/calendar/render?action=TEMPLATE"
    now = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0).strftime('%Y%m%dT%H%M00')
    end = (datetime.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0).strftime('%Y%m%dT%H%M00')
    return f"{base}&text={urllib.parse.quote('[RPG] ' + title)}&dates={now}/{end}"


# ==============================================================================
# INITIALISATION
# ==============================================================================

total_xp, lvl, xp_in_level, xp_req_level = 0, 1, 0, 100
current_streak, mana, chaos = 0, 100, 0
rent_paid, salt_paid, anki_done_today, sport_done_today = False, False, False, False
df_raw = pd.DataFrame()

try:
    df_raw = load_sheet_data("Data")

    # --- Fallback anti-crash XP → 0 ---
    if not df_raw.empty:
        total_xp = int(pd.to_numeric(df_raw["XP"], errors='coerce').fillna(0).sum())
        st.session_state['last_known_xp'] = total_xp
    elif 'last_known_xp' in st.session_state:
        total_xp = st.session_state['last_known_xp']

    lvl, xp_in_level, xp_req_level = get_level_data(total_xp)
    current_streak = calculate_streak(df_raw)

    if not df_raw.empty:
        # Mana
        loss = 8 if lvl >= 10 else 10
        last_anki = parse_last_date(df_raw, df_raw['Commentaire'].str.contains("Anki", na=False))
        mana = max(0, 100 - (datetime.now() - last_anki).days * loss) if last_anki else 0

        # Chaos
        last_gestion = parse_last_date(df_raw, df_raw['Type'].str.contains("Gestion", na=False))
        chaos = min(100, (datetime.now() - last_gestion).days * 3) if last_gestion else 100

        # Loyer / Salt
        cur_m = datetime.now().strftime("%Y-%m")
        month_mask = df_raw['Date'].str.contains(cur_m, na=False)
        rent_paid = not df_raw[month_mask & df_raw['Commentaire'].str.contains("Loyer", na=False)].empty
        salt_paid = not df_raw[month_mask & df_raw['Commentaire'].str.contains("Salt", na=False)].empty

        # Anki aujourd'hui ?
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_mask = df_raw['Date'].str.startswith(today_str, na=False)
        anki_done_today = not df_raw[today_mask & df_raw['Commentaire'].str.contains("Anki", na=False)].empty
        sport_done_today = not df_raw[today_mask & df_raw['Commentaire'].str.contains("Workout", na=False)].empty

except Exception as e:
    st.warning(f"⚠️ Chargement échoué : {e}")
    logger.error(f"Init failed: {e}")

# --- SESSION STATE ---
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Dashboard"


# ==============================================================================
# HEADER
# ==============================================================================

c_av, c_main, c_nav = st.columns([0.15, 0.60, 0.25])

with c_av:
    st.image("avatar.png", width=70)
    if st.button("🔄", help="Forcer la synchronisation"):
        invalidate_cache()
        st.rerun()

with c_main:
    st.markdown(
        f"<h3 style='margin:0;'>NIVEAU {lvl} | SELECTA "
        f"<span class='streak-fire'>🔥 {current_streak}</span></h3>",
        unsafe_allow_html=True
    )
    buffs = ""
    if lvl >= 5:
        buffs += "<span class='buff-badge'>🧠 Érudit (+10% Intellect)</span>"
    if lvl >= 10:
        buffs += "<span class='buff-badge'>🛡️ Mémoire d'Or (-8% Decay)</span>"
    if buffs:
        st.markdown(buffs, unsafe_allow_html=True)
    st.caption(f"{int(xp_req_level - xp_in_level)} XP requis pour le niveau {lvl + 1}")

with c_nav:
    n1, n2, n3, n4 = st.columns(4)
    if n1.button("🏰"): st.session_state['current_page'] = "Histoire"; st.rerun()
    if n2.button("🏆"): st.session_state['current_page'] = "HautsFaits"; st.rerun()
    if n3.button("⚔️"): st.session_state['current_page'] = "Donjon"; st.rerun()
    if n4.button("🏠"): st.session_state['current_page'] = "Dashboard"; st.rerun()

st.write("")

def draw_bar(label: str, value: float, css_class: str):
    st.markdown(
        f'<div class="bar-label"><span>{label}</span><span>{int(value)}%</span></div>'
        f'<div class="bar-container"><div class="bar-fill {css_class}" style="width:{value}%"></div></div>',
        unsafe_allow_html=True
    )

xp_pct = (xp_in_level / xp_req_level) * 100 if xp_req_level > 0 else 0
c_b1, c_b2, c_b3 = st.columns(3)
with c_b1: draw_bar("EXPÉRIENCE", xp_pct, "xp-fill")
with c_b2: draw_bar("MÉMOIRE", mana, "mana-fill")
with c_b3: draw_bar("CHAOS", chaos, "chaos-fill")
st.markdown("---")


# ==============================================================================
# PAGES
# ==============================================================================

if st.session_state['current_page'] == "Dashboard":
    col_l, col_r = st.columns([1, 1.1], gap="large")

    with col_l:
        # ── ANKI + SPORT ──────────────────────────────────────────
        st.markdown('<div class="section-header">⚡ ACTIONS DU JOUR</div>', unsafe_allow_html=True)
        a1, a2 = st.columns(2)

        with a1:
            if anki_done_today:
                st.success("✅ Anki fait !")
            else:
                st.markdown('<div class="big-action">', unsafe_allow_html=True)
                if st.button("🧠 ANKI FAIT"):
                    save_xp(20, "Intellect", "Anki")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with a2:
            if sport_done_today:
                st.success("✅ Sport fait !")
            else:
                st.markdown('<div class="big-action-green">', unsafe_allow_html=True)
                if st.button("💪 WORKOUT FAIT"):
                    save_xp(50, "Force", "Workout")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # ── INBOX ─────────────────────────────────────────────────
        st.markdown('<div class="section-header">📥 INBOX</div>', unsafe_allow_html=True)

        with st.form("t_f", clear_on_submit=True):
            nt = st.text_input("Ajouter quelque chose...", label_visibility="collapsed")
            if st.form_submit_button("AJOUTER") and nt.strip():
                add_task(nt)
                st.rerun()

        active_tasks = load_active_tasks()
        for i, t in enumerate(active_tasks):
            cl1, cl2, cl3, cl4, cl5 = st.columns([0.52, 0.12, 0.12, 0.12, 0.12])
            cl1.write(f"• {t}")
            cl2.link_button("📅", create_cal_link(t))
            if cl3.button("✓", key=f"q_{i}", help="Fait !"):
                complete_task(t)
                st.rerun()
            if cl4.button("⏸", key=f"b_{i}", help="Bloqué / en attente"):
                block_task(t)
                st.rerun()
            if cl5.button("×", key=f"d_{i}", help="Supprimer"):
                _clear_cell_in_col(t, 1)
                st.rerun()

        # ── EN ATTENTE (pliée par défaut) ─────────────────────────
        blocked_tasks = load_blocked_tasks()
        if blocked_tasks:
            with st.expander(f"⏸ EN ATTENTE ({len(blocked_tasks)})", expanded=False):
                st.caption("Ces tâches sont bloquées. Clique sur ↩ pour les remettre dans l'inbox quand tu es prêt.")
                for i, t in enumerate(blocked_tasks):
                    bc1, bc2, bc3 = st.columns([0.75, 0.13, 0.12])
                    bc1.markdown(f"<span class='task-blocked'>• {t}</span>", unsafe_allow_html=True)
                    if bc2.button("↩", key=f"ub_{i}", help="Remettre dans l'inbox"):
                        unblock_task(t)
                        st.rerun()
                    if bc3.button("×", key=f"bd_{i}", help="Supprimer"):
                        _clear_cell_in_col(t, 3)
                        st.rerun()

        # ── GESTION ROYAUME ───────────────────────────────────────
        st.markdown('<div class="section-header">🛡️ GESTION DU ROYAUME</div>', unsafe_allow_html=True)
        for name, xp_v, paid, k in [("LOYER", 30, rent_paid, "r"), ("SALT", 30, salt_paid, "s")]:
            if paid:
                st.markdown(f'<div class="gold-banner">✨ {name} RÉGLÉ ✨</div>', unsafe_allow_html=True)
            else:
                if st.button(f"🏠 PAYER {name}", key=f"btn_{k}"):
                    save_xp(xp_v, "Gestion", name)
                    st.rerun()

        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1: st.button("🧹 TRIER", on_click=save_xp, args=(10, "Gestion", "Tri"))
        with c2: st.button("✍️ RÉPONDRE", on_click=save_xp, args=(10, "Gestion", "Réponse"))
        with c3: st.button("📅 AGENDA", on_click=save_xp, args=(10, "Gestion", "Agenda"))

    with col_r:
        # ── GRIMOIRE ──────────────────────────────────────────────
        st.markdown('<div class="section-header">🧠 FORGE DU SAVOIR</div>', unsafe_allow_html=True)
        st.caption("📜 **GRIMOIRE** — choses à apprendre")
        with st.expander("📥 IMPORTER (.txt)"):
            up = st.file_uploader(".txt", type="txt", key="gup")
            if up and st.button("GO"):
                try:
                    ls = [l.strip() for l in up.getvalue().decode().splitlines() if l.strip()]
                    if ls:
                        ws = get_db().worksheet("Tasks")
                        start = len(ws.col_values(2)) + 1
                        cells = ws.range(start, 2, start + len(ls) - 1, 2)
                        for idx, c in enumerate(cells):
                            c.value = ls[idx]
                        ws.update_cells(cells)
                        invalidate_cache()
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur import grimoire : {e}")

        try:
            data = get_db().worksheet("Tasks").get_all_values()
            grimoire = [row[1] for row in data[1:] if len(row) >= 2 and row[1].strip()]
        except Exception:
            grimoire = []

        for i, t in enumerate(grimoire):
            g1, g2 = st.columns([0.85, 0.15])
            g1.write(f"**{t}**")
            if g2.button("✓", key=f"v_{i}"):
                save_xp(30, "Intellect", t)
                _clear_cell_in_col(t, 2)
                st.rerun()


elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    with st.expander("➕ INVOQUER UN BOSS"):
        with st.form("nb"):
            n = st.text_input("Nom")
            d = st.date_input("Date")
            if st.form_submit_button("SCELLER"):
                try:
                    get_db().worksheet("Bosses").append_row([n, d.strftime("%Y-%m-%d"), 0, 100])
                    invalidate_cache()
                    st.rerun()
                except Exception as e:
                    st.error(f"Crée l'onglet 'Bosses' ! ({e})")

    try:
        df_b = load_sheet_data("Bosses")
        for _, b in df_b.iterrows():
            pv = b['PV_Restants']
            try:
                days = (pd.to_datetime(b['Date'], errors='coerce').date() - datetime.now().date()).days
            except Exception:
                days = "?"

            # Alerte deadline proche
            if isinstance(days, int) and days <= 3 and pv > 0:
                st.error(f"🚨 **{b['Nom']}** — deadline dans {days} jour(s) !")

            st.markdown(
                f"## 👹 {b['Nom']} "
                f"<span style='font-size:0.5em;color:#d9534f;margin-left:15px;'>⏳ J-{days}</span>",
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="boss-hp-container">'
                f'<div class="boss-hp-text">{int(pv)}% PV</div>'
                f'<div class="boss-hp-fill" style="width:{pv}%"></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            try:
                df_c = load_sheet_data("Boss_Tasks")
                df_c = df_c[df_c['Boss_Nom'] == b['Nom']]
                if df_c.empty and pv > 0:
                    up = st.file_uploader(f"Munitions {b['Nom']}", type="txt", key=f"u{b['Nom']}")
                    if up:
                        content = [l.strip() for l in up.getvalue().decode().splitlines() if l.strip()]
                        ws_t = get_db().worksheet("Boss_Tasks")
                        ws_t.append_rows([[b['Nom'], c] for c in content])
                        ws_b = get_db().worksheet("Bosses")
                        row = ws_b.find(b['Nom']).row
                        ws_b.update_cell(row, 3, len(content))
                        invalidate_cache()
                        st.rerun()
                elif pv > 0:
                    dmg = 100 / b['Total_Initial']
                    cols = st.columns(2)
                    for i, (_, row) in enumerate(df_c.iterrows()):
                        with cols[i % 2]:
                            if st.button(f"🔥 {row['Chapitre']}", key=f"a{b['Nom']}{i}"):
                                attack_boss(b['Nom'], row['Chapitre'], dmg)
                                save_xp(10, "Combat Boss", b['Nom'])
                                st.rerun()
                else:
                    st.success("VAINCU !")
                    st.button("💎 TRÉSOR (+200 XP)", on_click=save_xp, args=(200, "Victoire", b['Nom']))
            except Exception as e:
                st.warning(f"Erreur tâches boss : {e}")
    except Exception as e:
        st.error(f"Erreur chargement bosses : {e}")

elif st.session_state['current_page'] == "Histoire":
    st.markdown('<div class="section-header">📜 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    if not df_raw.empty:
        for _, r in df_raw.iloc[::-1].head(15).iterrows():
            st.markdown(
                f'<div class="history-card">'
                f'<b>{r["Date"]}</b> | {r["Type"]} | <b>+{r["XP"]} XP</b>'
                f'<br>{r["Commentaire"]}</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("Aucune entrée dans le journal.")

elif st.session_state['current_page'] == "HautsFaits":
    st.markdown('<div class="section-header">🏆 SALLE DES HAUTS FAITS</div>', unsafe_allow_html=True)
    if df_raw.empty:
        st.write("Aucun exploit.")
    else:
        h1, h2, h3 = st.columns(3)
        with h1:
            if lvl >= 2:
                st.markdown('<div class="achievement-card">🎖️<br><b>NOVICE</b><br><small>Niv. 2 atteint</small></div>', unsafe_allow_html=True)
        with h2:
            if df_raw['Commentaire'].str.contains("LOYER", na=False).any():
                st.markdown('<div class="achievement-card">💰<br><b>LOYAL</b><br><small>Loyer payé</small></div>', unsafe_allow_html=True)
        with h3:
            if df_raw['Commentaire'].str.contains("Anki", na=False).sum() >= 10:
                st.markdown('<div class="achievement-card">🔥<br><b>ASSIDU</b><br><small>10 sessions Anki</small></div>', unsafe_allow_html=True)
