import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, date
from pathlib import Path

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Teacher Dashboard", layout="wide", page_icon="👨‍🏫")


# --- HELPER FUNCTIONS FOR CONFIRM ATTENDANCE ---
def confirm_single(attendance_id):
    """Confirm single attendance record"""
    try:
        if "teacher_token" not in st.session_state:
            st.error("❌ Not authenticated. Please login again.")
            return

        token = st.session_state.teacher_token
        response = requests.post(
            f"{BASE_URL}/attendance/{attendance_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if response.status_code == 200:
            st.success("✅ Confirmed!")
            time.sleep(0.5)
            st.rerun()
        elif response.status_code == 401:
            error_detail = response.json().get("detail", "Unauthorized")
            st.error(f"❌ Unauthorized: {error_detail}")
            st.info("Please try logging out and back in.")
        else:
            error_detail = response.json().get("detail", "Unknown error")
            st.error(f"❌ Error: {error_detail}")
    except Exception as e:
        st.error(f"❌ Connection error: {str(e)}")


def delete_single(attendance_id):
    """Delete single attendance record"""
    try:
        response = requests.delete(
            f"{BASE_URL}/attendance/{attendance_id}/cancel",
            params={"user_uuid": "teacher_override"},
            timeout=5,
        )
        if response.status_code == 200:
            st.success("Removed!")
            time.sleep(0.5)
            st.rerun()
    except:
        st.error("Error removing")


def bulk_confirm(attendance_ids):
    """Bulk confirm attendance records"""
    try:
        token = st.session_state.teacher_token
        response = requests.post(
            f"{BASE_URL}/attendance/bulk-confirm",
            json={"attendance_ids": attendance_ids},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if response.status_code == 200:
            st.success(f"Confirmed {len(attendance_ids)} students!")
            time.sleep(0.5)
            st.rerun()
    except:
        st.error("Error in bulk confirm")


def bulk_delete(attendance_ids):
    """Bulk delete attendance records"""
    # For bulk delete, we'd need a new endpoint, so just delete one by one
    try:
        for aid in attendance_ids:
            requests.delete(
                f"{BASE_URL}/attendance/{aid}/cancel",
                params={"user_uuid": "teacher_override"},
                timeout=5,
            )
        st.success(f"Removed {len(attendance_ids)} check-ins!")
        time.sleep(0.5)
        st.rerun()
    except:
        st.error("Error in bulk remove")


def create_direct_attendance(user, class_obj, class_date):
    """Teacher override - add student directly"""
    try:
        token = st.session_state.teacher_token
        response = requests.post(
            f"{BASE_URL}/attendance/direct",
            json={
                "user_uuid": user["user_uuid"],
                "class_id": class_obj["id"],
                "attendance_date": str(class_date),
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if response.status_code == 200:
            st.success(f"Added {user['first_name']}!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Error adding student")
    except:
        st.error("Connection error")


# Function to load CSS files
def load_css():
    """Load custom CSS files for styling"""
    import re

    # Load base styles
    css_path = Path(__file__).parent.parent / "assets/style.css"
    css_content = ""
    if css_path.exists():
        with open(css_path) as f:
            css_content = f.read()

    # Load theme-specific CSS
    theme = st.session_state.get("theme", "dark")
    theme_file = (
        "assets/dark-theme.css" if theme == "dark" else "assets/light-theme.css"
    )
    theme_path = Path(__file__).parent.parent / theme_file

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

    # Combine styles
    combined_css = f"""
    <style>
    {theme_css_content}

    {css_content}
    </style>
    """

    st.markdown(combined_css, unsafe_allow_html=True)


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
tab1, tab2, tab3 = st.tabs(["✅ Confirm Attendance", "📋 Class Roster", "💬 Feedback"])

# --- TAB 1: CONFIRM ATTENDANCE (NEW - Primary tab) ---
with tab1:
    st.header("Confirm Student Attendance")

    # Class & Date Selection
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        confirm_date = st.date_input("Date", value=datetime.now(), key="confirm_date")
    with col2:
        try:
            classes = requests.get(f"{BASE_URL}/classes/").json()
            confirm_class = st.selectbox(
                "Class",
                classes,
                format_func=lambda x: x["class_name"],
                key="confirm_class",
            )
        except:
            st.error("Error loading classes")
            st.stop()
    with col3:
        st.write("")  # Spacer
        auto_refresh = st.checkbox(
            "Auto-refresh (5s)", value=True, key="auto_refresh_checkbox"
        )

        # Manual refresh button
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.session_state.last_pending_refresh = datetime.now().timestamp()
            st.rerun()

        # Auto-refresh logic
        if auto_refresh:
            # Check if we need to refresh (every 5 seconds)
            current_time = datetime.now().timestamp()
            last_refresh = st.session_state.get("last_pending_refresh", 0)

            if current_time - last_refresh >= 5:  # Refresh every 5 seconds
                st.session_state.last_pending_refresh = current_time
                st.rerun()

    st.markdown("---")

    # Fetch ALL attendance for this class and date
    try:
        # Get class instance first
        instance_response = requests.get(
            f"{BASE_URL}/class-instances/by-date/",
            params={"class_id": confirm_class["id"], "class_date": str(confirm_date)},
            timeout=5,
        )

        attendance_records = []
        class_instance_id = None

        if instance_response.status_code == 200:
            instance_data = instance_response.json()
            class_instance_id = instance_data.get("id")

            # Get all attendance for this class instance
            if class_instance_id:
                attendance_response = requests.get(
                    f"{BASE_URL}/attendance/",
                    params={"class_instance_id": class_instance_id},
                    timeout=5,
                )
                if attendance_response.status_code == 200:
                    attendance_records = attendance_response.json()

        # If no instance exists or no records found, try alternative query
        if not attendance_records:
            # Try getting by class and date directly
            attendance_response = requests.get(
                f"{BASE_URL}/attendance/class/{confirm_class['id']}",
                params={"class_date": str(confirm_date)},
                timeout=5,
            )
            if attendance_response.status_code == 200:
                attendance_records = attendance_response.json()

        # Separate pending and confirmed
        pending_records = [
            r for r in attendance_records if r.get("status") == "pending"
        ]
        confirmed_records = [
            r for r in attendance_records if r.get("status") == "confirmed"
        ]

        # Summary metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Total Students", len(attendance_records))
        with col_m2:
            st.metric("⏳ Pending", len(pending_records))
        with col_m3:
            st.metric("✅ Confirmed", len(confirmed_records))

        st.markdown("---")

        if not attendance_records:
            st.info("📭 No students have checked in for this class and date yet.")
            st.caption("Students who check in will appear here for confirmation.")
        else:
            # Show all students with their status
            st.subheader(f"📋 Student List ({len(attendance_records)} total)")

            # Table header
            header_cols = st.columns([0.5, 2.5, 1.5, 1.5, 2])
            with header_cols[0]:
                st.write("**Select**")
            with header_cols[1]:
                st.write("**Student**")
            with header_cols[2]:
                st.write("**Time**")
            with header_cols[3]:
                st.write("**Status**")
            with header_cols[4]:
                st.write("**Action**")

            st.markdown("---")

            selected_pending_ids = []

            for record in attendance_records:
                is_pending = record.get("status") == "pending"
                is_confirmed = record.get("status") == "confirmed"

                row_cols = st.columns([0.5, 2.5, 1.5, 1.5, 2])

                with row_cols[0]:
                    if is_pending:
                        is_selected = st.checkbox(
                            "",
                            key=f"select_{record['id']}",
                            label_visibility="collapsed",
                        )
                        if is_selected:
                            selected_pending_ids.append(record["id"])
                    else:
                        st.write("✓")

                with row_cols[1]:
                    student_name = f"{record.get('first_name', '')} {record.get('last_name', '')}".strip()
                    if not student_name:
                        student_name = record.get("user_name", "Unknown")

                    cols_student = st.columns([1, 3])
                    with cols_student[0]:
                        img_url = record.get("profile_image_url") or record.get(
                            "user", {}
                        ).get("profile_image_url")
                        if img_url:
                            st.image(img_url, width=250)
                        else:
                            st.write("👤")
                    with cols_student[1]:
                        st.write(f"**{student_name}**")

                with row_cols[2]:
                    check_in_time = record.get("created_at") or record.get(
                        "check_in_time"
                    )
                    if check_in_time:
                        try:
                            from datetime import datetime as dt

                            time_obj = dt.fromisoformat(
                                str(check_in_time).replace("Z", "+00:00")
                            )
                            st.write(f"🕐 {time_obj.strftime('%H:%M')}")
                        except:
                            st.write("🕐 --:--")
                    else:
                        st.write("🕐 --:--")

                with row_cols[3]:
                    if is_pending:
                        st.warning("⏳ Pending")
                    elif is_confirmed:
                        st.success("✅ Confirmed")
                    else:
                        st.info(f"ℹ️ {record.get('status', 'Unknown')}")

                with row_cols[4]:
                    if is_pending:
                        action_cols = st.columns(2)
                        with action_cols[0]:
                            if st.button(
                                "✓ Confirm",
                                key=f"confirm_btn_{record['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                confirm_single(record["id"])
                        with action_cols[1]:
                            if st.button(
                                "✕ Remove",
                                key=f"delete_btn_{record['id']}",
                                type="secondary",
                                use_container_width=True,
                            ):
                                delete_single(record["id"])
                    else:
                        st.caption("Already confirmed")

            # Bulk actions section
            if selected_pending_ids:
                st.markdown("---")
                st.subheader("Bulk Actions")
                st.write(f"**{len(selected_pending_ids)} students selected**")

                bulk_cols = st.columns(2)
                with bulk_cols[0]:
                    if st.button(
                        f"✅ Confirm All Selected ({len(selected_pending_ids)})",
                        type="primary",
                        use_container_width=True,
                    ):
                        bulk_confirm(selected_pending_ids)

                with bulk_cols[1]:
                    if st.button(
                        "🗑️ Remove All Selected",
                        type="secondary",
                        use_container_width=True,
                    ):
                        bulk_delete(selected_pending_ids)

            # "Confirm All Pending" button at the bottom
            if pending_records:
                st.markdown("---")
                if st.button(
                    f"✅ CONFIRM ALL PENDING ({len(pending_records)} students)",
                    type="primary",
                    use_container_width=True,
                ):
                    pending_ids = [r["id"] for r in pending_records]
                    bulk_confirm(pending_ids)

        # Add student override section (always visible)
        st.markdown("---")
        with st.expander("➕ Add Student Manually (Bypass Check-in)"):
            st.write("Add a student directly without requiring them to check in first:")

            try:
                users_response = requests.get(f"{BASE_URL}/users/").json()
                users = [u for u in users_response if u.get("is_current")]

                # Filter out already checked-in students
                checked_in_uuids = {r.get("user_uuid") for r in attendance_records}
                available_users = [
                    u for u in users if u["user_uuid"] not in checked_in_uuids
                ]

                if available_users:
                    selected_user = st.selectbox(
                        "Select Student to Add",
                        available_users,
                        format_func=lambda x: f"{x['first_name']} {x['last_name']} ({x['rank']})",
                    )

                    if st.button(
                        "Add & Confirm", type="primary", use_container_width=True
                    ):
                        create_direct_attendance(
                            selected_user, confirm_class, confirm_date
                        )
                else:
                    st.info("All students are already checked in for this class!")

            except Exception as e:
                st.error("Error loading users")

    except Exception as e:
        st.error(f"Error loading attendance: {str(e)}")
        st.code(f"Class ID: {confirm_class['id']}, Date: {confirm_date}")


# --- TAB 2: CLASS ROSTER (existing functionality) ---
with tab2:
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


# --- TAB 3: FEEDBACK ---
with tab3:
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
