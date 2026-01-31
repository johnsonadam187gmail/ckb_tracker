import streamlit as st
import requests
import pandas as pd
from datetime import date
from pathlib import Path


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


# --- AUTHENTICATION LOGIC ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        # Check against your desired credentials
        if (
            st.session_state["username"] == "admin"
            and st.session_state["password"] == "ckb2026"
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs
        st.subheader("🔒 Admin Access Required")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        return False

    elif not st.session_state["password_correct"]:
        # Password not correct, show inputs + error
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        st.error("😕 User not known or password incorrect")
        return False

    else:
        # Password correct.
        return True


# --- PAGE EXECUTION ---
if check_password():
    # --- CONFIGURATION ---
    BASE_URL = "http://127.0.0.1:8000"

    st.set_page_config(page_title="Management Console", layout="wide", page_icon="⚙️")
    st.title("⚙️ Management Console")

    # --- HELPER: API REQUEST HANDLER ---
    def handle_request(method, endpoint, data=None):
        try:
            if method == "POST":
                res = requests.post(f"{BASE_URL}/{endpoint}/", json=data)
            elif method == "PUT":
                # For SCD Type 2, we target the UUID
                target_uuid = data.pop("uuid", None)
                res = requests.put(f"{BASE_URL}/{endpoint}/{target_uuid}", json=data)

            if res.status_code == 200:
                st.success("✅ Action completed successfully!")
                st.rerun()
            else:
                detail = res.json().get("detail", "Unknown error")
                st.error(f"❌ Error: {detail}")
        except Exception as e:
            st.error(f"⚠️ Connection failed: {e}")

    # --- TABS DEFINITION ---
    tab_user, tab_class, tab_gym_types, tab_terms, tab_targets, tab_lessons = st.tabs(
        [
            "🥋 User Admin",
            "📅 Class Schedule",
            "🏢 Gyms & Types",
            "🗓️ Terms",
            "🎯 Targets",
            "📚 Lessons",
        ]
    )

    # --- 1. USER ADMIN ---
    with tab_user:
        st.header("🥋 Member Administration")

        # 1. Fetch Fresh Data
        try:
            u_res = requests.get(f"{BASE_URL}/users/")
            if u_res.status_code == 200:
                all_users = u_res.json()

                if not all_users:
                    st.info(
                        "No members found in the database. Add them via the main dashboard."
                    )
                else:
                    # Layout: Search and Table at the top
                    df_u = pd.DataFrame(all_users)

                    col_search, col_stats = st.columns([2, 1])
                    with col_search:
                        search_query = st.text_input(
                            "🔍 Search Members",
                            placeholder="Filter by name, rank, or email...",
                        )

                    # Filter logic for the table
                    if search_query:
                        mask = df_u.apply(
                            lambda row: row.astype(str)
                            .str.contains(search_query, case=False)
                            .any(),
                            axis=1,
                        )
                        df_u = df_u[mask]

                    with col_stats:
                        st.metric("Total Active Members", len(all_users))

                    # Display Table
                    st.dataframe(
                        df_u[
                            ["first_name", "last_name", "rank", "email", "created_date"]
                        ],
                        width="stretch",
                        hide_index=True,
                    )

                    st.divider()

                    # 2. Update Section
                    st.subheader("📝 Modify Member Profile")
                    st.caption(
                        "Updating a member will archive their current record and create a new version to maintain history."
                    )

                    # Map names for the selection process
                    user_map = {
                        f"{u['first_name']} {u['last_name']} ({u['rank']})": u
                        for u in all_users
                    }

                    selected_user_key = st.selectbox(
                        "Select a member to edit:",
                        options=["-- Select Member --"] + list(user_map.keys()),
                    )

                    if selected_user_key != "-- Select Member --":
                        member = user_map[selected_user_key]

                        with st.form("edit_member_form"):
                            c1, c2 = st.columns(2)

                            # Pre-populated fields
                            up_first = c1.text_input(
                                "First Name", value=member["first_name"]
                            )
                            up_last = c2.text_input(
                                "Last Name", value=member["last_name"]
                            )

                            ranks = ["White", "Blue", "Purple", "Brown", "Black"]
                            # Safe index lookup
                            try:
                                rank_idx = ranks.index(member["rank"])
                            except ValueError:
                                rank_idx = 0

                            up_rank = c1.selectbox(
                                "Current Rank", options=ranks, index=rank_idx
                            )
                            up_email = c2.text_input(
                                "Email Address", value=member["email"]
                            )

                            up_nick = st.text_input(
                                "Nicknames (Optional)",
                                value=member.get("nicknames", ""),
                            )

                            # Form Submission
                            submit_update = st.form_submit_button(
                                "Save Changes & Archive History"
                            )

                            if submit_update:
                                # We keep the user_uuid the same so attendance history links up
                                update_data = {
                                    "uuid": member["user_uuid"],
                                    "first_name": up_first,
                                    "last_name": up_last,
                                    "rank": up_rank,
                                    "email": up_email,
                                    "nicknames": up_nick,
                                }
                                handle_request("PUT", "users", update_data)

                        # --- ROLE MANAGEMENT SECTION ---
                        st.divider()
                        st.subheader("👤 Role Management")

                        # Fetch current roles
                        roles_res = requests.get(
                            f"{BASE_URL}/roles/user/{member['user_uuid']}"
                        )
                        current_roles = (
                            roles_res.json() if roles_res.status_code == 200 else []
                        )

                        # Display current roles as badges
                        if current_roles:
                            role_names = [r["role_name"] for r in current_roles]
                            st.info(f"**Current Roles:** {' • '.join(role_names)}")
                        else:
                            st.warning("No roles assigned")

                        # Role assignment form
                        all_roles_res = requests.get(f"{BASE_URL}/roles/")
                        all_roles = (
                            all_roles_res.json()
                            if all_roles_res.status_code == 200
                            else []
                        )

                        with st.form("role_assignment_form"):
                            st.caption("Select all roles this member should have")

                            # Create checkboxes with unique keys for session state
                            for role in all_roles:
                                is_current = any(
                                    r["role_id"] == role["id"] for r in current_roles
                                )
                                # Checkbox state will be stored in session_state with the key
                                st.checkbox(
                                    f"{role['name']} - {role['description']}",
                                    value=is_current,
                                    key=f"role_{role['id']}_{member['user_uuid']}",
                                )

                            submit_roles = st.form_submit_button("Update Roles")

                            # Handle submission INSIDE the form context
                            if submit_roles:
                                # Collect selected role IDs from session state
                                selected_role_ids = [
                                    role["id"]
                                    for role in all_roles
                                    if st.session_state.get(f"role_{role['id']}_{member['user_uuid']}", False)
                                ]

                                update_payload = {"role_ids": selected_role_ids}
                                try:
                                    update_res = requests.put(
                                        f"{BASE_URL}/roles/user/{member['user_uuid']}",
                                        json=update_payload,
                                    )
                                    if update_res.status_code == 200:
                                        st.success("✅ Roles updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Error: {update_res.json().get('detail', 'Unknown error')}"
                                        )
                                except Exception as e:
                                    st.error(f"Connection failed: {e}")

                        # Role history (collapsible)
                        with st.expander("📜 View Role History"):
                            history_res = requests.get(
                                f"{BASE_URL}/roles/user/{member['user_uuid']}/history"
                            )
                            if history_res.status_code == 200:
                                history_data = history_res.json()
                                history_df = pd.DataFrame(history_data["history"])

                                if not history_df.empty:
                                    # Format dates
                                    history_df["effective_date"] = pd.to_datetime(
                                        history_df["effective_date"]
                                    ).dt.strftime("%Y-%m-%d %H:%M")
                                    history_df["end_date"] = history_df[
                                        "end_date"
                                    ].apply(
                                        lambda x: pd.to_datetime(x).strftime(
                                            "%Y-%m-%d %H:%M"
                                        )
                                        if x
                                        else "Present"
                                    )

                                    display_df = history_df[
                                        [
                                            "role_name",
                                            "effective_date",
                                            "end_date",
                                            "is_current",
                                        ]
                                    ]
                                    display_df.columns = [
                                        "Role",
                                        "Assigned Date",
                                        "Removed Date",
                                        "Current",
                                    ]

                                    st.dataframe(
                                        display_df, hide_index=True, width="stretch"
                                    )
                                else:
                                    st.info("No role history available")
            else:
                st.error(f"Error fetching users: {u_res.text}")

        except Exception as e:
            st.error(f"Connection Error: {e}")

    # --- 2. CLASS SCHEDULE ---
    with tab_class:
        st.header("Class Management")

        # Fetch prerequisite data
        try:
            gyms = requests.get(f"{BASE_URL}/gyms/").json()
            types = requests.get(f"{BASE_URL}/class-types/").json()
            classes = requests.get(f"{BASE_URL}/classes/").json()

            gym_opts = {g["name"]: g["id"] for g in gyms}
            type_opts = {t["name"]: t["id"] for t in types}

            with st.expander("➕ Add New Class to Timetable"):
                if not gym_opts or not type_opts:
                    st.warning("Please add a Gym Location and Class Type first.")
                else:
                    with st.form("new_class_form"):
                        c_name = st.text_input("Class Name")
                        c_day = st.selectbox(
                            "Day",
                            [
                                "Monday",
                                "Tuesday",
                                "Wednesday",
                                "Thursday",
                                "Friday",
                                "Saturday",
                                "Sunday",
                            ],
                        )
                        c_time = st.text_input("Time (e.g., 18:00)")
                        c_wght = st.number_input("Weighting", value=1.0)
                        c_gym = st.selectbox(
                            "Gym Location", options=list(gym_opts.keys())
                        )
                        c_typ = st.selectbox(
                            "Class Type", options=list(type_opts.keys())
                        )

                        if st.form_submit_button("Create Class"):
                            handle_request(
                                "POST",
                                "classes",
                                {
                                    "class_name": c_name,
                                    "day": c_day,
                                    "time": c_time,
                                    "weighting": c_wght,
                                    "gym_id": gym_opts[c_gym],
                                    "class_type_id": type_opts[c_typ],
                                },
                            )

            if classes:
                st.subheader("Current Active Schedule")
                st.dataframe(
                    pd.DataFrame(classes)[["class_name", "day", "time", "weighting"]],
                    width="stretch",
                    hide_index=True,
                )
        except Exception as e:
            st.error(f"Schedule Fetch Error: {e}")

    # --- 3. GYMS & TYPES ---
    with tab_gym_types:
        col_g, col_t = st.columns(2)

        with col_g:
            st.header("Gym Locations")
            with st.form("gym_form"):
                g_name = st.text_input("Location Name")
                g_addr = st.text_input("Address")
                if st.form_submit_button("Add Gym"):
                    handle_request("POST", "gyms", {"name": g_name, "address": g_addr})

            # Display existing
            g_res = requests.get(f"{BASE_URL}/gyms/")
            if g_res.status_code == 200:
                st.dataframe(
                    pd.DataFrame(g_res.json()), width="stretch", hide_index=True
                )

        with col_t:
            st.header("Class Types")
            with st.form("type_form"):
                t_name = st.text_input("Type (e.g., No-Gi)")
                if st.form_submit_button("Add Type"):
                    handle_request("POST", "class-types", {"name": t_name})

            # Display existing
            t_res = requests.get(f"{BASE_URL}/class-types/")
            if t_res.status_code == 200:
                st.dataframe(
                    pd.DataFrame(t_res.json()), width="stretch", hide_index=True
                )

    # --- 4. TERMS ---
    with tab_terms:
        st.header("Term Management")
        with st.form("term_form"):
            term_n = st.text_input("Term Name (e.g. Q1 2026)")
            s_date = st.date_input("Start Date")
            e_date = st.date_input("End Date")
            if st.form_submit_button("Create Term"):
                handle_request(
                    "POST",
                    "terms",
                    {
                        "term_name": term_n,
                        "start_date": str(s_date),
                        "end_date": str(e_date),
                    },
                )

        term_res = requests.get(f"{BASE_URL}/terms/")
        if term_res.status_code == 200:
            st.dataframe(
                pd.DataFrame(term_res.json()), width="stretch", hide_index=True
            )

    # --- 5. PERFORMANCE TARGETS ---
    with tab_targets:
        st.header("Mat Hour Targets")
        terms_res = requests.get(f"{BASE_URL}/terms/")
        if terms_res.status_code == 200 and terms_res.json():
            term_map = {t["term_name"]: t["id"] for t in terms_res.json()}
            with st.form("target_form"):
                t_term = st.selectbox("Term", list(term_map.keys()))
                t_rank = st.selectbox(
                    "Target Rank", ["White", "Blue", "Purple", "Brown", "Black"]
                )
                t_val = st.number_input("Hours Required", min_value=0.0)
                if st.form_submit_button("Set Target"):
                    handle_request(
                        "POST",
                        "term-targets",
                        {"term_id": term_map[t_term], "rank": t_rank, "target": t_val},
                    )

            # Display existing
            targ_res = requests.get(f"{BASE_URL}/term-targets/")
            if targ_res.status_code == 200:
                st.dataframe(
                    pd.DataFrame(targ_res.json()), width="stretch", hide_index=True
                )
        else:
            st.warning("Create a Term first before setting targets.")

    # --- 6. LESSONS MANAGEMENT ---
    with tab_lessons:
        st.header("📚 Lesson Management")
        st.caption(
            "Manage lesson plans and video resources for class instances (class + date)"
        )

        # Fetch prerequisites
        try:
            classes = requests.get(f"{BASE_URL}/classes/").json()
            teachers_res = requests.get(f"{BASE_URL}/roles/users/by-role/Teacher")
            teachers = teachers_res.json() if teachers_res.status_code == 200 else []

            # Check if classes exist
            if not classes:
                st.warning(
                    "⚠️ No classes found. Please create a class in the 'Class Schedule' tab first."
                )
            else:
                # Create/Update Lesson Form
                with st.expander("➕ Add/Update Lesson", expanded=True):
                    with st.form("lesson_form"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            class_opts = {
                                f"{c['class_name']} ({c['day']} {c['time']})": c["id"]
                                for c in classes
                            }
                            selected_class = st.selectbox(
                                "Select Class", options=list(class_opts.keys())
                            )
                            class_id = class_opts[selected_class]

                        with col2:
                            lesson_date = st.date_input(
                                "Class Date", value=date.today()
                            )

                        with col3:
                            teacher_opts = {"-- No Teacher --": None}
                            if teachers:
                                teacher_opts.update(
                                    {
                                        f"{t['first_name']} {t['last_name']}": t[
                                            "user_uuid"
                                        ]
                                        for t in teachers
                                    }
                                )
                            selected_teacher = st.selectbox(
                                "Assign Teacher", options=list(teacher_opts.keys())
                            )
                            teacher_uuid = teacher_opts[selected_teacher]

                        lesson_title = st.text_input(
                            "Lesson Title (Optional)",
                            placeholder="e.g., Fundamentals - Guard Passing",
                        )

                        col_url1, col_url2 = st.columns(2)
                        with col_url1:
                            lesson_plan_url = st.text_input(
                                "Lesson Plan URL (Optional)",
                                placeholder="https://docs.google.com/document/...",
                                help="Enter a valid URL (Google Docs, Dropbox, etc.)",
                            )

                        with col_url2:
                            video_folder_url = st.text_input(
                                "Video Folder URL (Optional)",
                                placeholder="https://drive.google.com/drive/folders/...",
                                help="Enter a valid URL to video resources",
                            )

                        submit_lesson = st.form_submit_button("Save Lesson")

                        if submit_lesson:
                            # Build payload
                            payload = {
                                "class_id": class_id,
                                "class_date": str(lesson_date),
                                "teacher_uuid": teacher_uuid,
                                "lesson_title": lesson_title if lesson_title else None,
                                "lesson_plan_url": lesson_plan_url
                                if lesson_plan_url
                                else None,
                                "video_folder_url": video_folder_url
                                if video_folder_url
                                else None,
                            }

                            try:
                                res = requests.post(
                                    f"{BASE_URL}/class-instances/", json=payload
                                )
                                if res.status_code == 200:
                                    st.success("✅ Lesson saved successfully!")
                                    st.rerun()
                                else:
                                    detail = res.json().get("detail", "Unknown error")
                                    st.error(f"❌ Error: {detail}")
                            except Exception as e:
                                st.error(f"⚠️ Connection failed: {e}")

                st.divider()

                # Display existing lessons
                st.subheader("📋 Current Lessons")

                # Filters
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    filter_class = st.selectbox(
                        "Filter by Class",
                        options=["-- All Classes --"] + list(class_opts.keys()),
                        key="filter_class",
                    )
                with col_f2:
                    filter_start = st.date_input(
                        "From Date",
                        value=date.today().replace(day=1),
                        key="filter_start",
                    )
                with col_f3:
                    filter_end = st.date_input(
                        "To Date", value=date.today(), key="filter_end"
                    )

                # Fetch lessons with filters
                params = {}
                if filter_class != "-- All Classes --":
                    params["class_id"] = class_opts[filter_class]
                if filter_start:
                    params["start_date"] = str(filter_start)
                if filter_end:
                    params["end_date"] = str(filter_end)

                lessons_res = requests.get(
                    f"{BASE_URL}/class-instances/", params=params
                )

                if lessons_res.status_code == 200:
                    lessons = lessons_res.json()

                    if lessons:
                        # Display as table
                        lessons_df = pd.DataFrame(lessons)

                        # Format display
                        display_df = lessons_df[
                            [
                                "class_name",
                                "class_date",
                                "teacher_name",
                                "lesson_title",
                                "id",
                            ]
                        ].copy()
                        display_df.columns = [
                            "Class",
                            "Date",
                            "Teacher",
                            "Lesson Title",
                            "ID",
                        ]
                        display_df["Date"] = pd.to_datetime(
                            display_df["Date"]
                        ).dt.strftime("%Y-%m-%d")

                        # Fill NaN values
                        display_df = display_df.fillna("--")

                        st.dataframe(
                            display_df.drop(columns=["ID"]),
                            width="stretch",
                            hide_index=True,
                        )

                        st.divider()

                        # Edit/Delete section
                        st.subheader("✏️ Edit or Delete Lesson")
                        lesson_map = {
                            f"{row['Class']} - {row['Date']}": row["ID"]
                            for _, row in display_df.iterrows()
                        }
                        selected_lesson = st.selectbox(
                            "Select a lesson to edit or delete:",
                            options=["-- Select Lesson --"] + list(lesson_map.keys()),
                        )

                        if selected_lesson != "-- Select Lesson --":
                            lesson_id = lesson_map[selected_lesson]

                            # Fetch lesson details
                            lesson_detail_res = requests.get(
                                f"{BASE_URL}/class-instances/{lesson_id}"
                            )
                            if lesson_detail_res.status_code == 200:
                                lesson_detail = lesson_detail_res.json()

                                col_btn1, col_btn2 = st.columns(2)

                                with col_btn1:
                                    if st.button("🗑️ Delete Lesson", type="secondary"):
                                        try:
                                            del_res = requests.delete(
                                                f"{BASE_URL}/class-instances/{lesson_id}"
                                            )
                                            if del_res.status_code == 200:
                                                st.success("✅ Lesson deleted!")
                                                st.rerun()
                                            else:
                                                detail = del_res.json().get(
                                                    "detail", "Unknown error"
                                                )
                                                st.error(f"❌ Error: {detail}")
                                        except Exception as e:
                                            st.error(f"⚠️ Connection failed: {e}")

                                # Show current details
                                st.info(f"**Current Details:**")
                                st.write(
                                    f"- **Teacher:** {lesson_detail.get('teacher_name', 'Not assigned')}"
                                )
                                st.write(
                                    f"- **Lesson Title:** {lesson_detail.get('lesson_title', 'None')}"
                                )
                                if lesson_detail.get("lesson_plan_url"):
                                    st.write(
                                        f"- **Lesson Plan:** {lesson_detail.get('lesson_plan_url')}"
                                    )
                                if lesson_detail.get("video_folder_url"):
                                    st.write(
                                        f"- **Video Folder:** {lesson_detail.get('video_folder_url')}"
                                    )

                    else:
                        st.info("ℹ️ No lessons found for the selected filters.")
                        st.caption(
                            "Create a lesson using the form above or adjust your filters."
                        )
                else:
                    st.error(f"❌ Failed to fetch lessons: {lessons_res.status_code}")

        except Exception as e:
            st.error(f"⚠️ Connection error: {e}")

    st.success("Welcome, Admin")
    # tab_user, tab_class, etc...
else:
    st.stop()  # Prevents the rest of the page from running
