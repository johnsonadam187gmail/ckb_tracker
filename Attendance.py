import streamlit as st
import pandas as pd
import requests
import time
from datetime import date, datetime, timedelta
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


# ===== KIOSK MODE =====
def render_kiosk_mode():
    """Student self check-in interface (kiosk mode)"""

    # Check for timeout
    if st.session_state.get("kiosk_expires"):
        time_remaining = int(st.session_state.kiosk_expires - time.time())
        if time_remaining <= 0:
            st.session_state.pop("kiosk_mode", None)
            st.session_state.pop("kiosk_expires", None)
            st.session_state.pop("current_student", None)
            st.session_state.pop("selected_user", None)
            st.switch_page("pages/1_Landing.py")

    # Header with timeout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📝 Student Check-In")
    with col2:
        time_remaining = int(st.session_state.kiosk_expires - time.time())
        if time_remaining < 60:
            st.error(f"⏰ Expires in {time_remaining}s")
        else:
            st.info(f"⏰ {time_remaining // 60}m remaining")

    st.markdown("---")

    # Class & Date Selection
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Date", value=date.today(), key="kiosk_date")
    with col2:
        try:
            classes_response = requests.get(f"{BASE_URL}/classes/", timeout=5)
            classes = classes_response.json()
            selected_class = st.selectbox(
                "Select Class",
                classes,
                format_func=lambda x: x["class_name"],
                key="kiosk_class",
            )
        except:
            st.error("Error loading classes")
            return

    # Show search interface or confirmation
    if "current_student" in st.session_state:
        show_check_in_confirmation(selected_class, selected_date)
    elif "selected_user" in st.session_state:
        show_user_selection(selected_class, selected_date)
    else:
        show_user_search(selected_class, selected_date)

    # Exit button
    st.markdown("---")
    if st.button("⬅️ Exit Student Mode", type="secondary", use_container_width=True):
        st.session_state.pop("kiosk_mode", None)
        st.session_state.pop("kiosk_expires", None)
        st.session_state.pop("current_student", None)
        st.session_state.pop("selected_user", None)
        st.switch_page("pages/1_Landing.py")


def show_user_search(selected_class, selected_date):
    """Search interface for finding self"""
    st.subheader("Find Yourself")
    st.write("Search by your first or last name")

    search_query = st.text_input(
        "Search",
        placeholder="Type at least 2 letters...",
        label_visibility="collapsed",
        key="user_search",
    )

    if search_query and len(search_query) >= 2:
        try:
            response = requests.get(
                f"{BASE_URL}/users/search", params={"query": search_query}, timeout=5
            )

            if response.status_code == 200:
                users = response.json()

                if users:
                    st.write(f"Found {len(users)} match(es):")

                    for user in users:
                        col1, col2, col3 = st.columns([1, 3, 1])

                        with col1:
                            if user.get("profile_image_url"):
                                st.image(user["profile_image_url"], width=60)
                            else:
                                st.write("👤")

                        with col2:
                            st.write(f"**{user['first_name']} {user['last_name']}**")
                            st.write(f"📧 {user['email']}")

                        with col3:
                            if st.button(
                                "Select",
                                key=f"select_{user['user_uuid']}",
                                type="primary",
                            ):
                                st.session_state.selected_user = user
                                st.rerun()
                else:
                    st.info("No matches found. Try a different search.")

        except Exception as e:
            st.error("Error searching users")


def show_user_selection(selected_class, selected_date):
    """Show selected user and confirm check-in"""
    user = st.session_state.selected_user

    st.success(f"Selected: {user['first_name']} {user['last_name']}")

    # Check for existing check-in
    try:
        response = requests.get(
            f"{BASE_URL}/attendance/user/{user['user_uuid']}", timeout=5
        )

        if response.status_code == 200:
            attendance_records = response.json()
            # Check if already checked in for this class/date
            existing = [
                r
                for r in attendance_records
                if r.get("class_id") == selected_class["id"]
                and r.get("attendance_date") == str(selected_date)
            ]

            if existing:
                status = existing[0].get("status", "confirmed")
                if status == "confirmed":
                    st.warning("You're already confirmed for this class!")
                    if st.button("Done", type="primary", use_container_width=True):
                        st.session_state.pop("selected_user", None)
                        st.rerun()
                    return
                elif status == "pending":
                    st.info(
                        "You have a pending check-in. Waiting for teacher confirmation."
                    )
                    st.session_state.current_student = user
                    st.session_state.check_in_status = "pending"
                    if st.button(
                        "View Status", type="primary", use_container_width=True
                    ):
                        st.rerun()
                    return
    except:
        pass

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Check In Now", type="primary", use_container_width=True):
            create_pending_check_in(user, selected_class, selected_date)
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.pop("selected_user", None)
            st.rerun()


def create_pending_check_in(user, selected_class, selected_date):
    """Create PENDING attendance record"""
    try:
        response = requests.post(
            f"{BASE_URL}/attendance/check-in",
            json={
                "user_uuid": user["user_uuid"],
                "class_id": selected_class["id"],
                "attendance_date": str(selected_date),
            },
            timeout=5,
        )

        if response.status_code == 200:
            st.session_state.current_student = user
            st.session_state.check_in_status = "pending"
            st.rerun()
        elif response.status_code == 400:
            data = response.json()
            if "already" in data.get("detail", "").lower():
                st.warning("You already checked in for this class!")
        else:
            st.error("Error checking in. Please try again.")

    except Exception as e:
        st.error("Error connecting to server")


