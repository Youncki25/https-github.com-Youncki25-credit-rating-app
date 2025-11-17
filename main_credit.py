#streamlit run "/Users/beldjenna/Desktop/Rating Algo/main_credit.py"
# Nous avons le code script.py pour les images des analystes 
# Nous avons API.py pour les appels API des différents données

import streamlit as st
from dataclasses import dataclass
from typing import Optional, List, Dict
import base64, os, uuid

# Streamlit
# main_app.py
import streamlit as st
from ui_streamlit import launch_dashboard

st.set_page_config(
    page_title="Board Analystes",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

launch_dashboard()

