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

# --- CSS (V45 - BOSS ARENA) ---
st.markdown("""
    <style>
    header { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 1rem !important; margin-top: -2rem !important; }
    .stApp { background-color: #f4f6f9; color: #333; }

    /* BARRE DE VIE STYLE DARK SOULS */
    .boss-hp-container { background-color: #222; border: 3px solid #000; height: 35px; border-radius: 5px; overflow: hidden; margin: 20px 0; position: relative; box-shadow: 0 0 15px rgba(255,0,0,0.2); }
    .boss-hp-fill { background: linear-gradient(90deg, #ff0000, #990000); height: 100%; transition: width 1s ease-out; }
    .boss-hp-text { position: absolute; width: 100%; text-align: center; color: #fff; font-weight: 900; line-height: 35px; text-transform: uppercase; letter-spacing: 2px; text-shadow: 2px 2px 4px #000; }

    /* BOUTONS D'ATTAQUE */
    .atk-btn > div > button {
        background: linear-gradient(135deg, #ffffff, #f0f0f0) !important;
        color: #444 !important; border: 1px solid #ccc !important;
        font-weight: 700 !important; text-transform: none !important;
        margin-bottom: 10px !important; transition: all 0.3s !important;
    }
    .atk-btn > div > button:hover {
        background: #333 !important; color: #fff !important; transform: scale(1.02); border-color: #000 !important;
    }
    
    .section-header { font-size: 1.1em; font-weight: 800; text-transform: uppercase; color: #444; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-bottom: 15px; }
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
        st.toast(f"⚔️ +{amt} XP")
    except: pass

# --- BOSS ENGINE V45 ---
def load_bosses():
    try: return pd.DataFrame(get_db().worksheet("Bosses").get_all_records())
    except: return pd.DataFrame()

def load_boss_chapters(boss_name):
    try:
        df = pd.DataFrame(get_db().worksheet("Boss_Tasks").get_all_records())
        return df[df['Boss_Nom'] == boss_name]
    except: return pd.DataFrame()

def attack_boss(boss_name, chapter_name, damage):
    db = get_db()
    # 1. Supprimer le chapitre de la liste
    ws_tasks = db.worksheet("Boss_Tasks")
    cell = ws_tasks.find(chapter_name) # Idéalement filtrer par boss_nom aussi
    ws_tasks.delete_rows(cell.row)
    
    # 2. Update PV du Boss
    ws_boss = db.worksheet("Bosses")
    b_cell = ws_boss.find(boss_name)
    current_pv = float(ws_boss.cell(b_cell.row, 4).value)
    new_pv = max(0, current_pv - damage)
    ws_boss.update_cell(b_cell.row, 4, new_pv)

# --- NAVIGATION ---
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Dashboard"

# ==============================================================================
# PAGE : DONJON
# ==============================================================================
if st.session_state['current_page'] == "Donjon":
    st.markdown('<div class="section-header">⚔️ LES PROFONDEURS DU DONJON</div>', unsafe_allow_html=True)
    
    # NAVIGATION RETOUR
    if st.button("🏠 RETOUR AU DASHBOARD"):
        st.session_state['current_page'] = "Dashboard"; st.rerun()

    # CRÉATION DU BOSS
    with st.expander("➕ INVOQUER UN BOSS"):
        with st.form("new_boss", clear_on_submit=True):
            name = st.text_input("Nom de l'Examen")
            date_exa = st.date_input("Date de l'échéance")
            if st.form_submit_button("SCELLER LE DESTIN"):
                get_db().worksheet("Bosses").append_row([name, date_exa.strftime("%Y-%m-%d"), 0, 100])
                st.rerun()

    df_boss = load_bosses()
    
    if df_boss.empty:
        st.write("Le donjon est vide.")
    else:
        for _, boss in df_boss.iterrows():
            b_name = boss['Nom']
            pv = boss['PV_Restants']
            
            st.markdown(f"## 👹 {b_name}")
            
            # Affichage Barre de Vie
            st.markdown(f"""
            <div class="boss-hp-container">
                <div class="boss-hp-text">{int(pv)}% PV</div>
                <div class="boss-hp-fill" style="width: {pv}%"></div>
            </div>
            """, unsafe_allow_html=True)

            # Logique de munitions (Chapitres)
            df_chapters = load_boss_chapters(b_name)
            
            # SI PAS DE CHAPITRES -> MOSTRER UPLOADER
            if df_chapters.empty and pv > 0:
                st.info(f"L'arsenal pour {b_name} est vide. Charge tes munitions (.txt)")
                uploaded_file = st.file_uploader(f"Liste des chapitres pour {b_name}", type="txt", key=f"up_{b_name}")
                if uploaded_file:
                    content = uploaded_file.getvalue().decode("utf-8").splitlines()
                    chapters = [c.strip() for c in content if c.strip()]
                    if chapters:
                        db = get_db()
                        # Enregistrer les chapitres
                        ws_tasks = db.worksheet("Boss_Tasks")
                        for c in chapters:
                            ws_tasks.append_row([b_name, c])
                        # Update Total Initial
                        ws_boss = db.worksheet("Bosses")
                        row_idx = ws_boss.find(b_name).row
                        ws_boss.update_cell(row_idx, 3, len(chapters))
                        st.rerun()

            # SI CHAPITRES DISPONIBLES -> MOSTRER LES ATTAQUES
            elif pv > 0:
                st.write("### 🗡️ CHOISIS TON ATTAQUE")
                cols = st.columns(2) # Deux colonnes de boutons pour mobile
                dmg = 100 / boss['Total_Initial']
                
                for i, row_c in enumerate(df_chapters.iterrows()):
                    chap_name = row_c[1]['Chapitre']
                    with cols[i % 2]:
                        st.markdown('<div class="atk-btn">', unsafe_allow_html=True)
                        if st.button(f"🔥 {chap_name}", key=f"btn_{b_name}_{i}"):
                            attack_boss(b_name, chap_name, dmg)
                            save_xp(10, "Combat", f"Attaque {b_name}: {chap_name}")
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            
            # SI MORT -> RÉCOMPENSE
            else:
                st.success(f"🔥 {b_name} A ÉTÉ TERRASSÉ !")
                if st.button(f"💎 RÉCLAMER LE TRÉSOR (+200 XP)", key=f"win_{b_name}"):
                    save_xp(200, "Victoire", f"Boss {b_name} vaincu")
                    # Nettoyage
                    db = get_db()
                    ws_boss = db.worksheet("Bosses")
                    ws_boss.delete_rows(ws_boss.find(b_name).row)
                    st.rerun()