def show_check_in_confirmation(selected_class, selected_date):
    """Show check-in status and allow cancellation"""
    user = st.session_state.current_student

    st.success(f"✅ Welcome, {user['first_name']}!")

    # Check current status from server
    try:
        response = requests.get(
            f"{BASE_URL}/attendance/user/{user['user_uuid']}", timeout=5
        )

        if response.status_code == 200:
            attendance_records = response.json()
            # Find record for this class/date
            attendance = None
            for r in attendance_records:
                if r.get("class_id") == selected_class["id"] and r.get(
                    "attendance_date"
                ) == str(selected_date):
                    attendance = r
                    break

            if attendance:
                if attendance.get("status") == "pending":
                    st.info("⏳ You're checked in! Waiting for teacher confirmation...")
                    st.write("Your attendance will be confirmed when the class starts.")

                    # Allow cancellation
                    if st.button(
                        "🗑️ Cancel My Check-in",
                        type="secondary",
                        use_container_width=True,
                    ):
                        cancel_check_in(attendance["id"], user["user_uuid"])

                elif attendance.get("status") == "confirmed":
                    st.success("🎉 You're confirmed for today's class!")
                    st.write("See you on the mat!")

                    if st.button("Done", type="primary", use_container_width=True):
                        st.session_state.pop("current_student", None)
                        st.session_state.pop("selected_user", None)
                        st.rerun()
            else:
                st.warning("No check-in found. Please try again.")
                if st.button("Start Over", type="primary", use_container_width=True):
                    st.session_state.pop("current_student", None)
                    st.session_state.pop("selected_user", None)
                    st.rerun()

    except Exception as e:
        st.error("Error checking status")


def cancel_check_in(attendance_id, user_uuid):
    """Cancel own pending check-in"""
    try:
        response = requests.delete(
            f"{BASE_URL}/attendance/{attendance_id}/cancel",
            params={"user_uuid": user_uuid},
            timeout=5,
        )

        if response.status_code == 200:
            st.success("Check-in cancelled")
            time.sleep(1)
            st.session_state.pop("current_student", None)
            st.session_state.pop("selected_user", None)
            st.rerun()
        else:
            st.error("Error cancelling check-in")

    except Exception as e:
        st.error("Error connecting to server")


# Check if in kiosk mode
if st.session_state.get("kiosk_mode"):
    render_kiosk_mode()
    st.stop()


# ===== ADMIN MODE (existing functionality) =====
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
            file_bytes = uploaded_file.getvalue()
            # DEBUG: Uncomment below for debugging file uploads
            # st.sidebar.write(f"DEBUG: File size: {len(file_bytes)} bytes")
            # st.sidebar.write(f"DEBUG: File name: {uploaded_file.name}")
            # st.sidebar.write(f"DEBUG: File type: {uploaded_file.type}")
            files = {
                "file": (
                    uploaded_file.name,
                    file_bytes,
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

    # DEBUG: Uncomment to check photo URLs
    # with st.expander("🔍 Debug: Check Photo URLs", expanded=False):
    #     if members:
    #         for m in members[:3]:
    #             img_url = m.get("profile_image_url", "NO URL")
    #             st.write(f"**{m['first_name']}:** `{img_url}`")
    #             if img_url and img_url != "NO URL":
    #                 st.code(f"Full URL: {img_url}", language="text")
    #     else:
    #         st.write("No members found")

    for m in members:
        # Create columns for photo, info, and button
        cols = st.columns([1, 4, 1.5])

        # Photo column
        with cols[0]:
            img_url = m.get("profile_image_url")
            if img_url:
                # Use simple st.image with error handling via columns
                try:
                    st.image(img_url, width=50)
                except Exception:
                    st.markdown("👤", help="Photo unavailable")
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
                    # Use the new check-in endpoint (creates PENDING status)
                    post_res = requests.post(
                        f"{BASE_URL}/attendance/check-in", json=payload
                    )

                    if post_res.status_code == 200:
                        response_data = post_res.json()
                        if response_data.get("status") == "pending":
                            st.toast(
                                f"✅ {m['first_name']} checked in! Waiting for teacher confirmation.",
                                icon="🥋",
                            )
                        else:
                            st.toast(
                                f"✅ {m['first_name']} checked in successfully!",
                                icon="🥋",
                            )

                    elif post_res.status_code == 400:
                        # This catches the UniqueConstraint violation from the backend
                        error_detail = post_res.json().get("detail", "")
                        if (
                            "already" in error_detail.lower()
                            and "confirmed" in error_detail.lower()
                        ):
                            st.warning(
                                f"⚠️ {m['first_name']} is already confirmed for this class."
                            )
                        else:
                            st.warning(
                                f"⚠️ {m['first_name']} is already checked into this class."
                            )

                    else:
                        st.error(
                            f"Error: {post_res.json().get('detail', 'Unknown error occurred')}"
                        )

                except Exception as e:
                    st.error(f"Connection failed: {e}")
