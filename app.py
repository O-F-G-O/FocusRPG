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
