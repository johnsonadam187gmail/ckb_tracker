import streamlit as st
import requests
import pandas as pd
from datetime import date


BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Analytics", layout="wide")
st.title("📈 Analytics")