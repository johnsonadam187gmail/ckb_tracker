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
    import re

    # Load base styles
    css_path = Path(__file__).parent / "assets/style.css"
    css_content = ""
    if css_path.exists():
        with open(css_path) as f:
            css_content = f.read()

    # Load theme-specific CSS
    theme = st.session_state.get("theme", "dark")
    theme_file = (
        "assets/dark-theme.css" if theme == "dark" else "assets/light-theme.css"
    )
    theme_path = Path(__file__).parent / theme_file

    theme_css_content = ""
    if theme_path.exists():
        with open(theme_path) as f:
            theme_css = f.read()

            # Extract the entire :root[data-theme="X"], .X-theme { ... } block content
            root_pattern = (
                r":root\[data-theme=\""
                + theme
                + r"\"\],\s*\."
                + theme
                + r"-theme\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}"
            )
            root_match = re.search(root_pattern, theme_css, re.DOTALL)
            if root_match:
                theme_vars = root_match.group(1).strip()
                theme_css_content = f":root {{\n{theme_vars}\n}}\n\n"

            # Extract and convert all [data-theme="X"] selectors to apply directly
            # Replace [data-theme="X"] prefix with nothing (apply directly)
            selector_pattern = r'\[data-theme="' + theme + r'"\]\s+'
            theme_rules = re.sub(selector_pattern, "", theme_css)

            # Remove the :root block we already extracted
            theme_rules = re.sub(root_pattern, "", theme_rules, flags=re.DOTALL)

            # Clean up any remaining empty selectors or duplicates
            theme_rules = re.sub(r"\n\s*\n+", "\n\n", theme_rules)

            theme_css_content += theme_rules

    # Add base text color rule to ensure text changes with theme
    text_color_rule = """
    /* Base text color for all content */
    .stApp, .stApp *, .stApp p, .stApp span, .stApp label, .stApp div, .stApp li {
        color: var(--text-primary) !important;
    }
    
    /* Headings */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: var(--text-primary) !important;
    }
    
    /* Ensure Streamlit text elements use theme colors */
    .stMarkdown, .stText {
        color: var(--text-primary) !important;
    }
    
    /* Tables and DataFrames */
    .stDataFrame, .stTable, [data-testid="stDataFrameResizable"], [data-testid="stTable"] {
        color: var(--text-primary) !important;
    }
    .stDataFrame td, .stDataFrame th, .stTable td, .stTable th {
        color: var(--text-primary) !important;
        background-color: var(--bg-secondary) !important;
    }
    
    /* Streamlit native elements */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {
        color: var(--text-primary) !important;
    }
    
    /* Form inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stMultiselect, .stTextArea textarea {
        color: var(--text-primary) !important;
        background-color: var(--input-background) !important;
    }
    
    /* Buttons */
    .stButton button, button[kind="primary"], button[kind="secondary"] {
        color: var(--button-text) !important;
    }
    
    /* Expander and tabs */
    [data-testid="stExpander"], [data-testid="stTabs"] {
        color: var(--text-primary) !important;
    }
    
    /* Plotly charts - ensure dark background */
    .js-plotly-plot .plotly {
        background-color: transparent !important;
    }
    
    /* Sidebar specific */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-background) !important;
    }
    section[data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }
    """

    # Combine styles
    combined_css = f"""
    <style>
    {theme_css_content}
    
    {text_color_rule}
    
    {css_content}
    </style>
    """

    st.markdown(combined_css, unsafe_allow_html=True)


# Initialize theme in session state
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Initialize photo capture state
if "show_camera" not in st.session_state:
    st.session_state.show_camera = False
if "captured_photo" not in st.session_state:
    st.session_state.captured_photo = None

# Initialize student check-in state
if "session_student" not in st.session_state:
    st.session_state.session_student = None
if "session_last_activity" not in st.session_state:
    st.session_state.session_last_activity = None
if "show_start_over_confirm" not in st.session_state:
    st.session_state.show_start_over_confirm = False
if "show_cancel_confirm" not in st.session_state:
    st.session_state.show_cancel_confirm = None  # Will store attendance_id to cancel
if "checking_in_classes" not in st.session_state:
    st.session_state.checking_in_classes = (
        set()
    )  # Track which classes are being checked in
if "session_checked_in_classes" not in st.session_state:
    st.session_state.session_checked_in_classes = (
        set()
    )  # Track ALL classes checked in this session

# Load CSS
load_css()


# ===== SESSION MANAGEMENT =====
def check_session_timeout():
    """Check if session has expired (2 minutes of inactivity)"""
    if st.session_state.session_student and st.session_state.session_last_activity:
        elapsed = time.time() - st.session_state.session_last_activity
        if elapsed > 120:  # 2 minutes
            # Session expired
            st.session_state.session_student = None
            st.session_state.session_last_activity = None
            st.session_state.show_start_over_confirm = False
            st.session_state.show_cancel_confirm = None
            return True
    return False


