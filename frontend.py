import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime

# The URL where your FastAPI server is running
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="CKB Tracker", layout="wide")

st.title("🥋 CKB Member Management")

tabs = st.tabs(["Members", "Class Management", "Attendance"])
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
st.header("Current Active Members")

try:
    response = requests.get(f"{BASE_URL}/users/")
    if response.status_code == 200:
        users_data = response.json()
        
        if users_data:
            # 1. Convert everything to a DataFrame (the SELECT * data)
            df = pd.DataFrame(users_data)

            # 2. Let the user choose which columns to see
            # We set a default list, but they can add more (like 'user_uuid' or 'effective_date')
            all_columns = df.columns.tolist()
            default_cols = ["first_name", "last_name", "rank", "last_graded_date"]
            
            selected_cols = st.multiselect(
                "Select columns to display:", 
                options=all_columns, 
                default=default_cols
            )

            # 3. Filter the dataframe based on the selection
            if selected_cols:
                # Format the column names to look nicer (Capitalized)
                display_df = df[selected_cols].copy()
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Please select at least one column to view data.")
        else:
            st.info("No members found.")
            
except Exception as e:
    st.error(f"Failed to load members: {e}")

st.header("Update Member Info")

# 1. Fetch current users for the dropdown
users_resp = requests.get(f"{BASE_URL}/users/")
if users_resp.status_code == 200:
    all_users = users_resp.json()
    user_names = {f"{u['first_name']} {u['last_name']}": u for u in all_users}
    
    selected_name = st.selectbox("Select a member to update", options=["-- Select --"] + list(user_names.keys()))

    if selected_name != "-- Select --":
        user_to_edit = user_names[selected_name]
        
        # 2. Start the Form
        with st.form("edit_member_form"):
            st.write(f"Editing: **{selected_name}**")
            
            # Pre-populate with existing data
            new_first = st.text_input("First Name", value=user_to_edit['first_name'])
            new_last = st.text_input("Last Name", value=user_to_edit['last_name'])
            new_rank = st.selectbox(
                "Rank", 
                ["White", "Blue", "Purple", "Brown", "Black"], 
                index=["White", "Blue", "Purple", "Brown", "Black"].index(user_to_edit['rank'])
            )
            new_nicknames = st.text_input("Nicknames", value=user_to_edit.get('nicknames', ''))
            new_email = st.text_input("Email", value=user_to_edit['email'])
            # new_password_hash = st.text_input("Password Hash", value=user_to_edit['password_hash'])
            
            # THE CRITICAL BUTTON (Must be inside the 'with' block)
            submitted = st.form_submit_button("Update Member & Save History")


        # 3. Handle the Submission (Outside the 'with' block)
        if submitted:
            update_payload = {
                "first_name": new_first,
                "last_name": new_last,
                "rank": new_rank,
                "nicknames": new_nicknames,
                "email": new_email
                # "password_hash": new_password_hash
            }
            
            # Send to FastAPI PUT endpoint
            try:
                put_resp = requests.put(
                    f"{BASE_URL}/users/{user_to_edit['user_uuid']}", 
                    data=update_payload
                )
                
                if put_resp.status_code == 200:
                    st.success(f"Successfully updated {new_first}. Old record archived.")
                    # Optional: clear cache or rerun to refresh the table
                    st.rerun()
                else:
                    st.error(f"Failed to update: {put_resp.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

with tabs[1]:
    st.header("Schedule a New Class")
    with st.form("new_class_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Class Name")
            day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        with c2:
            time = st.text_input("Time (e.g. 18:30)")
            weight = st.number_input("Weighting", value=1.0, step=0.1)
        
        desc = st.text_area("Description")
        
        if st.form_submit_button("Create Class"):
            payload = {"class_name": name, "day": day, "time": time, "weighting": weight, "description": desc}
            res = requests.post(f"{BASE_URL}/classes/", data=payload)
            if res.status_code == 200:
                st.success("Class Added!")
                st.rerun()

    # View existing classes
    st.subheader("Current Timetable")
class_res = requests.get(f"{BASE_URL}/classes/")

if class_res.status_code == 200:
    classes_data = class_res.json()
    
    # Check if we actually have data
    if classes_data:
        df_classes = pd.DataFrame(classes_data)
        
        # Define the columns we want to show
        display_cols = ["day", "time", "class_name", "weighting"]
        
        # Ensure these columns actually exist in the dataframe before filtering
        # (This prevents crashes if the API schema changes)
        existing_cols = [c for c in display_cols if c in df_classes.columns]
        
        st.dataframe(df_classes[existing_cols], use_container_width=True, hide_index=True)
    else:
        # Friendly message instead of a red error box
        st.info("The timetable is currently empty. Add your first class above!")
else:
    st.error("Could not connect to the backend to fetch classes.")

# Inside your tabs logic
with tabs[2]: # Attendance Tab
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
                post_res = requests.post(f"{BASE_URL}/attendance/", data=payload)
                if post_res.status_code == 200:
                    st.toast(f"{m['first_name']} checked in!")


##TODO Class update, get attendance, get attendance by class/date, get attendance by user