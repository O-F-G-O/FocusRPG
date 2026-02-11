import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="Mon RPG Vie", page_icon="⚔️", layout="centered")

# CSS pour masquer le header rouge moche et styliser
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    .big-timer {
        font-size: 40px;
        font-weight: bold;
        color: #FF4B4B;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR (ON NE TOUCHE PAS) ---
def get_worksheet():
    secrets = st.secrets["connections"]["gsheets"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_url = secrets["spreadsheet"]
    sh = client.open_by_url(sheet_url)
    return sh.worksheet("Data")

def save_action(xp_amount, type_stat, comment=""):
    try:
        ws = get_worksheet()
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            type_stat, 
            xp_amount, 
            comment
        ])
        st.toast(f"✅ Validé ! (+{xp_amount} XP)", icon="✨")
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

def load_data():
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])
        return df
    except:
        return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])

# --- CONTENU SPORT (LES 4 SÉANCES) ---
SEANCES_GYM = {
    "A": "🏋️‍♂️ **Full Body A (Barres)**\n- Squat : 3x8\n- Développé Couché : 3x10\n- Tirage Buste Penché (Rowing) : 3x10\n- Presse à cuisses : 3x12\n- Gainage : 3x1 min",
    "B": "🔥 **Full Body B (Haltères)**\n- Fentes marchées : 3x12 pas\n- Développé Militaire (Épaules) : 3x10\n- Soulevé de terre jambes tendues : 3x10\n- Curl Biceps + Extension Triceps : 3x12 (SuperSet)\n- Abdos (Crunchs) : 3x20",
    "C": "⚙️ **Full Body C (Machines)**\n- Presse à cuisses : 4x10\n- Tirage Vertical (Dos) : 4x10\n- Chest Press (Pecs) : 4x10\n- Leg Extension : 3x15\n- Elliptique : 10 min intensif",
    "D": "⚡ **Full Body D (Hybride)**\n- Goblet Squat (Kettlebell) : 3x12\n- Pompes : 3xMax\n- Tirage Horizontal Câble : 3x12\n- Kettlebell Swing : 3x15\n- Planche dynamique : 3x45 sec"
}

# --- INITIALISATION SESSION (POUR LA TO-DO LIST) ---
if 'todos' not in st.session_state:
    st.session_state.todos = ["Vérifier Agenda", "Répondre Mails", "Faire Anki"] # Tâches par défaut
if 'timer_active' not in st.session_state:
    st.session_state.timer_active = False

# --- CALCUL NIVEAU ---
df = load_data()
if not df.empty and "XP" in df.columns:
    df["XP"] = pd.to_numeric(df["XP"], errors='coerce').fillna(0)
    total_xp = df["XP"].sum()
    xp_intellect = df[df["Type"] == "Intellect"]["XP"].sum()
    xp_force = df[df["Type"] == "Force"]["XP"].sum()
    xp_gestion = df[df["Type"] == "Gestion"]["XP"].sum()
else:
    total_xp, xp_intellect, xp_force, xp_gestion = 0, 0, 0, 0

niveau = 1 + (int(total_xp) // 100)
xp_restant = 100 - (int(total_xp) % 100)

# --- HEADER PERSONNAGE ---
col1, col2 = st.columns([1, 3])
with col1:
    st.image("https://api.dicebear.com/7.x/notionists/svg?seed=Felix", width=90)
with col2:
    st.metric(label=f"Héros Niveau {niveau}", value=f"{int(total_xp)} XP", delta=f"Prochain niveau : {xp_restant} XP")
    st.progress((int(total_xp) % 100) / 100)

st.divider()

# --- ONGLETS ---
tab_sport, tab_admin, tab_stats = st.tabs(["💪 Sport & Forme", "✅ To-Do & Gestion", "📊 Historique"])

# === TAB 1 : SPORT ===
with tab_sport:
    mode = st.radio("Mode :", ["🏠 Maison (20min)", "🏋️‍♂️ Salle de Sport (1h)"], horizontal=True)
    
    if "Maison" in mode:
        st.info("Objectif : 20 minutes non-stop. Pas de téléphone.")
        if st.button("⏱️ Lancer le Timer 20 min"):
            st.session_state.timer_active = True
        
        if st.session_state.timer_active:
            # Code simple pour le timer visuel
            progress_bar = st.progress(0)
            status_text = st.empty()
            # Pour la démo, on accélère le temps (enlève le /60 pour vrai temps)
            for i in range(100):
                time.sleep(0.01) # C'est juste visuel ici pour l'exemple immédiat
                progress_bar.progress(i + 1)
            st.success("Séance terminée ! Bien joué.")
            st.session_state.timer_active = False
            
        st.write("---")
        if st.button("Valider séance Maison (+20 XP)"):
            save_action(20, "Force", "Séance Maison 20min")
            st.rerun()

    else: # Mode Salle
        st.info("Objectif : Compléter une séance. Clique pour générer.")
        if st.button("🎲 Propose-moi une séance"):
            seance_id = random.choice(list(SEANCES_GYM.keys()))
            st.session_state.current_workout = SEANCES_GYM[seance_id]
        
        if 'current_workout' in st.session_state:
            st.warning(st.session_state.current_workout)
            if st.button("J'ai fini cette séance (+50 XP)"):
                save_action(50, "Force", "Séance Salle Full Body")
                del st.session_state.current_workout # On efface après validation
                st.rerun()

# === TAB 2 : ADMIN & TO-DO ===
with tab_admin:
    st.write("### 📝 Ma liste de tâches")
    
    # Ajouter une tâche
    col_add, col_btn = st.columns([3, 1])
    with col_add:
        new_task = st.text_input("Nouvelle tâche", placeholder="Ex: Payer loyer...", label_visibility="collapsed")
    with col_btn:
        if st.button("Ajouter"):
            if new_task:
                st.session_state.todos.append(new_task)
                st.rerun()

    # Afficher la liste
    if not st.session_state.todos:
        st.caption("Rien à faire ! Profite ou ajoute des trucs.")
    
    # On itère sur une copie de la liste pour pouvoir supprimer sans bug
    for i, task in enumerate(st.session_state.todos):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"⬜ {task}")
        with c2:
            if st.button("Fait (+10 XP)", key=f"todo_{i}"):
                save_action(10, "Gestion", f"Tâche : {task}")
                st.session_state.todos.pop(i)
                st.rerun()

    st.divider()
    st.write("### 🧠 Entretien Cerveau")
    if st.button("📚 Session Anki terminée (+15 XP)"):
        save_action(15, "Intellect", "Anki")
        st.rerun()

# === TAB 3 : STATS & HISTO ===
with tab_stats:
    st.subheader("Journal de bord")
    st.dataframe(df.tail(10).iloc[::-1], use_container_width=True, hide_index=True)
    
    if total_xp > 0:
        st.write("### Répartition")
        st.bar_chart({"Intellect": xp_intellect, "Force": xp_force, "Gestion": xp_gestion})
