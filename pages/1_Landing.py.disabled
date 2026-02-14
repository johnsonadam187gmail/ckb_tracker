import streamlit as st
import requests
import time
from datetime import datetime
from pathlib import Path

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="CKB Tracker - Welcome",
    page_icon="🏋️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# Function to load CSS files
def load_css():
    """Load custom CSS files for styling"""
    css_files = [
        "assets/style.css",
        "assets/dark-theme.css"
        if st.session_state.get("theme", "dark") == "dark"
        else "assets/light-theme.css",
    ]

    css_content = ""
    for css_file in css_files:
        # Go up one directory level since we're in pages/
        css_path = Path(__file__).parent.parent / css_file
        if css_path.exists():
            with open(css_path) as f:
                css_content += f.read()

    # Apply theme data attribute
    theme = st.session_state.get("theme", "dark")
    css_content = f"""
    <style>
    :root {{
        data-theme: "{theme}";
    }}
    {css_content}
    </style>
    """

    st.markdown(css_content, unsafe_allow_html=True)


# Initialize theme in session state
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Clear any existing session states for fresh start
for key in [
    "kiosk_mode",
    "kiosk_expires",
    "teacher_token",
    "teacher_info",
    "selected_user",
    "current_student",
]:
    if key in st.session_state:
        del st.session_state[key]

# Load CSS
load_css()

# --- MAIN PAGE ---
st.title("🏋️ CKB Tracker")
st.markdown(
    "<h2 style='text-align: center;'>Mat-Side Check-In</h2>", unsafe_allow_html=True
)
st.markdown("---")

# Two large buttons side by side
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.subheader("🧑‍🎓 Students")
    st.write("Check in for class")

    # PIN entry
    pin = st.text_input(
        "Enter Gym PIN",
        type="password",
        max_chars=6,
        label_visibility="collapsed",
        placeholder="Enter 4-6 digit PIN",
        key="student_pin",
    )

    if st.button(
        "Enter", type="primary", use_container_width=True, key="student_enter"
    ):
        if len(pin) < 4:
            st.error("PIN must be at least 4 digits")
        elif not pin.isdigit():
            st.error("PIN must be numbers only")
        else:
            # Verify PIN via API
            try:
                response = requests.post(
                    f"{BASE_URL}/kiosk/verify-pin", json={"pin": pin}, timeout=5
                )
                if response.status_code == 200:
                    st.session_state.kiosk_mode = True
                    st.session_state.kiosk_expires = time.time() + 300  # 5 minutes
                    st.switch_page("Attendance.py")
                else:
                    st.error("Invalid PIN")
            except Exception as e:
                st.error("Error connecting to server")

    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.subheader("👨‍🏫 Teachers")
    st.write("Manage class attendance")

    if st.button(
        "Teacher Sign In",
        type="secondary",
        use_container_width=True,
        key="teacher_signin",
    ):
        st.switch_page("pages/4_Teacher.py")

    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("CKB Martial Arts Tracker © 2026")
