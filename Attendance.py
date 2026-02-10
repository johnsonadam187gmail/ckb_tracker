import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
from pathlib import Path

# The URL where your FastAPI server is running
BASE_URL = "http://127.0.0.1:8000"

# Configure page
st.set_page_config(
    page_title="CKB Tracker",
    layout="wide",
    page_icon="🥋",
    initial_sidebar_state="expanded",
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
        css_path = Path(__file__).parent / css_file
        if css_path.exists():
            with open(css_path) as f:
                css_content += f.read()

    # Apply theme data attribute to root
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

# Initialize photo capture state
if "show_camera" not in st.session_state:
    st.session_state.show_camera = False
if "captured_photo" not in st.session_state:
    st.session_state.captured_photo = None

# Load CSS
load_css()

st.title("🥋 CKB Member Management")

# --- SIDEBAR: THEME TOGGLE ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    # Theme toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("**Theme Mode**")
    with col2:
        # Theme toggle button
        current_theme = st.session_state.get("theme", "dark")
        if st.button(
            "🌙" if current_theme == "dark" else "☀️",
            key="theme_toggle",
            help="Toggle theme",
        ):
            st.session_state.theme = "light" if current_theme == "dark" else "dark"
            st.rerun()

    st.divider()

# --- SIDEBAR: ADD NEW MEMBER ---
st.sidebar.header("Add New Member")

# Photo Capture Section (OUTSIDE the form to allow buttons)
st.sidebar.markdown("### 📸 Profile Photo")
st.sidebar.markdown("*Optional - Add a profile photo*")

# Photo input method selection
photo_method = st.sidebar.radio(
    "Choose photo method:",
    ["Take Photo (Camera)", "Upload File", "No Photo"],
    key="photo_method",
)

uploaded_file = None

if photo_method == "Take Photo (Camera)":
    # Toggle button for camera
    if not st.session_state.show_camera:
        if st.sidebar.button(
            "📷 Open Camera", key="open_camera", use_container_width=True
        ):
            st.session_state.show_camera = True
            st.rerun()
    else:
        # Show the camera input
        camera_photo = st.sidebar.camera_input(
            "Take a photo",
            help="Click the camera button to capture",
            key="camera_input",
        )
        if camera_photo:
            st.session_state.captured_photo = camera_photo
            st.session_state.show_camera = False
            st.rerun()

        # Button to close camera without taking photo
        if st.sidebar.button("❌ Cancel", key="cancel_camera"):
            st.session_state.show_camera = False
            st.rerun()

    # Use captured photo if available
    if st.session_state.captured_photo:
        uploaded_file = st.session_state.captured_photo
        st.sidebar.success("Photo captured!")

elif photo_method == "Upload File":
    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload Profile Picture",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG (Max 5MB)",
    )
    # Clear any previously captured photo
    if st.session_state.captured_photo:
        st.session_state.captured_photo = None

else:
    # No photo selected
    uploaded_file = None
    if st.session_state.captured_photo:
        st.session_state.captured_photo = None

# Preview the photo if captured/uploaded
if uploaded_file:
    st.sidebar.image(uploaded_file, width=200)
    st.sidebar.caption("Photo ready for upload")
    if st.sidebar.button("❌ Clear Photo", key="clear_photo"):
        st.session_state.captured_photo = None
        st.session_state.show_camera = False
        st.rerun()

st.sidebar.markdown("---")

# Now the form (without camera inside it)
with st.sidebar.form("add_user_form"):
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Email")

    # Password fields (required)
    password = st.text_input(
        "Password", type="password", help="Minimum 6 characters required"
    )
    confirm_password = st.text_input("Confirm Password", type="password")

    nicknames = st.text_input("Nicknames (Optional)")
    rank = st.selectbox("Current Rank", ["White", "Blue", "Purple", "Brown", "Black"])
    last_grade = st.date_input("Last Grading Date", value=date.today())
    comments = st.text_area("Comments")

    submit_button = st.form_submit_button("Create Member")

if submit_button:
    # Validate required fields
    if not first_name or not last_name or not email:
        st.sidebar.error("❌ First Name, Last Name, and Email are required!")
    elif not password or not confirm_password:
        st.sidebar.error("❌ Password is required!")
    elif len(password) < 6:
        st.sidebar.error("❌ Password must be at least 6 characters!")
    elif password != confirm_password:
        st.sidebar.error("❌ Passwords do not match!")
    else:
        # Prepare the form data for FastAPI
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
            "nicknames": nicknames,
            "rank": rank,
            "last_grade_date": str(last_grade),  # Convert date to string for the form
            "comments": comments,
        }

        # Handle the file upload part
        files = None
        if uploaded_file:
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type,
                )
            }

        try:
            # We send a POST request to your FastAPI /users/ endpoint
            response = requests.post(f"{BASE_URL}/users/", data=payload, files=files)

            if response.status_code == 200:
                st.sidebar.success(f"✅ Successfully added {first_name}!")
                # Clear the captured photo after successful creation
                st.session_state.captured_photo = None
                st.session_state.show_camera = False
                st.rerun()
            else:
                st.sidebar.error(
                    f"❌ Error: {response.json().get('detail', 'Unknown error')}"
                )
        except Exception as e:
            st.sidebar.error(f"⚠️ Could not connect to Backend: {e}")

# --- MAIN AREA: VIEW MEMBERS ---

st.header("Daily Attendance")

# 1. Date and Class Selection
col1, col2 = st.columns(2)
with col1:
    selected_date = st.date_input("Training Date", value=datetime.now())
with col2:
    class_res = requests.get(f"{BASE_URL}/classes/")
    classes = class_res.json() if class_res.status_code == 200 else []
    class_options = {f"{c['class_name']} ({c['time']})": c["id"] for c in classes}
    selected_class_name = st.selectbox(
        "Select Class", options=list(class_options.keys())
    )

if selected_class_name:
    class_id = class_options[selected_class_name]

    # 2. Get Active Members to check in
    members_res = requests.get(f"{BASE_URL}/users/")  # Only returns is_current=True
    members = members_res.json()

    st.subheader("Class Attendance")
    for m in members:
        # Create columns for photo, info, and button
        cols = st.columns([0.8, 3, 1])

        # Photo column
        with cols[0]:
            if m.get("profile_image_url"):
                st.image(m["profile_image_url"], width=60)
            else:
                st.markdown("👤", help="No photo")

        # Name and info column
        with cols[1]:
            st.write(f"**{m['first_name']} {m['last_name']}** ({m['rank']})")

        # Button column
        with cols[2]:
            if st.button("Check In", key=f"checkin_{m['user_uuid']}"):
                payload = {
                    "user_uuid": m["user_uuid"],
                    "class_id": class_id,
                    "attendance_date": str(selected_date),
                }

                try:
                    post_res = requests.post(f"{BASE_URL}/attendance/", data=payload)

                    if post_res.status_code == 200:
                        st.toast(
                            f"✅ {m['first_name']} checked in successfully!", icon="🥋"
                        )

                    elif post_res.status_code == 400:
                        # This catches the UniqueConstraint violation from the backend
                        st.warning(
                            f"⚠️ {m['first_name']} is already checked into this class."
                        )

                    else:
                        st.error(
                            f"Error: {post_res.json().get('detail', 'Unknown error occurred')}"
                        )

                except Exception as e:
                    st.error(f"Connection failed: {e}")
