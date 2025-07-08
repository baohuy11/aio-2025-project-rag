import streamlit as st
from dotenv import load_dotenv
import requests
import time

st.set_page_config(
    page_title="Local RAG Chatbot",
    layout="wide",
    initial_sidebar_state="expanded"
)
