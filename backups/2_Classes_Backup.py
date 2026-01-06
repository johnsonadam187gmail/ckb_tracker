import streamlit as st
import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Class Management", layout="wide")
st.title("📅 Class Schedule & Management")

# --- 1. INITIALIZE & FETCH DATA ---
gyms, types, classes_data = [], [], []

try:
    gym_res = requests.get(f"{BASE_URL}/gyms/")
    type_res = requests.get(f"{BASE_URL}/class-types/")
    class_res = requests.get(f"{BASE_URL}/classes/")

    if gym_res.status_code == 200: gyms = gym_res.json()
    if type_res.status_code == 200: types = type_res.json()
    if class_res.status_code == 200: classes_data = class_res.json()
except Exception as e:
    st.error(f"Backend Connection Error: {e}")

# Map names to IDs safely
gym_options = {g['name']: g['id'] for g in gyms}
type_options = {t['name']: t['id'] for t in types}

# --- SECTION 1: CREATE NEW CLASS ---
with st.expander("➕ Create New Class"):
    if not gym_options or not type_options:
        st.warning("⚠️ You must add at least one Gym Location and one Class Type before creating a class.")
    else:
        with st.form("create_class_form"):
            c_name = st.text_input("Class Name (e.g., Morning Gi)")
            c_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            c_time = st.text_input("Time (e.g., 06:30)")
            c_weight = st.number_input("Attendance Weighting", min_value=0.0, value=1.0, step=0.1)
            c_gym = st.selectbox("Location", options=list(gym_options.keys()))
            c_type = st.selectbox("Class Type", options=list(type_options.keys()))
            c_desc = st.text_area("Description")
            submit_create = st.form_submit_button("Add to Schedule")

        if submit_create:
            payload = {
                "class_name": c_name, "day": c_day, "time": c_time,
                "weighting": c_weight, "gym_id": gym_options[c_gym],
                "class_type_id": type_options[c_type], "description": c_desc
            }
            # Use json=payload for FastAPI compatibility
            res = requests.post(f"{BASE_URL}/classes/", json=payload)
            if res.status_code == 200:
                st.success(f"Class '{c_name}' created!")
                st.rerun()

# --- SECTION 2: VIEW ACTIVE CLASSES ---
st.header("Current Timetable")
if classes_data:
    df = pd.DataFrame(classes_data)
    # Updated to 2026 width='stretch' parameter
    st.dataframe(df[["class_name", "day", "time", "weighting"]], width='stretch', hide_index=True)
else:
    st.info("No active classes found in the database.")

# --- SECTION 3: MODIFY / UPDATE CLASS (SCD TYPE 2) ---
st.header("Update Class Details")
if classes_data:
    class_map = {f"{c['class_name']} ({c['day']} @ {c['time']})": c for c in classes_data}
    selected_label = st.selectbox("Select Class to Edit", options=["-- Select --"] + list(class_map.keys()))
    
    if selected_label != "-- Select --":
        selected_class_obj = class_map[selected_label]
        
        with st.form("update_class_form"):
            st.info("Updating creates a new version for future attendance while archiving the old one.")
            u_name = st.text_input("Class Name", value=selected_class_obj['class_name'])
            u_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], 
                                 index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(selected_class_obj['day']))
            u_time = st.text_input("Time", value=selected_class_obj['time'])
            u_weight = st.number_input("Weighting", value=selected_class_obj['weighting'])
            submit_update = st.form_submit_button("Save Changes (New Version)")

        if submit_update:
            update_payload = {
                "class_name": u_name, "day": u_day, "time": u_time, "weighting": u_weight,
                "gym_id": selected_class_obj['gym_id'], "class_type_id": selected_class_obj['class_type_id']
            }
            res = requests.put(f"{BASE_URL}/classes/{selected_class_obj['class_uuid']}", json=update_payload)
            if res.status_code == 200:
                st.success("Class version updated successfully!")
                st.rerun()