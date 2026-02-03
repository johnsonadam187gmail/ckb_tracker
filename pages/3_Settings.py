import streamlit as st
import requests
import pandas as pd
import re
from datetime import date
from pathlib import Path


# Password validation function
def validate_password(password):
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return (
            False,
            'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)',
        )

    return True, ""


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
    (
        tab_user,
        tab_class,
        tab_gym_types,
        tab_terms,
        tab_targets,
        tab_lessons,
        tab_passwords,
    ) = st.tabs(
        [
            "🥋 User Admin",
            "📅 Class Schedule",
            "🏢 Gyms & Types",
            "🗓️ Terms",
            "🎯 Targets",
            "📚 Lessons",
            "🔐 Student Passwords",
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

                        # --- PASSWORD RESET SECTION ---
                        st.divider()
                        st.subheader("🔐 Reset Password (Account Recovery)")
                        st.caption(
                            "Reset this member's password to recover their account access. "
                            "Password must meet security requirements."
                        )

                        with st.form(f"reset_password_form_{member['user_uuid']}"):
                            st.caption(
                                "Password must be at least 8 characters and include: "
                                "uppercase, lowercase, number, and special character"
                            )

                            reset_password = st.text_input(
                                "New Password *",
                                type="password",
                                help="Required: Min 8 chars with uppercase, lowercase, number, and special character",
                                key=f"reset_pwd_{member['user_uuid']}",
                            )
                            reset_confirm = st.text_input(
                                "Confirm New Password *",
                                type="password",
                                key=f"reset_confirm_{member['user_uuid']}",
                            )

                            submit_reset = st.form_submit_button("🔄 Reset Password")

                            if submit_reset:
                                if not reset_password:
                                    st.error("❌ Password cannot be empty")
                                elif reset_password != reset_confirm:
                                    st.error("❌ Passwords do not match")
                                else:
                                    # Validate password strength
                                    is_valid, error_msg = validate_password(
                                        reset_password
                                    )
                                    if not is_valid:
                                        st.error(f"❌ {error_msg}")
                                    else:
                                        # Call API to reset password
                                        try:
                                            password_data = {
                                                "user_uuid": member["user_uuid"],
                                                "password": reset_password,
                                            }
                                            response = requests.post(
                                                f"{BASE_URL}/auth/set-password",
                                                json=password_data,
                                            )
                                            if response.status_code == 200:
                                                st.success(
                                                    f"✅ Password reset successfully for {member['first_name']} {member['last_name']}! "
                                                    "They can now log in with the new password."
                                                )
                                                st.rerun()
                                            else:
                                                error_detail = (
                                                    response.json().get(
                                                        "detail", "Unknown error"
                                                    )
                                                    if response.status_code != 500
                                                    else response.text
                                                )
                                                st.error(f"❌ Failed: {error_detail}")
                                                st.caption(
                                                    f"Status code: {response.status_code}"
                                                )
                                        except Exception as e:
                                            st.error(f"⚠️ Connection error: {e}")
                                            st.caption(
                                                f"API URL: {BASE_URL}/auth/set-password"
                                            )

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
                                    "points": c_wght,
                                    "gym_id": gym_opts[c_gym],
                                    "class_type_id": type_opts[c_typ],
                                },
                            )

            if classes:
                st.subheader("Current Active Schedule")
                st.dataframe(
                    pd.DataFrame(classes)[["class_name", "day", "time", "points"]],
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
                                                st.error(f"⚠️ Connection failed: {e}")
        except Exception as e:
            st.error(f"⚠️ Connection error: {e}")

    # --- 7. STUDENT PASSWORDS TAB ---
    with tab_passwords:
        st.header("🔐 Student Password Management")
        st.markdown(
            "Set or remove passwords for students to access the **Student Portal**. Students use their email and password to log in and view analytics + submit feedback."
        )

        # Fetch all users
        try:
            users_res = requests.get(f"{BASE_URL}/users/")
            if users_res.status_code == 200:
                all_users = users_res.json()
            else:
                all_users = []
                st.error("Failed to fetch users")
        except Exception as e:
            st.error(f"Connection error: {e}")
            all_users = []

        if not all_users:
            st.warning("No users found")
        else:
            # --- SET PASSWORD FORM ---
            st.subheader("🔑 Set/Update Password")

            with st.form("set_password_form"):
                # User selection
                user_options = {
                    f"{u['first_name']} {u['last_name']} ({u['email']})": u
                    for u in all_users
                }
                selected_user_label = st.selectbox(
                    "Select Student", options=list(user_options.keys())
                )
                selected_user = user_options[selected_user_label]

                # Password input
                st.caption(
                    "Password must be at least 8 characters and include: "
                    "uppercase, lowercase, number, and special character"
                )
                new_password = st.text_input(
                    "New Password *",
                    type="password",
                    help="Required: Min 8 chars with uppercase, lowercase, number, and special character",
                )
                confirm_password = st.text_input("Confirm Password *", type="password")

                submit_password = st.form_submit_button("💾 Set Password")

                if submit_password:
                    if not new_password:
                        st.error("❌ Password cannot be empty")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match")
                    else:
                        # Validate password strength
                        is_valid, error_msg = validate_password(new_password)
                        if not is_valid:
                            st.error(f"❌ {error_msg}")
                        else:
                            # Call API
                            try:
                                password_data = {
                                    "user_uuid": selected_user["user_uuid"],
                                    "password": new_password,
                                }
                                response = requests.post(
                                    f"{BASE_URL}/auth/set-password", json=password_data
                                )
                                if response.status_code == 200:
                                    st.success(
                                        f"✅ Password set for {selected_user['first_name']} {selected_user['last_name']}"
                                    )
                                else:
                                    st.error(f"❌ Failed: {response.text}")
                            except Exception as e:
                                st.error(f"⚠️ Connection error: {e}")

            st.divider()

            # --- PASSWORD STATUS TABLE ---
            st.subheader("📋 Password Status")

            # Check password status for all users
            password_statuses = []
            for user in all_users:
                try:
                    status_res = requests.get(
                        f"{BASE_URL}/auth/check-password/{user['user_uuid']}"
                    )
                    if status_res.status_code == 200:
                        status_data = status_res.json()
                        password_statuses.append(
                            {
                                "name": f"{user['first_name']} {user['last_name']}",
                                "email": user["email"],
                                "user_uuid": user["user_uuid"],
                                "has_password": status_data["has_password"],
                            }
                        )
                except:
                    password_statuses.append(
                        {
                            "name": f"{user['first_name']} {user['last_name']}",
                            "email": user["email"],
                            "user_uuid": user["user_uuid"],
                            "has_password": False,
                        }
                    )

            if password_statuses:
                df_passwords = pd.DataFrame(password_statuses)

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_users = len(df_passwords)
                    st.metric("Total Students", total_users)
                with col2:
                    with_passwords = df_passwords["has_password"].sum()
                    st.metric("With Passwords", with_passwords)
                with col3:
                    without_passwords = total_users - with_passwords
                    st.metric("Without Passwords", without_passwords)

                st.markdown("---")

                # Display table with remove buttons
                for idx, row in df_passwords.iterrows():
                    col1, col2, col3, col4 = st.columns([3, 3, 2, 2])

                    with col1:
                        st.write(f"**{row['name']}**")

                    with col2:
                        st.write(row["email"])

                    with col3:
                        if row["has_password"]:
                            st.success("✅ Active")
                        else:
                            st.warning("❌ No Password")

                    with col4:
                        if row["has_password"]:
                            if st.button(
                                "🗑️ Remove", key=f"remove_pwd_{row['user_uuid']}"
                            ):
                                # Remove password
                                try:
                                    remove_res = requests.delete(
                                        f"{BASE_URL}/auth/remove-password/{row['user_uuid']}"
                                    )
                                    if remove_res.status_code == 200:
                                        st.success(f"✅ Password removed")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed: {remove_res.text}")
                                except Exception as e:
                                    st.error(f"⚠️ Error: {e}")

            st.divider()

            # --- INSTRUCTIONS ---
            st.subheader("ℹ️ How It Works")
            st.markdown(
                """
                1. **Set Password**: Select a student and create a strong password (min 8 chars with uppercase, lowercase, number, and special character)
                2. **Student Access**: Students visit the **Student Portal** page and log in with their email + password
                3. **Features**: Students can view their personal analytics and submit feedback on recent classes
                4. **Remove Password**: Click the "Remove" button to disable a student's access
                5. **Security**: Passwords are hashed using bcrypt for security
                
                **Password Requirements:**
                - Minimum 8 characters
                - At least one uppercase letter (A-Z)
                - At least one lowercase letter (a-z)
                - At least one number (0-9)
                - At least one special character (!@#$%^&*(),.?\":{}|<>)
                """
            )

else:
    st.stop()  # Prevents the rest of the page from running