def update_activity():
    """Update last activity timestamp"""
    st.session_state.session_last_activity = time.time()


def clear_session():
    """Clear student session"""
    st.session_state.session_student = None
    st.session_state.session_last_activity = None
    st.session_state.show_start_over_confirm = False
    st.session_state.show_cancel_confirm = None
    st.session_state.checking_in_classes = set()
    st.session_state.session_checked_in_classes = set()


# ===== USER SEARCH =====
def show_user_search():
    """Search interface for finding student"""
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
                                st.image(user["profile_image_url"], width=80)
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
                                st.session_state.session_student = user
                                update_activity()
                                st.rerun()
                else:
                    st.info("No matches found. Try a different search.")

        except Exception as e:
            st.error("Error searching users")


# ===== CLASS CHECK-IN DASHBOARD =====
def get_todays_attendance(user_uuid):
    """Get all attendance records for user for today"""
    today = date.today()
    try:
        response = requests.get(f"{BASE_URL}/attendance/user/{user_uuid}", timeout=5)
        if response.status_code == 200:
            records = response.json()
            # Filter for today's records only
            return [r for r in records if r.get("attendance_date") == str(today)]
    except:
        pass
    return []


def get_all_classes():
    """Get all available classes"""
    try:
        response = requests.get(f"{BASE_URL}/classes/", timeout=5)
        if response.status_code == 200:
            classes = response.json()
            # Sort by time
            return sorted(classes, key=lambda x: x.get("time", ""))
    except:
        pass
    return []


def check_in_to_class(user_uuid, class_id):
    """Create PENDING attendance record for class"""
    today = date.today()
    try:
        response = requests.post(
            f"{BASE_URL}/attendance/check-in",
            json={
                "user_uuid": user_uuid,
                "class_id": class_id,
                "attendance_date": str(today),
            },
            timeout=5,
        )
        return response.status_code == 200
    except:
        return False


def cancel_check_in(attendance_id, user_uuid):
    """Cancel pending check-in"""
    try:
        response = requests.delete(
            f"{BASE_URL}/attendance/{attendance_id}/cancel",
            params={"user_uuid": user_uuid},
            timeout=5,
        )
        return response.status_code == 200
    except:
        return False


