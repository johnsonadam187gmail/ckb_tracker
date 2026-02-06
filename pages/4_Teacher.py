import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
from pathlib import Path

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Teacher Dashboard", layout="wide", page_icon="👨‍🏫")


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

# Load CSS
load_css()


# --- AUTHENTICATION FUNCTIONS ---
def verify_session():
    """Verify teacher session token is still valid."""
    if "teacher_token" not in st.session_state:
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/auth/verify-session",
            json={"token": st.session_state.teacher_token},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            # Update token with extended one
            st.session_state.teacher_token = data["new_token"]
            return True
        else:
            return False
    except Exception:
        return False


def teacher_login(email: str, password: str):
    """Authenticate teacher and store session."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/teacher-login",
            data={
                "username": email,
                "password": password,
            },  # OAuth2PasswordRequestForm format
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            st.session_state.teacher_token = data["access_token"]
            st.session_state.teacher_info = data["user_info"]
            return True, None
        else:
            error_detail = response.json().get("detail", "Login failed")
            return False, error_detail
    except Exception as e:
        return False, f"Connection error: {str(e)}"


def logout():
    """Clear teacher session."""
    if "teacher_token" in st.session_state:
        del st.session_state.teacher_token
    if "teacher_info" in st.session_state:
        del st.session_state.teacher_info
    st.rerun()


# --- AUTHENTICATION GATE ---
if "teacher_token" not in st.session_state or not verify_session():
    # Show login form
    st.title("👨‍🏫 Teacher Dashboard - Login")
    st.markdown("Please sign in with your teacher account to access the dashboard.")

    with st.form("teacher_login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("🔐 Login", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("❌ Please enter both email and password")
            else:
                with st.spinner("Authenticating..."):
                    success, error = teacher_login(email, password)
                    if success:
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error(f"❌ {error}")

    st.stop()  # Don't render rest of page


# --- AUTHENTICATED VIEW ---
st.title("👨‍🏫 Teacher Dashboard")

# Sidebar with logout button
with st.sidebar:
    teacher_name = f"{st.session_state.teacher_info['first_name']} {st.session_state.teacher_info['last_name']}"
    st.write(f"**Logged in as:** {teacher_name}")
    if st.button("🚪 Logout", use_container_width=True):
        logout()


# --- TABS ---
tab1, tab2 = st.tabs(["📋 Class Roster", "💬 Feedback"])

# --- TAB 1: CLASS ROSTER (existing functionality) ---
with tab1:
    st.header("Class Roster & Assignment")

    col1, col2, col3, col4 = st.columns([1, 2, 2, 1.5])

    with col1:
        selected_date = st.date_input("Class Date", value=datetime.now())

    with col2:
        # Fetch all classes
        try:
            class_res = requests.get(f"{BASE_URL}/classes/")
            classes = class_res.json() if class_res.status_code == 200 else []
        except:
            classes = []
            st.error("⚠️ Could not fetch classes from server")

        class_data = {}
        for c in classes:
            display_key = f"{c['class_name']} ({c['time']})"
            class_data[display_key] = {
                "id": c["id"],
                "name": c["class_name"],
                "time": c["time"],
            }

        selected_class_name = st.selectbox(
            "Select Class", options=["-- Select Class --"] + list(class_data.keys())
        )

    with col3:
        # Fetch users with Teacher role
        try:
            teachers_res = requests.get(f"{BASE_URL}/roles/users/by-role/Teacher")
            teachers = teachers_res.json() if teachers_res.status_code == 200 else []
        except:
            teachers = []

        teacher_options = {"-- No Teacher Assigned --": None}
        if teachers:
            teacher_options.update(
                {
                    f"{t['first_name']} {t['last_name']}": t["user_uuid"]
                    for t in teachers
                }
            )

        # Pre-select logged-in teacher as default
        logged_in_teacher_name = teacher_name
        default_index = 0
        if logged_in_teacher_name in teacher_options:
            default_index = list(teacher_options.keys()).index(logged_in_teacher_name)

        selected_teacher_name = st.selectbox(
            "Assign Teacher",
            options=list(teacher_options.keys()),
            index=default_index,
            help="Select the teacher who taught this class (you can assign yourself to any class)",
        )

    with col4:
        # Assignment button
        selected_teacher_uuid = teacher_options.get(selected_teacher_name)
        class_selected = selected_class_name != "-- Select Class --"
        teacher_selected = selected_teacher_uuid is not None

        button_disabled = not (class_selected and teacher_selected)

        if st.button(
            "💾 Assign Teacher",
            disabled=button_disabled,
            help="Assigns teacher to this class instance"
            if not button_disabled
            else "Select class and teacher first",
            use_container_width=True,
        ):
            if class_selected and teacher_selected:
                class_id = class_data[selected_class_name]["id"]

                # Check if ClassInstance exists
                try:
                    instance_res = requests.get(
                        f"{BASE_URL}/class-instances/by-date/",
                        params={"class_id": class_id, "class_date": str(selected_date)},
                    )

                    with st.spinner("Assigning teacher..."):
                        if instance_res.status_code == 200:
                            # Update existing instance
                            instance = instance_res.json()
                            update_res = requests.put(
                                f"{BASE_URL}/class-instances/{instance['id']}",
                                json={"teacher_uuid": selected_teacher_uuid},
                            )
                            if update_res.status_code == 200:
                                st.success(
                                    f"✅ Assigned {selected_teacher_name} to class!"
                                )
                                st.toast("Teacher assigned successfully!", icon="✅")
                                st.rerun()
                            else:
                                st.error(
                                    f"❌ Failed to update: {update_res.json().get('detail')}"
                                )
                        else:
                            # Create new instance
                            create_res = requests.post(
                                f"{BASE_URL}/class-instances/",
                                json={
                                    "class_id": class_id,
                                    "class_date": str(selected_date),
                                    "teacher_uuid": selected_teacher_uuid,
                                    "lesson_id": None,
                                },
                            )
                            if create_res.status_code == 200:
                                st.success(
                                    f"✅ Assigned {selected_teacher_name} to class!"
                                )
                                st.toast("Teacher assigned successfully!", icon="✅")
                                st.rerun()
                            else:
                                st.error(
                                    f"❌ Failed to create: {create_res.json().get('detail')}"
                                )
                except Exception as e:
                    st.error(f"⚠️ Error: {str(e)}")

    # Show student roster if class selected
    if selected_class_name != "-- Select Class --":
        class_id = class_data[selected_class_name]["id"]

        st.divider()
        st.subheader(f"📊 {selected_class_name} - {selected_date}")

        # Fetch attendance for this class and date
        try:
            attendance_res = requests.get(
                f"{BASE_URL}/attendance/class/{class_id}",
                params={"class_date": str(selected_date)},
            )

            if attendance_res.status_code == 200:
                attendance_records = attendance_res.json()

                if not attendance_records:
                    st.info("No students have checked in yet for this class.")
                else:
                    # Display student roster
                    roster_data = []
                    for record in attendance_records:
                        roster_data.append(
                            {
                                "Name": f"{record.get('first_name', '')} {record.get('last_name', '')}",
                                "Rank": record.get("rank", "N/A"),
                                "Check-in Time": pd.to_datetime(
                                    record.get("created_at")
                                ).strftime("%H:%M:%S")
                                if record.get("created_at")
                                else "N/A",
                            }
                        )

                    df_roster = pd.DataFrame(roster_data)
                    st.dataframe(df_roster, use_container_width=True, hide_index=True)
                    st.caption(f"**Total Attendees:** {len(roster_data)}")
            else:
                st.error("Failed to fetch attendance records")
        except Exception as e:
            st.error(f"⚠️ Error fetching attendance: {str(e)}")


# --- TAB 2: FEEDBACK ---
with tab2:
    st.header("💬 Student Feedback")
    st.markdown(
        "Feedback from students for classes you taught (student names are anonymous)"
    )

    teacher_uuid = st.session_state.teacher_info["user_uuid"]

    # Fetch feedback for this teacher
    try:
        feedback_res = requests.get(f"{BASE_URL}/feedback/teacher/{teacher_uuid}")

        if feedback_res.status_code == 200:
            feedback_records = feedback_res.json()

            if not feedback_records:
                st.info("📭 No feedback yet for classes you've taught")
            else:
                # Filters
                with st.expander("🔍 Filters"):
                    col_f1, col_f2, col_f3 = st.columns(3)

                    with col_f1:
                        # Date range filter
                        dates = [
                            pd.to_datetime(f["class_date"]).date()
                            for f in feedback_records
                            if f.get("class_date")
                        ]
                        if dates:
                            min_date = min(dates)
                            max_date = max(dates)
                            date_range = st.date_input(
                                "Date Range",
                                value=(min_date, max_date),
                                min_value=min_date,
                                max_value=max_date,
                            )
                        else:
                            date_range = None

                    with col_f2:
                        # Class filter
                        all_classes = list(
                            set(
                                [
                                    f["class_name"]
                                    for f in feedback_records
                                    if f.get("class_name")
                                ]
                            )
                        )
                        selected_classes = st.multiselect(
                            "Classes", options=all_classes, default=all_classes
                        )

                    with col_f3:
                        # Rating filter
                        rating_filter = st.selectbox(
                            "Rating", options=["All", "Positive", "Negative"]
                        )

                # Apply filters
                filtered_records = feedback_records

                if date_range and len(date_range) == 2:
                    filtered_records = [
                        f
                        for f in filtered_records
                        if date_range[0]
                        <= pd.to_datetime(f["class_date"]).date()
                        <= date_range[1]
                    ]

                if selected_classes:
                    filtered_records = [
                        f
                        for f in filtered_records
                        if f.get("class_name") in selected_classes
                    ]

                if rating_filter != "All":
                    if rating_filter == "Positive":
                        filtered_records = [
                            f
                            for f in filtered_records
                            if f.get("rating") == "thumbs_up"
                        ]
                    else:
                        filtered_records = [
                            f
                            for f in filtered_records
                            if f.get("rating") == "thumbs_down"
                        ]

                # Display metrics
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Total Feedback", len(filtered_records))
                with col_m2:
                    positive = sum(
                        1 for f in filtered_records if f.get("rating") == "thumbs_up"
                    )
                    st.metric("👍 Positive", positive)
                with col_m3:
                    negative = sum(
                        1 for f in filtered_records if f.get("rating") == "thumbs_down"
                    )
                    st.metric("👎 Negative", negative)

                st.divider()

                # Display feedback table (ANONYMOUS - no student names)
                feedback_display = []
                for record in filtered_records:
                    feedback_display.append(
                        {
                            "Date": pd.to_datetime(record["class_date"]).strftime(
                                "%Y-%m-%d"
                            ),
                            "Class": record.get("class_name", "Unknown"),
                            "Lesson": record.get("lesson_title") or "No lesson",
                            "Rating": "👍 Positive"
                            if record.get("rating") == "thumbs_up"
                            else "👎 Negative"
                            if record.get("rating") == "thumbs_down"
                            else "N/A",
                            "Comment": record.get("comment") or "No comment",
                        }
                    )

                df_feedback = pd.DataFrame(feedback_display)
                st.dataframe(df_feedback, use_container_width=True, hide_index=True)

                st.caption("ℹ️ Student names are kept anonymous for privacy")
        else:
            st.error(
                f"Failed to fetch feedback: {feedback_res.json().get('detail', 'Unknown error')}"
            )
    except Exception as e:
        st.error(f"⚠️ Error loading feedback: {str(e)}")
