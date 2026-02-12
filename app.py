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

# --- CSS (V44 - DONJON BOSS & MOBILE OPTIMIZED) ---
st.markdown("""
    <style>
    /* SUPPRESSION RADICALE DU HEADER ET DU BLANC */
    header { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 1rem !important; margin-top: -2rem !important; }
    
    .stApp { background-color: #f4f6f9; color: #333; }

    /* BARRES DE STATS */
    .bar-label { font-weight: 700; font-size: 0.8em; color: #555; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .bar-container { background-color: #e9ecef; border-radius: 8px; width: 100%; height: 16px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 8px; transition: width 0.6s ease-in-out; }
    .xp-fill { background: linear-gradient(90deg, #8A2BE2, #9e47ff); }
    .mana-fill { background: linear-gradient(90deg, #0056b3, #007bff); }
    .chaos-fill { background: linear-gradient(90deg, #800000, #a71d2a); }

    /* BARRE DE VIE DU BOSS */
    .boss-hp-container { background-color: #444; border: 2px solid #000; height: 30px; border-radius: 4px; overflow: hidden; margin: 10px 0; position: relative; }
    .boss-hp-fill { background: linear-gradient(90deg, #ff0000, #8b0000); height: 100%; transition: width 0.8s ease-in-out; }
    .boss-hp-text { position: absolute; width: 100%; text-align: center; color: white; font-weight: 900; line-height: 30px; text-shadow: 1px 1px 2px black; }

    .section-header { font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; margin-top: 20px; }
    
    .stButton>button, .stFormSubmitButton>button {
        width: 100%; min-height: 40px; border: 1px solid #bbb; border-radius: 6px;
        background-color: white; color: #333; font-weight: 600; text-transform: uppercase; font-size: 0.85em;
    }
    .stButton>button:hover, .stFormSubmitButton>button:hover { border-color: #333; background-color: #333; color: white; }

    /* MOBILE ADJUST */
    @media (max-width: 768px) {
        .bar-label { font-size: 0.65em; }
        .bar-container { height: 12px; }
        [data-testid="column"] { min-width: 0px !important; }
    }

    .gold-banner { background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728, #fbf5b7); color: #5c4004; padding: 15px; text-align: center; border-radius: 8px; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; border: 2px solid #d4af37; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
def get_db():
    secrets = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(secrets, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_url(secrets["spreadsheet"])

def save_xp(amt, type_s, cmt=""):
    try:
        get_db().worksheet("Data").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), type_s, amt, cmt])
        st.toast(f"+{amt} XP")
    except: pass

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

# --- BOSS ENGINE ---
def load_bosses():
    try: return pd.DataFrame(get_db().worksheet("Bosses").get_all_records())
    except: return pd.DataFrame(columns=["Nom", "Date", "Total_Chapitres", "PV_Restants"])

def update_boss(name, damage):
    ws = get_db().worksheet("Bosses")
    cell = ws.find(name)
    current_pv = float(ws.cell(cell.row, 4).value)
    new_pv = max(0, current_pv - damage)
    ws.update_cell(cell.row, 4, new_pv)

# --- INIT ---
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Dashboard"
total_xp, current_mana, current_chaos, rent_paid, salt_paid, df_full = get_stats()
niveau = 1 + (total_xp // 100)
progress_pct = total_xp % 100

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
def draw_bar(l, v, col):
    st.markdown(f'<div class="bar-label"><span>{l}</span><span>{int(v)}%</span></div><div class="bar-container"><div class="bar-fill {col}" style="width:{v}%"></div></div>', unsafe_allow_html=True)
with c_b1: draw_bar("EXPÉRIENCE", progress_pct, "xp-fill")
with c_b2: draw_bar("MÉMOIRE", current_mana, "mana-fill")
with c_b3: draw_bar("CHAOS", current_chaos, "chaos-fill")
st.markdown("---")

# ==============================================================================
# PAGES
# ==============================================================================

if st.session_state['current_page'] == "Dashboard":
    # (Logique Dashboard V43 identique...)
    st.write("Bienvenue sur le Dashboard. Sélectionne le Donjon pour combattre tes examens.")
    # Note : Insérer ici le reste du code Dashboard précédent pour garder la To-do et la Gestion.

elif st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    
    # 1. AJOUTER UN BOSS
    with st.expander("➕ INVOQUER UN NOUVEAU BOSS (EXAMEN)"):
        with st.form("boss_form", clear_on_submit=True):
            b_name = st.text_input("Nom de l'examen (ex: ORL)")
            b_date = st.date_input("Date de l'examen")
            b_chaps = st.number_input("Nombre total de chapitres", min_value=1)
            if st.form_submit_button("SCELLER LE PACTE"):
                get_db().worksheet("Bosses").append_row([b_name, b_date.strftime("%Y-%m-%d"), b_chaps, 100])
                st.rerun()

    # 2. LISTE DES BOSS ACTIFS
    df_boss = load_bosses()
    if df_boss.empty:
        st.write("Le donjon est calme... pour le moment.")
    else:
        for _, boss in df_boss.iterrows():
            if boss['PV_Restants'] > 0:
                days_left = (datetime.strptime(boss['Date'], "%Y-%m-%d") - datetime.now()).days
                dmg_per_hit = 100 / boss['Total_Chapitres']
                
                st.markdown(f"### 👹 {boss['Nom']}")
                st.caption(f"L'attaque aura lieu le {boss['Date']} (J-{days_left})")
                
                # Barre de vie
                st.markdown(f"""
                <div class="boss-hp-container">
                    <div class="boss-hp-text">{int(boss['PV_Restants'])}% HP</div>
                    <div class="boss-hp-fill" style="width: {boss['PV_Restants']}%"></div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"⚔️ FINIR UN CHAPITRE (-{dmg_per_hit:.1f}% PV)", key=f"atk_{boss['Nom']}"):
                    update_boss(boss['Nom'], dmg_per_hit)
                    save_xp(10, "Combat", f"Attaque Boss: {boss['Nom']}")
                    st.rerun()
            else:
                st.success(f"🏆 {boss['Nom']} a été vaincu !")
                if st.button(f"🎁 RÉCLAMER LE TRÉSOR (+200 XP)", key=f"win_{boss['Nom']}"):
                    save_xp(200, "Victoire", f"Boss {boss['Nom']} terrassé")
                    # Optionnel: Supprimer le boss du sheet ici
                    st.rerun()

# (Pages Histoire et HautsFaits identiques...)
