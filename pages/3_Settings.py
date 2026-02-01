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

                            # Last Graded Date field
                            from datetime import datetime as dt

                            last_graded_val = None
                            if member.get("last_graded_date"):
                                try:
                                    last_graded_val = dt.fromisoformat(
                                        member["last_graded_date"].replace(
                                            "Z", "+00:00"
                                        )
                                    ).date()
                                except:
                                    pass

                            up_last_graded = c1.date_input(
                                "Last Graded Date (Optional)",
                                value=last_graded_val,
                                help="Date of most recent belt promotion",
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
                                    "last_graded_date": up_last_graded.isoformat()
                                    if up_last_graded
                                    else None,
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
                                    if st.session_state.get(
                                        f"role_{role['id']}_{member['user_uuid']}",
                                        False,
                                    )
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

    # --- 6. CURRICULUM & LESSONS MANAGEMENT ---
    with tab_lessons:
        st.header("📚 Curriculum & Lesson Management")
        st.caption(
            "Create curricula for each class, build lesson libraries, and assign lessons to specific dates"
        )

        # Fetch prerequisites
        try:
            classes = requests.get(f"{BASE_URL}/classes/").json()
            curricula = requests.get(f"{BASE_URL}/curricula/").json()

            # Check if classes exist
            if not classes:
                st.warning(
                    "⚠️ No classes found. Please create a class in the 'Class Schedule' tab first."
                )
            else:
                # Create sub-tabs for Curriculum, Lessons, Assignment, and Teachers
                subtab_curr, subtab_lib, subtab_assign, subtab_teachers = st.tabs(
                    [
                        "📖 Curricula",
                        "📝 Lesson Library",
                        "📅 Assign to Dates",
                        "👨‍🏫 Teacher Assignments",
                    ]
                )

                # --- SUBTAB 1: CURRICULUM MANAGEMENT ---
                with subtab_curr:
                    st.subheader("Curriculum Management")
                    st.caption(
                        "Each class has exactly one curriculum containing all its lessons"
                    )

                    # Create curriculum form
                    with st.expander("➕ Create Curriculum for Class", expanded=False):
                        # Find classes without curricula
                        curricula_class_ids = [c["class_id"] for c in curricula]
                        classes_without_curr = [
                            c for c in classes if c["id"] not in curricula_class_ids
                        ]

                        if not classes_without_curr:
                            st.info("✅ All classes already have curricula")
                        else:
                            with st.form("curriculum_form"):
                                class_opts = {
                                    f"{c['class_name']} ({c['day']} {c['time']})": c[
                                        "id"
                                    ]
                                    for c in classes_without_curr
                                }
                                selected_class = st.selectbox(
                                    "Select Class", options=list(class_opts.keys())
                                )
                                class_id = class_opts[selected_class]

                                curr_name = st.text_input(
                                    "Curriculum Name (Optional)",
                                    placeholder="Leave blank for auto-generated name",
                                    help="Will auto-generate as '[Class Name] Curriculum' if not provided",
                                )

                                curr_desc = st.text_area(
                                    "Description (Optional)",
                                    placeholder="Describe the learning objectives and structure...",
                                )

                                submit_curr = st.form_submit_button("Create Curriculum")

                                if submit_curr:
                                    payload = {
                                        "class_id": class_id,
                                        "name": curr_name if curr_name else None,
                                        "description": curr_desc if curr_desc else None,
                                    }

                                    try:
                                        res = requests.post(
                                            f"{BASE_URL}/curricula/", json=payload
                                        )
                                        if res.status_code == 200:
                                            st.success("✅ Curriculum created!")
                                            st.rerun()
                                        else:
                                            detail = res.json().get(
                                                "detail", "Unknown error"
                                            )
                                            st.error(f"❌ Error: {detail}")
                                    except Exception as e:
                                        st.error(f"⚠️ Connection failed: {e}")

                    # Display existing curricula
                    if curricula:
                        st.divider()
                        st.subheader("📋 Existing Curricula")

                        # Enrich with class names
                        class_map = {c["id"]: c for c in classes}
                        for curr in curricula:
                            curr["class_name"] = class_map.get(
                                curr["class_id"], {}
                            ).get("class_name", "Unknown")

                        curr_df = pd.DataFrame(curricula)
                        display_curr = curr_df[
                            ["class_name", "name", "description", "id"]
                        ].copy()
                        display_curr.columns = ["Class", "Name", "Description", "ID"]
                        display_curr["Description"] = display_curr[
                            "Description"
                        ].fillna("--")

                        st.dataframe(
                            display_curr.drop(columns=["ID"]),
                            width="stretch",
                            hide_index=True,
                        )

                        # Edit/Delete curriculum
                        with st.expander("✏️ Edit or Delete Curriculum"):
                            curr_map = {
                                f"{row['Class']} - {row['Name']}": row["ID"]
                                for _, row in display_curr.iterrows()
                            }
                            selected_curr = st.selectbox(
                                "Select curriculum:",
                                options=["-- Select --"] + list(curr_map.keys()),
                            )

                            if selected_curr != "-- Select --":
                                curr_id = curr_map[selected_curr]

                                # Fetch curriculum details
                                curr_detail_res = requests.get(
                                    f"{BASE_URL}/curricula/{curr_id}"
                                )
                                if curr_detail_res.status_code == 200:
                                    curr_detail = curr_detail_res.json()

                                    # Edit form
                                    with st.form("edit_curriculum_form"):
                                        edit_name = st.text_input(
                                            "Name", value=curr_detail.get("name", "")
                                        )
                                        edit_desc = st.text_area(
                                            "Description",
                                            value=curr_detail.get("description", ""),
                                        )

                                        if st.form_submit_button("Update Curriculum"):
                                            update_payload = {
                                                "name": edit_name
                                                if edit_name
                                                else None,
                                                "description": edit_desc
                                                if edit_desc
                                                else None,
                                            }

                                            try:
                                                update_res = requests.put(
                                                    f"{BASE_URL}/curricula/{curr_id}",
                                                    json=update_payload,
                                                )
                                                if update_res.status_code == 200:
                                                    st.success("✅ Curriculum updated!")
                                                    st.rerun()
                                                else:
                                                    detail = update_res.json().get(
                                                        "detail", "Unknown error"
                                                    )
                                                    st.error(f"❌ Error: {detail}")
                                            except Exception as e:
                                                st.error(f"⚠️ Connection failed: {e}")

                                    # Delete button
                                    if st.button(
                                        "🗑️ Delete Curriculum", type="secondary"
                                    ):
                                        try:
                                            del_res = requests.delete(
                                                f"{BASE_URL}/curricula/{curr_id}"
                                            )
                                            if del_res.status_code == 200:
                                                st.success("✅ Curriculum deleted!")
                                                st.rerun()
                                            else:
                                                detail = del_res.json().get(
                                                    "detail", "Unknown error"
                                                )
                                                st.error(f"❌ Error: {detail}")
                                        except Exception as e:
                                            st.error(f"⚠️ Connection failed: {e}")

                    else:
                        st.info("ℹ️ No curricula created yet")

                # --- SUBTAB 2: LESSON LIBRARY ---
                with subtab_lib:
                    st.subheader("Lesson Library")
                    st.caption(
                        "Create reusable lesson templates that can be assigned to class dates"
                    )

                    if not curricula:
                        st.warning(
                            "⚠️ No curricula found. Create a curriculum first in the 'Curricula' tab."
                        )
                    else:
                        # Create lesson form
                        with st.expander("➕ Create New Lesson", expanded=False):
                            with st.form("create_lesson_form"):
                                # Curriculum selection
                                curr_opts = {
                                    f"{c['class_name']} - {c['name']}": c["id"]
                                    for c in curricula
                                }
                                selected_curr = st.selectbox(
                                    "Curriculum", options=list(curr_opts.keys())
                                )
                                curriculum_id = curr_opts[selected_curr]

                                lesson_title = st.text_input(
                                    "Lesson Title*",
                                    placeholder="e.g., Guard Passing Fundamentals",
                                )

                                lesson_desc = st.text_area(
                                    "Description (Optional)",
                                    placeholder="Describe the techniques and concepts covered...",
                                )

                                col_url1, col_url2 = st.columns(2)
                                with col_url1:
                                    lesson_plan_url = st.text_input(
                                        "Lesson Plan URL (Optional)",
                                        placeholder="https://docs.google.com/document/...",
                                    )

                                with col_url2:
                                    video_folder_url = st.text_input(
                                        "Video Folder URL (Optional)",
                                        placeholder="https://drive.google.com/drive/...",
                                    )

                                submit_new_lesson = st.form_submit_button(
                                    "Create Lesson"
                                )

                                if submit_new_lesson:
                                    if not lesson_title:
                                        st.error("❌ Lesson title is required")
                                    else:
                                        payload = {
                                            "curriculum_id": curriculum_id,
                                            "title": lesson_title,
                                            "description": lesson_desc
                                            if lesson_desc
                                            else None,
                                            "lesson_plan_url": lesson_plan_url
                                            if lesson_plan_url
                                            else None,
                                            "video_folder_url": video_folder_url
                                            if video_folder_url
                                            else None,
                                        }

                                        try:
                                            res = requests.post(
                                                f"{BASE_URL}/lessons/", json=payload
                                            )
                                            if res.status_code == 200:
                                                st.success("✅ Lesson created!")
                                                st.rerun()
                                            else:
                                                detail = res.json().get(
                                                    "detail", "Unknown error"
                                                )
                                                st.error(f"❌ Error: {detail}")
                                        except Exception as e:
                                            st.error(f"⚠️ Connection failed: {e}")

                        # Display lesson library
                        st.divider()
                        st.subheader("📚 Lesson Library")

                        # Filter by curriculum
                        curr_filter_opts = ["-- All Curricula --"] + list(
                            curr_opts.keys()
                        )
                        filter_curr = st.selectbox(
                            "Filter by Curriculum",
                            options=curr_filter_opts,
                            key="filter_curr",
                        )

                        # Fetch lessons
                        params = {}
                        if filter_curr != "-- All Curricula --":
                            params["curriculum_id"] = curr_opts[filter_curr]

                        lessons_res = requests.get(
                            f"{BASE_URL}/lessons/", params=params
                        )

                        if lessons_res.status_code == 200:
                            lessons = lessons_res.json()

                            if lessons:
                                # Enrich with curriculum names
                                curr_name_map = {c["id"]: c for c in curricula}
                                for lesson in lessons:
                                    curr_info = curr_name_map.get(
                                        lesson["curriculum_id"], {}
                                    )
                                    lesson["curriculum_name"] = curr_info.get(
                                        "name", "Unknown"
                                    )
                                    lesson["class_name"] = curr_info.get(
                                        "class_name", "Unknown"
                                    )

                                lessons_df = pd.DataFrame(lessons)
                                display_lessons = lessons_df[
                                    [
                                        "class_name",
                                        "curriculum_name",
                                        "title",
                                        "description",
                                        "id",
                                    ]
                                ].copy()
                                display_lessons.columns = [
                                    "Class",
                                    "Curriculum",
                                    "Title",
                                    "Description",
                                    "ID",
                                ]
                                display_lessons["Description"] = display_lessons[
                                    "Description"
                                ].fillna("--")

                                st.dataframe(
                                    display_lessons.drop(columns=["ID"]),
                                    width="stretch",
                                    hide_index=True,
                                )

                                # Edit/Delete lesson
                                with st.expander("✏️ Edit or Delete Lesson"):
                                    lesson_map = {
                                        f"{row['Class']} - {row['Title']}": row["ID"]
                                        for _, row in display_lessons.iterrows()
                                    }
                                    selected_lesson = st.selectbox(
                                        "Select lesson:",
                                        options=["-- Select --"]
                                        + list(lesson_map.keys()),
                                        key="edit_lesson_select",
                                    )

                                    if selected_lesson != "-- Select --":
                                        lesson_id = lesson_map[selected_lesson]

                                        # Fetch lesson details
                                        lesson_detail_res = requests.get(
                                            f"{BASE_URL}/lessons/{lesson_id}"
                                        )
                                        if lesson_detail_res.status_code == 200:
                                            lesson_detail = lesson_detail_res.json()

                                            # Edit form
                                            with st.form("edit_lesson_form"):
                                                edit_title = st.text_input(
                                                    "Title",
                                                    value=lesson_detail.get(
                                                        "title", ""
                                                    ),
                                                )
                                                edit_desc = st.text_area(
                                                    "Description",
                                                    value=lesson_detail.get(
                                                        "description", ""
                                                    ),
                                                )
                                                edit_plan_url = st.text_input(
                                                    "Lesson Plan URL",
                                                    value=lesson_detail.get(
                                                        "lesson_plan_url", ""
                                                    ),
                                                )
                                                edit_video_url = st.text_input(
                                                    "Video Folder URL",
                                                    value=lesson_detail.get(
                                                        "video_folder_url", ""
                                                    ),
                                                )

                                                if st.form_submit_button(
                                                    "Update Lesson"
                                                ):
                                                    update_payload = {
                                                        "title": edit_title
                                                        if edit_title
                                                        else None,
                                                        "description": edit_desc
                                                        if edit_desc
                                                        else None,
                                                        "lesson_plan_url": edit_plan_url
                                                        if edit_plan_url
                                                        else None,
                                                        "video_folder_url": edit_video_url
                                                        if edit_video_url
                                                        else None,
                                                    }

                                                    try:
                                                        update_res = requests.put(
                                                            f"{BASE_URL}/lessons/{lesson_id}",
                                                            json=update_payload,
                                                        )
                                                        if (
                                                            update_res.status_code
                                                            == 200
                                                        ):
                                                            st.success(
                                                                "✅ Lesson updated!"
                                                            )
                                                            st.rerun()
                                                        else:
                                                            detail = (
                                                                update_res.json().get(
                                                                    "detail",
                                                                    "Unknown error",
                                                                )
                                                            )
                                                            st.error(
                                                                f"❌ Error: {detail}"
                                                            )
                                                    except Exception as e:
                                                        st.error(
                                                            f"⚠️ Connection failed: {e}"
                                                        )

                                            # Delete button (outside form)
                                            if st.button(
                                                "🗑️ Delete Lesson", type="secondary"
                                            ):
                                                try:
                                                    del_res = requests.delete(
                                                        f"{BASE_URL}/lessons/{lesson_id}"
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
                                                    st.error(
                                                        f"⚠️ Connection failed: {e}"
                                                    )
                            else:
                                st.info("ℹ️ No lessons in library yet")
                        else:
                            st.error(
                                f"❌ Failed to fetch lessons: {lessons_res.status_code}"
                            )

                # --- SUBTAB 3: ASSIGN LESSONS TO DATES ---
                with subtab_assign:
                    st.subheader("Assign Lessons to Class Dates")
                    st.caption("Link curriculum lessons to specific class instances")

                    if not curricula:
                        st.warning("⚠️ No curricula found. Create a curriculum first.")
                    else:
                        # Assignment form
                        with st.expander("📅 Assign Lesson to Date", expanded=True):
                            with st.form("assign_lesson_form"):
                                col1, col2 = st.columns(2)

                                with col1:
                                    class_opts = {
                                        f"{c['class_name']} ({c['day']} {c['time']})": c[
                                            "id"
                                        ]
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

                                # Find curriculum for selected class
                                class_curriculum = next(
                                    (c for c in curricula if c["class_id"] == class_id),
                                    None,
                                )

                                if not class_curriculum:
                                    st.warning(
                                        f"⚠️ No curriculum exists for this class. Create one first in the 'Curricula' tab."
                                    )
                                    lesson_opts = {}
                                else:
                                    # Fetch lessons for this curriculum
                                    curr_lessons_res = requests.get(
                                        f"{BASE_URL}/lessons/",
                                        params={
                                            "curriculum_id": class_curriculum["id"]
                                        },
                                    )

                                    if (
                                        curr_lessons_res.status_code == 200
                                        and curr_lessons_res.json()
                                    ):
                                        curr_lessons = curr_lessons_res.json()
                                        lesson_opts = {
                                            lesson["title"]: lesson["id"]
                                            for lesson in curr_lessons
                                        }

                                        selected_lesson_title = st.selectbox(
                                            "Select Lesson from Curriculum",
                                            options=["-- None --"]
                                            + list(lesson_opts.keys()),
                                        )
                                    else:
                                        st.info(
                                            "ℹ️ No lessons in this curriculum yet. Create lessons in the 'Lesson Library' tab."
                                        )
                                        lesson_opts = {}

                                submit_assign = st.form_submit_button("Assign Lesson")

                                if submit_assign:
                                    lesson_id = None
                                    if (
                                        lesson_opts
                                        and selected_lesson_title != "-- None --"
                                    ):
                                        lesson_id = lesson_opts.get(
                                            selected_lesson_title
                                        )

                                    payload = {
                                        "class_id": class_id,
                                        "class_date": str(lesson_date),
                                        "lesson_id": lesson_id,
                                        "teacher_uuid": None,
                                    }

                                    try:
                                        res = requests.post(
                                            f"{BASE_URL}/class-instances/", json=payload
                                        )
                                        if res.status_code == 200:
                                            st.success("✅ Lesson assigned to date!")
                                            st.rerun()
                                        else:
                                            detail = res.json().get(
                                                "detail", "Unknown error"
                                            )
                                            st.error(f"❌ Error: {detail}")
                                    except Exception as e:
                                        st.error(f"⚠️ Connection failed: {e}")

                        st.divider()

                        # Display assigned lessons
                        st.subheader("📋 Assigned Lessons")

                        # Filters
                        col_f1, col_f2, col_f3 = st.columns(3)
                        with col_f1:
                            class_opts_all = {
                                f"{c['class_name']} ({c['day']} {c['time']})": c["id"]
                                for c in classes
                            }
                            filter_class = st.selectbox(
                                "Filter by Class",
                                options=["-- All Classes --"]
                                + list(class_opts_all.keys()),
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

                        # Fetch class instances with filters
                        params = {}
                        if filter_class != "-- All Classes --":
                            params["class_id"] = class_opts_all[filter_class]
                        if filter_start:
                            params["start_date"] = str(filter_start)
                        if filter_end:
                            params["end_date"] = str(filter_end)

                        instances_res = requests.get(
                            f"{BASE_URL}/class-instances/", params=params
                        )

                        if instances_res.status_code == 200:
                            instances = instances_res.json()

                            if instances:
                                instances_df = pd.DataFrame(instances)

                                # Format display
                                display_df = instances_df[
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
                                    "Lesson",
                                    "ID",
                                ]
                                display_df["Date"] = pd.to_datetime(
                                    display_df["Date"]
                                ).dt.strftime("%Y-%m-%d")
                                display_df["Teacher"] = display_df["Teacher"].fillna(
                                    "Not Assigned"
                                )
                                display_df["Lesson"] = display_df["Lesson"].fillna(
                                    "-- Not Assigned --"
                                )

                                st.dataframe(
                                    display_df.drop(columns=["ID"]),
                                    width="stretch",
                                    hide_index=True,
                                )

                                # Edit/Unassign lesson
                                with st.expander("✏️ Edit Assignment"):
                                    instance_map = {
                                        f"{row['Class']} - {row['Date']}": row["ID"]
                                        for _, row in display_df.iterrows()
                                    }
                                    selected_instance = st.selectbox(
                                        "Select class instance:",
                                        options=["-- Select --"]
                                        + list(instance_map.keys()),
                                        key="edit_instance_select",
                                    )

                                    if selected_instance != "-- Select --":
                                        instance_id = instance_map[selected_instance]

                                        # Fetch instance details
                                        instance_detail_res = requests.get(
                                            f"{BASE_URL}/class-instances/{instance_id}"
                                        )
                                        if instance_detail_res.status_code == 200:
                                            instance_detail = instance_detail_res.json()

                                            # Show current assignment
                                            current_lesson = instance_detail.get(
                                                "lesson_title", "Not assigned"
                                            )
                                            st.info(
                                                f"**Current Lesson:** {current_lesson}"
                                            )

                                            # Re-assignment or unassignment
                                            col_btn1, col_btn2 = st.columns(2)

                                            with col_btn1:
                                                if st.button(
                                                    "🗑️ Remove Lesson Assignment",
                                                    type="secondary",
                                                ):
                                                    try:
                                                        update_res = requests.put(
                                                            f"{BASE_URL}/class-instances/{instance_id}",
                                                            json={"lesson_id": None},
                                                        )
                                                        if (
                                                            update_res.status_code
                                                            == 200
                                                        ):
                                                            st.success(
                                                                "✅ Lesson unassigned!"
                                                            )
                                                            st.rerun()
                                                        else:
                                                            detail = (
                                                                update_res.json().get(
                                                                    "detail",
                                                                    "Unknown error",
                                                                )
                                                            )
                                                            st.error(
                                                                f"❌ Error: {detail}"
                                                            )
                                                    except Exception as e:
                                                        st.error(
                                                            f"⚠️ Connection failed: {e}"
                                                        )
                            else:
                                st.info("ℹ️ No class instances found")
                                st.caption(
                                    "Class instances are created when students check in or when you assign a lesson"
                                )
                        else:
                            st.error(
                                f"❌ Failed to fetch instances: {instances_res.status_code}"
                            )

                # --- SUBTAB 4: TEACHER ASSIGNMENTS ---
                with subtab_teachers:
                    st.subheader("👨‍🏫 Teacher Assignment Management")
                    st.caption("Assign and manage teachers for class instances")

                    # === SECTION A: ASSIGN/UPDATE TEACHER FORM ===
                    with st.expander("💾 Assign Teacher to Class Date", expanded=True):
                        with st.form("assign_teacher_form"):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                # Class selection
                                class_opts = {
                                    f"{c['class_name']} ({c['day']} {c['time']})": c[
                                        "id"
                                    ]
                                    for c in classes
                                }
                                selected_class = st.selectbox(
                                    "Select Class",
                                    options=list(class_opts.keys()),
                                    key="teacher_assign_class",
                                )
                                assign_class_id = class_opts[selected_class]

                            with col2:
                                # Date selection
                                assign_date = st.date_input(
                                    "Class Date",
                                    value=date.today(),
                                    key="teacher_assign_date",
                                )

                            with col3:
                                # Teacher selection
                                teachers_res = requests.get(
                                    f"{BASE_URL}/roles/users/by-role/Teacher"
                                )
                                teachers_list = (
                                    teachers_res.json()
                                    if teachers_res.status_code == 200
                                    else []
                                )

                                teacher_opts = {"-- No Teacher Assigned --": None}
                                if teachers_list:
                                    teacher_opts.update(
                                        {
                                            f"{t['first_name']} {t['last_name']}": t[
                                                "user_uuid"
                                            ]
                                            for t in teachers_list
                                        }
                                    )

                                selected_teacher = st.selectbox(
                                    "Assign Teacher",
                                    options=list(teacher_opts.keys()),
                                    help="Select teacher for this class date",
                                    key="teacher_assign_select",
                                )
                                selected_teacher_uuid = teacher_opts[selected_teacher]

                            submit_teacher = st.form_submit_button(
                                "💾 Save Teacher Assignment"
                            )

                            if submit_teacher:
                                # Check if ClassInstance exists
                                try:
                                    instance_check = requests.get(
                                        f"{BASE_URL}/class-instances/by-date/",
                                        params={
                                            "class_id": assign_class_id,
                                            "class_date": str(assign_date),
                                        },
                                    )

                                    if instance_check.status_code == 200:
                                        # Update existing instance
                                        instance_id = instance_check.json()["id"]
                                        update_res = requests.put(
                                            f"{BASE_URL}/class-instances/{instance_id}",
                                            json={
                                                "teacher_uuid": selected_teacher_uuid
                                            },
                                        )
                                        action = "updated"
                                    else:
                                        # Create new instance
                                        update_res = requests.post(
                                            f"{BASE_URL}/class-instances/",
                                            json={
                                                "class_id": assign_class_id,
                                                "class_date": str(assign_date),
                                                "teacher_uuid": selected_teacher_uuid,
                                                "lesson_id": None,
                                            },
                                        )
                                        action = "assigned"

                                    if update_res.status_code == 200:
                                        teacher_name = (
                                            selected_teacher
                                            if selected_teacher
                                            != "-- No Teacher Assigned --"
                                            else "removed"
                                        )
                                        st.success(f"✅ Teacher {action} successfully!")
                                        st.rerun()
                                    else:
                                        detail = update_res.json().get(
                                            "detail", "Unknown error"
                                        )
                                        st.error(f"❌ Error: {detail}")

                                except Exception as e:
                                    st.error(f"⚠️ Connection failed: {e}")

                    st.divider()

                    # === SECTION B: VIEW ALL TEACHER ASSIGNMENTS ===
                    st.subheader("📋 Current Teacher Assignments")

                    # Filters
                    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

                    with col_f1:
                        filter_class_opts = {
                            f"{c['class_name']} ({c['day']} {c['time']})": c["id"]
                            for c in classes
                        }
                        filter_class = st.selectbox(
                            "Filter by Class",
                            options=["-- All Classes --"]
                            + list(filter_class_opts.keys()),
                            key="teacher_filter_class",
                        )

                    with col_f2:
                        filter_teacher_opts = ["-- All Teachers --"]
                        if teachers_list:
                            filter_teacher_opts.extend(
                                [
                                    f"{t['first_name']} {t['last_name']}"
                                    for t in teachers_list
                                ]
                            )

                        filter_teacher = st.selectbox(
                            "Filter by Teacher",
                            options=filter_teacher_opts,
                            key="teacher_filter_teacher",
                        )

                    with col_f3:
                        filter_start = st.date_input(
                            "From Date",
                            value=date.today().replace(day=1),
                            key="teacher_filter_start",
                        )

                    with col_f4:
                        filter_end = st.date_input(
                            "To Date", value=date.today(), key="teacher_filter_end"
                        )

                    # Fetch class instances with filters
                    params = {}
                    if filter_class != "-- All Classes --":
                        params["class_id"] = filter_class_opts[filter_class]
                    if filter_teacher != "-- All Teachers --":
                        # Find teacher UUID
                        teacher_name_parts = filter_teacher.split()
                        if len(teacher_name_parts) >= 2:
                            matching_teacher = next(
                                (
                                    t
                                    for t in teachers_list
                                    if t["first_name"] == teacher_name_parts[0]
                                    and t["last_name"]
                                    == " ".join(teacher_name_parts[1:])
                                ),
                                None,
                            )
                            if matching_teacher:
                                params["teacher_uuid"] = matching_teacher["user_uuid"]
                    if filter_start:
                        params["start_date"] = str(filter_start)
                    if filter_end:
                        params["end_date"] = str(filter_end)

                    instances_res = requests.get(
                        f"{BASE_URL}/class-instances/", params=params
                    )

                    if instances_res.status_code == 200:
                        instances = instances_res.json()

                        if instances:
                            # Prepare display data
                            instances_df = pd.DataFrame(instances)
                            display_df = instances_df[
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
                                "Lesson",
                                "ID",
                            ]

                            # Format dates
                            display_df["Date"] = pd.to_datetime(
                                display_df["Date"]
                            ).dt.strftime("%Y-%m-%d")

                            # Handle null values
                            display_df["Teacher"] = display_df["Teacher"].fillna(
                                "Not Assigned"
                            )
                            display_df["Lesson"] = display_df["Lesson"].fillna(
                                "No Lesson"
                            )

                            # Show summary metrics
                            col_m1, col_m2, col_m3 = st.columns(3)
                            with col_m1:
                                st.metric("Total Instances", len(display_df))
                            with col_m2:
                                assigned_count = (
                                    display_df["Teacher"] != "Not Assigned"
                                ).sum()
                                st.metric("Teachers Assigned", assigned_count)
                            with col_m3:
                                unique_teachers = display_df[
                                    display_df["Teacher"] != "Not Assigned"
                                ]["Teacher"].nunique()
                                st.metric("Unique Teachers", unique_teachers)

                            # Display table
                            st.dataframe(
                                display_df.drop(columns=["ID"]),
                                width="stretch",
                                hide_index=True,
                            )

                            # === SECTION C: EDIT/REMOVE ACTIONS ===
                            with st.expander("✏️ Edit Teacher Assignment"):
                                instance_map = {
                                    f"{row['Class']} - {row['Date']}": row["ID"]
                                    for _, row in display_df.iterrows()
                                }

                                selected_instance = st.selectbox(
                                    "Select class instance to edit:",
                                    options=["-- Select --"]
                                    + list(instance_map.keys()),
                                    key="edit_teacher_instance",
                                )

                                if selected_instance != "-- Select --":
                                    instance_id = instance_map[selected_instance]

                                    # Fetch instance details
                                    detail_res = requests.get(
                                        f"{BASE_URL}/class-instances/{instance_id}"
                                    )

                                    if detail_res.status_code == 200:
                                        instance_detail = detail_res.json()

                                        # Show current teacher
                                        current_teacher = instance_detail.get(
                                            "teacher_name", "Not assigned"
                                        )
                                        st.info(
                                            f"**Current Teacher:** {current_teacher}"
                                        )

                                        # Change teacher form
                                        with st.form("edit_teacher_assignment_form"):
                                            st.write("**Update Teacher:**")

                                            new_teacher_opts = {
                                                "-- No Teacher Assigned --": None
                                            }
                                            if teachers_list:
                                                new_teacher_opts.update(
                                                    {
                                                        f"{t['first_name']} {t['last_name']}": t[
                                                            "user_uuid"
                                                        ]
                                                        for t in teachers_list
                                                    }
                                                )

                                            new_teacher = st.selectbox(
                                                "Select New Teacher",
                                                options=list(new_teacher_opts.keys()),
                                                key="new_teacher_select",
                                            )
                                            new_teacher_uuid = new_teacher_opts[
                                                new_teacher
                                            ]

                                            if st.form_submit_button("Update Teacher"):
                                                try:
                                                    update_res = requests.put(
                                                        f"{BASE_URL}/class-instances/{instance_id}",
                                                        json={
                                                            "teacher_uuid": new_teacher_uuid
                                                        },
                                                    )

                                                    if update_res.status_code == 200:
                                                        st.success(
                                                            "✅ Teacher assignment updated!"
                                                        )
                                                        st.rerun()
                                                    else:
                                                        detail = update_res.json().get(
                                                            "detail", "Unknown error"
                                                        )
                                                        st.error(f"❌ Error: {detail}")
                                                except Exception as e:
                                                    st.error(
                                                        f"⚠️ Connection failed: {e}"
                                                    )

                                        # Remove teacher button (outside form)
                                        if st.button(
                                            "🗑️ Remove Teacher Assignment",
                                            type="secondary",
                                            key="remove_teacher_btn",
                                        ):
                                            try:
                                                remove_res = requests.put(
                                                    f"{BASE_URL}/class-instances/{instance_id}",
                                                    json={"teacher_uuid": None},
                                                )

                                                if remove_res.status_code == 200:
                                                    st.success("✅ Teacher removed!")
                                                    st.rerun()
                                                else:
                                                    detail = remove_res.json().get(
                                                        "detail", "Unknown error"
                                                    )
                                                    st.error(f"❌ Error: {detail}")
                                            except Exception as e:
                                                st.error(f"⚠️ Connection failed: {e}")
                        else:
                            st.info("ℹ️ No class instances found with current filters")
                            st.caption(
                                "Class instances are created when students check in or when you assign a teacher/lesson"
                            )
                    else:
                        st.error(
                            f"❌ Failed to fetch class instances: {instances_res.status_code}"
                        )

        except Exception as e:
            st.error(f"⚠️ Connection error: {e}")

    st.success("Welcome, Admin")
    # tab_user, tab_class, etc...
else:
    st.stop()  # Prevents the rest of the page from running