def show_student_dashboard():
    """Main student dashboard showing all classes and check-in status"""
    user = st.session_state.session_student

    # Check for session timeout
    if check_session_timeout():
        st.warning("⏰ Session expired due to inactivity. Please search again.")
        st.rerun()
        return

    # Update activity
    update_activity()

    # Calculate time remaining
    time_remaining = 120 - (time.time() - st.session_state.session_last_activity)

    # Student info header
    st.success(f"👤 Signed in as: {user['first_name']} {user['last_name']}")

    # Large photo
    col1, col2 = st.columns([1, 2])
    with col1:
        if user.get("profile_image_url"):
            st.image(user["profile_image_url"], width=250)
        else:
            st.markdown("## 👤")
    with col2:
        st.write(f"**Name:** {user['first_name']} {user['last_name']}")
        st.write(f"**Email:** {user['email']}")
        if time_remaining < 60:
            st.error(f"⏰ Session expires in {int(time_remaining)}s")
        else:
            st.info(
                f"⏰ Session expires in {int(time_remaining // 60)}m {int(time_remaining % 60)}s"
            )

    st.markdown("---")

    # Get today's attendance and all classes
    todays_attendance = get_todays_attendance(user["user_uuid"])
    all_classes = get_all_classes()

    # Create attendance lookup by class_id
    attendance_by_class = {}
    for att in todays_attendance:
        attendance_by_class[att.get("class_id")] = att

    # Display all classes
    st.subheader(f"📋 Today's Classes ({date.today().strftime('%B %d, %Y')}):")

    if not all_classes:
        st.info("No classes scheduled for today.")
    else:
        for cls in all_classes:
            class_id = cls["id"]
            class_name = cls.get("class_name", "Unknown")
            class_time = cls.get("time", "")

            # Get attendance status for this class
            att = attendance_by_class.get(class_id)

            if att:
                status = att.get("status", "pending")
                attendance_id = att.get("id")

                if status == "confirmed":
                    # Confirmed - Green background
                    with st.container():
                        st.markdown(
                            """
                            <div style="background-color: rgba(76, 175, 80, 0.2); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                            """,
                            unsafe_allow_html=True,
                        )
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.write(f"🥋 **{class_name}** ({class_time})")
                        with col2:
                            st.write("✅ Confirmed")
                        with col3:
                            st.button(
                                "Already Confirmed",
                                key=f"confirmed_{class_id}",
                                disabled=True,
                                use_container_width=True,
                            )
                        st.markdown("</div>", unsafe_allow_html=True)

                else:  # pending
                    # Pending - Yellow background
                    with st.container():
                        st.markdown(
                            """
                            <div style="background-color: rgba(255, 193, 7, 0.2); padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                            """,
                            unsafe_allow_html=True,
                        )
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.write(f"🥋 **{class_name}** ({class_time})")
                        with col2:
                            st.write("⏳ Pending")
                        with col3:
                            # Show cancel button or confirmation dialog
                            if st.session_state.show_cancel_confirm == attendance_id:
                                st.warning("Cancel this check-in?")
                                ccol1, ccol2 = st.columns(2)
                                with ccol1:
                                    if st.button(
                                        "Yes",
                                        key=f"confirm_cancel_{attendance_id}",
                                        type="primary",
                                    ):
                                        if cancel_check_in(
                                            attendance_id, user["user_uuid"]
                                        ):
                                            st.success("Cancelled!")
                                            st.session_state.show_cancel_confirm = None
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error("Error cancelling")
                                with ccol2:
                                    if st.button(
                                        "No", key=f"deny_cancel_{attendance_id}"
                                    ):
                                        st.session_state.show_cancel_confirm = None
                                        st.rerun()
                            else:
                                if st.button(
                                    "🗑️ Cancel",
                                    key=f"cancel_{class_id}",
                                    use_container_width=True,
                                ):
                                    st.session_state.show_cancel_confirm = attendance_id
                                    st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Not checked in - Check if being processed or was checked in this session
                is_checking_in = class_id in st.session_state.checking_in_classes
                is_session_checked = (
                    class_id in st.session_state.session_checked_in_classes
                )

                with st.container():
                    # Determine visual state
                    if is_checking_in:
                        # Currently processing
                        bg_color = "rgba(128, 128, 128, 0.3)"
                        status_text = "⏳ Checking in..."
                        button_label = "⏳ Processing..."
                        button_disabled = True
                    elif is_session_checked:
                        # Checked in this session (may not show in API yet)
                        bg_color = "rgba(255, 193, 7, 0.3)"
                        status_text = "⏳ Pending"
                        button_label = "🗑️ Cancel"
                        button_disabled = False
                    else:
                        # Not checked in
                        bg_color = "rgba(128, 128, 128, 0.2)"
                        status_text = "Not Checked In"
                        button_label = "✅ Check In"
                        button_disabled = False

                    st.markdown(
                        f"""
                        <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                        """,
                        unsafe_allow_html=True,
                    )
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.write(f"🥋 **{class_name}** ({class_time})")
                    with col2:
                        st.write(status_text)
                    with col3:
                        if is_checking_in:
                            # Show disabled processing button
                            st.button(
                                button_label,
                                key=f"processing_{class_id}",
                                disabled=True,
                                use_container_width=True,
                            )
                        elif is_session_checked:
                            # Show cancel button (treat as pending)
                            if st.button(
                                button_label,
                                key=f"cancel_{class_id}",
                                use_container_width=True,
                            ):
                                # Remove from session set to allow re-checkin
                                st.session_state.session_checked_in_classes.discard(
                                    class_id
                                )
                                st.rerun()
                        else:
                            # Show active check-in button
                            if st.button(
                                button_label,
                                key=f"checkin_{class_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                # Add to checking set immediately for visual feedback
                                st.session_state.checking_in_classes.add(class_id)
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    # Process any pending check-ins after rendering all buttons
    # This happens outside the loop to avoid duplicate processing
    for class_id in list(st.session_state.checking_in_classes):
        if check_in_to_class(user["user_uuid"], class_id):
            st.session_state.checking_in_classes.discard(class_id)
            st.session_state.session_checked_in_classes.add(class_id)
            st.rerun()
        else:
            st.session_state.checking_in_classes.discard(class_id)
            st.error(f"Error checking in to class {class_id}")
            st.rerun()

    st.markdown("---")

    # Complete button - simple way to finish and go back to search
    if st.button(
        "✅ Complete - Done",
        key="complete_session",
        type="primary",
        use_container_width=True,
    ):
        clear_session()
        st.rerun()

    st.markdown("---")

    # Start Over button at bottom with confirmation
    if st.session_state.show_start_over_confirm:
        st.warning(
            "Are you sure you want to start over? This will sign out the current student."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Yes, Start Over",
                key="confirm_start_over",
                type="primary",
                use_container_width=True,
            ):
                clear_session()
                st.rerun()
        with col2:
            if st.button(
                "No, Stay Signed In", key="cancel_start_over", use_container_width=True
            ):
                st.session_state.show_start_over_confirm = False
                st.rerun()
    else:
        if st.button(
            "🔄 Start Over - New Student", key="start_over", use_container_width=True
        ):
            st.session_state.show_start_over_confirm = True
            st.rerun()


# ===== SIDEBAR FUNCTIONS =====
def render_sidebar():
    """Render the sidebar with theme toggle and add member form"""
    # Theme toggle
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("**Theme Mode**")
        with col2:
            current_theme = st.session_state.get("theme", "dark")
            if st.button(
                "🌙" if current_theme == "dark" else "☀️",
                key="theme_toggle",
                help="Toggle theme",
            ):
                st.session_state.theme = "light" if current_theme == "dark" else "dark"
                st.rerun()

        st.divider()

    # Add New Member Section
    st.sidebar.header("Add New Member")

    # Photo Capture Section
    st.sidebar.markdown("### 📸 Profile Photo")
    st.sidebar.markdown("*Optional - Add a profile photo*")

    photo_method = st.sidebar.radio(
        "Choose photo method:",
        ["Take Photo (Camera)", "Upload File", "No Photo"],
        key="photo_method",
    )

    uploaded_file = None

    if photo_method == "Take Photo (Camera)":
        if not st.session_state.show_camera:
            if st.sidebar.button(
                "📷 Open Camera", key="open_camera", use_container_width=True
            ):
                st.session_state.show_camera = True
                st.rerun()
        else:
            camera_photo = st.sidebar.camera_input(
                "Take a photo",
                help="Click the camera button to capture",
                key="camera_input",
            )
            if camera_photo:
                st.session_state.captured_photo = camera_photo
                st.session_state.show_camera = False
                st.rerun()

            if st.sidebar.button("❌ Cancel", key="cancel_camera"):
                st.session_state.show_camera = False
                st.rerun()

        if st.session_state.captured_photo:
            uploaded_file = st.session_state.captured_photo
            st.sidebar.success("Photo captured!")

    elif photo_method == "Upload File":
        uploaded_file = st.sidebar.file_uploader(
            "Upload Profile Picture",
            type=["jpg", "jpeg", "png"],
            help="Supported formats: JPG, JPEG, PNG (Max 5MB)",
        )
        if st.session_state.captured_photo:
            st.session_state.captured_photo = None

    else:
        uploaded_file = None
        if st.session_state.captured_photo:
            st.session_state.captured_photo = None

    if uploaded_file:
        st.sidebar.image(uploaded_file, width=200)
        st.sidebar.caption("Photo ready for upload")
        if st.sidebar.button("❌ Clear Photo", key="clear_photo"):
            st.session_state.captured_photo = None
            st.session_state.show_camera = False
            st.rerun()

    st.sidebar.markdown("---")

    # Add member form
    with st.sidebar.form("add_user_form"):
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")

        password = st.text_input(
            "Password", type="password", help="Minimum 6 characters required"
        )
        confirm_password = st.text_input("Confirm Password", type="password")

        nicknames = st.text_input("Nicknames (Optional)")
        rank = st.selectbox(
            "Current Rank", ["White", "Blue", "Purple", "Brown", "Black"]
        )
        last_grade = st.date_input("Last Grading Date", value=date.today())
        comments = st.text_area("Comments")

        submit_button = st.form_submit_button("Create Member")

    if submit_button:
        if not first_name or not last_name or not email:
            st.sidebar.error("❌ First Name, Last Name, and Email are required!")
        elif not password or not confirm_password:
            st.sidebar.error("❌ Password is required!")
        elif len(password) < 6:
            st.sidebar.error("❌ Password must be at least 6 characters!")
        elif password != confirm_password:
            st.sidebar.error("❌ Passwords do not match!")
        else:
            payload = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
                "nicknames": nicknames,
                "rank": rank,
                "last_grade_date": str(last_grade),
                "comments": comments,
            }

            files = None
            if uploaded_file:
                file_bytes = uploaded_file.getvalue()
                files = {
                    "file": (
                        uploaded_file.name,
                        file_bytes,
                        uploaded_file.type,
                    )
                }

            try:
                response = requests.post(
                    f"{BASE_URL}/users/", data=payload, files=files
                )

                if response.status_code == 200:
                    st.sidebar.success(f"✅ Successfully added {first_name}!")
                    st.session_state.captured_photo = None
                    st.session_state.show_camera = False
                    st.rerun()
                else:
                    st.sidebar.error(
                        f"❌ Error: {response.json().get('detail', 'Unknown error')}"
                    )
            except Exception as e:
                st.sidebar.error(f"⚠️ Could not connect to Backend: {e}")


# ===== MAIN PAGE LAYOUT =====
st.title("📝 Student Check-In")

# Render sidebar
render_sidebar()

# Main content area
st.markdown("---")

# Display current date
st.info(f"📅 {date.today().strftime('%A, %B %d, %Y')}")

st.markdown("---")

# Show either search or dashboard based on session state
if st.session_state.session_student:
    show_student_dashboard()
else:
    show_user_search()
