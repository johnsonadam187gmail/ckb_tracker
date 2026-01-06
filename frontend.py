import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime

# The URL where your FastAPI server is running
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="CKB Tracker", layout="wide")

st.title("🥋 CKB Member Management")

# --- SIDEBAR: ADD NEW MEMBER ---
st.sidebar.header("Add New Member")
with st.sidebar.form("add_user_form"):
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Email")
    nicknames = st.text_input("Nicknames (Optional)")
    rank = st.selectbox("Current Rank", ["White", "Blue", "Purple", "Brown", "Black"])
    last_grade = st.date_input("Last Grading Date", value=date.today())
    comments = st.text_area("Comments")
    
    # Image Upload
    uploaded_file = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"])
    
    submit_button = st.form_submit_button("Create Member")

if submit_button:
    # Prepare the form data for FastAPI
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "nicknames": nicknames,
        "rank": rank,
        "last_grade_date": str(last_grade), # Convert date to string for the form
        "comments": comments
    }
    
    # Handle the file upload part
    files = None
    if uploaded_file:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

    try:
        # We send a POST request to your FastAPI /users/ endpoint
        response = requests.post(f"{BASE_URL}/users/", data=payload, files=files)
        
        if response.status_code == 200:
            st.sidebar.success(f"Successfully added {first_name}!")
        else:
            st.sidebar.error(f"Error: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.sidebar.error(f"Could not connect to Backend: {e}")

# --- MAIN AREA: VIEW MEMBERS ---

st.header("Daily Attendance")
    
# 1. Date and Class Selection
col1, col2 = st.columns(2)
with col1:
    selected_date = st.date_input("Training Date", value=datetime.now())
with col2:
    class_res = requests.get(f"{BASE_URL}/classes/")
    classes = class_res.json() if class_res.status_code == 200 else []
    class_options = {f"{c['class_name']} ({c['time']})": c['id'] for c in classes}
    selected_class_name = st.selectbox("Select Class", options=list(class_options.keys()))

if selected_class_name:
    class_id = class_options[selected_class_name]
    
# 2. Get Active Members to check in
    members_res = requests.get(f"{BASE_URL}/users/") # Only returns is_current=True
    members = members_res.json()
    
    st.subheader("Class Attendance")
    for m in members:
        col_name, col_btn = st.columns([3, 1])
        col_name.write(f"**{m['first_name']} {m['last_name']}** ({m['rank']})")
        
        if col_btn.button("Check In", key=f"checkin_{m['user_uuid']}"):
            payload = {
                "user_uuid": m['user_uuid'],
                "class_id": class_id,
                "attendance_date": str(selected_date)
            }
            
            try:
                post_res = requests.post(f"{BASE_URL}/attendance/", data=payload)
                
                if post_res.status_code == 200:
                    st.toast(f"✅ {m['first_name']} checked in successfully!", icon="🥋")
                
                elif post_res.status_code == 400:
                    # This catches the UniqueConstraint violation from the backend
                    st.warning(f"⚠️ {m['first_name']} is already checked into this class.")
                
                else:
                    st.error(f"Error: {post_res.json().get('detail', 'Unknown error occurred')}")
            
            except Exception as e:
                st.error(f"Connection failed: {e}")
