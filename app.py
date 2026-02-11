import streamlit as st
import pandas as pd
import gspread
import time
import random
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION SOBRE ---
st.set_page_config(page_title="Dashboard", page_icon="⚫", layout="wide")

# --- CSS MINIMALISTE (STYLE SUISSE) ---
st.markdown("""
    <style>
    /* Fond général plus doux */
    .stApp {
        background-color: #FAFAFA;
    }
    
    /* Style des boutons : Fin et élégant (Outline) */
    .stButton>button {
        width: 100%;
        border: 1px solid #444;
        border-radius: 4px;
        background-color: white;
        color: #333;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #333;
        color: white;
        border-color: #333;
    }

    /* Le Timer style "Horloge Digitale" */
    .digital-clock {
        font-family: 'Courier New', Courier, monospace;
        font-size: 80px;
        font-weight: bold;
        color: #333;
        text-align: center;
        letter-spacing: -2px;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    /* Zone To-Do (Carte blanche) */
    .todo-container {
        padding: 10px;
        border-left: 3px solid #333;
    }
    
    /* Titres sobres */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR (IDENTIQUE V4) ---
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
        ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), type_stat, xp_amount, comment])
        st.toast(f"Sauvegardé. (+{xp_amount})")
    except Exception as e:
        st.error(f"Erreur : {e}")

def load_data():
    try:
        ws = get_worksheet()
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])
        return df
    except:
        return pd.DataFrame(columns=["Date", "Type", "XP", "Commentaire"])

# --- DATA SPORT (TEXTE SIMPLE) ---
SEANCES_GYM = {
    "A": "**SEANCE A (Barres)**\n\nSquat (3x8)\nDéveloppé Couché (3x10)\nRowing Barre (3x10)\nPresse cuisses (3x12)\nGainage (3x1min)",
    "B": "**SEANCE B (Haltères)**\n\nFentes (3x12)\nDéveloppé Militaire (3x10)\nSoulevé de terre (3x10)\nBiceps/Triceps (3x12)\nAbdos (3x20)",
    "C": "**SEANCE C (Machines)**\n\nPresse (4x10)\nTirage Vertical (4x10)\nChest Press (4x10)\nLeg Extension (3x15)\nElliptique (10min)",
    "D": "**SEANCE D (Hybride)**\n\nGoblet Squat (3x12)\nPompes (3xMax)\nTirage Câble (3x12)\nKettlebell Swing (3x15)\nPlanche (3x45s)"
}

# --- INIT SESSION ---
if 'todos' not in st.session_state: st.session_state.todos = ["Vérifier Agenda", "Répondre Mails"]

# --- CALCUL NIVEAU (DISCRET) ---
df = load_data()
if not df.empty and "XP" in df.columns:
    df["XP"] = pd.to_numeric(df["XP"], errors='coerce').fillna(0)
    total_xp = df["XP"].sum()
else:
    total_xp = 0
niveau = 1 + (int(total_xp) // 100)

# --- LAYOUT ---
col_sidebar, col_main = st.columns([1, 2.5], gap="large")

# === COLONNE GAUCHE : TO-DO LIST (STYLE NOTEPAD) ===
with col_sidebar:
    st.caption(f"NIVEAU {niveau} • {int(total_xp)} XP")
    st.progress((int(total_xp) % 100) / 100)
    st.write("---")
    
    st.markdown("####
