import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re
from datetime import date, datetime, timedelta
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

    # Add base text color rule to ensure text changes with theme
    text_color_rule = """
    /* Base text color for all content */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div {
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

# Load CSS
load_css()


# Helper function for theme-aware chart colors
def get_chart_theme():
    """Get Plotly chart template based on current theme"""
    theme = st.session_state.get("theme", "dark")
    if theme == "dark":
        return {
            "template": "plotly_dark",
            "colors": ["#c91a2b", "#2196F3", "#4CAF50", "#FFA726", "#9C27B0"],
            "paper_bgcolor": "rgba(25, 27, 31, 0.8)",
            "plot_bgcolor": "rgba(15, 17, 21, 0.5)",
            "font_color": "#FFFFFF",
        }
    else:
        return {
            "template": "plotly_white",
            "colors": ["#c91a2b", "#1976D2", "#388E3C", "#F57C00", "#7B1FA2"],
            "paper_bgcolor": "rgba(255, 255, 255, 0.9)",
            "plot_bgcolor": "rgba(245, 245, 245, 0.5)",
            "font_color": "#212121",
        }


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


# --- LOGOUT FUNCTION ---
def logout():
    """Log out the current admin user"""
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    st.rerun()


# --- PAGE EXECUTION ---
if check_password():
    # --- CONFIGURATION ---
    BASE_URL = "http://127.0.0.1:8000"

    st.set_page_config(page_title="Management Console", layout="wide", page_icon="⚙️")

    # Header with logout button
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("⚙️ Management Console")
    with col2:
        st.write("")
        st.write("")
        if st.button("🚪 Logout", type="secondary"):
            logout()

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
        tab_performance,
        tab_feedback,
    ) = st.tabs(
        [
            "🥋 User Admin",
            "📅 Class Schedule",
            "🏢 Gyms & Types",
            "🗓️ Terms",
            "🎯 Targets",
            "📚 Lessons",
            "🔐 Student Passwords",
            "📈 Performance Analytics",
            "📊 Feedback Analytics",
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

                        # --- PHOTO MANAGEMENT SECTION ---
                        st.divider()
                        st.subheader("📸 Photo Management")
                        st.caption("Update or remove the member's profile photo")

                        # Display current photo
                        col_photo, col_actions = st.columns([1, 2])

                        with col_photo:
                            if member.get("profile_image_url"):
                                st.image(
                                    member["profile_image_url"],
                                    width=150,
                                    caption="Current Photo",
                                )
                            else:
                                st.info("No photo set")
                                st.markdown("👤")

                        with col_actions:
                            # Photo update section
                            st.caption("Upload new photo or take a picture")

                            # Photo input method
                            photo_method = st.radio(
                                "Choose method:",
                                ["Upload File", "Take Photo (Camera)"],
                                key=f"photo_method_{member['user_uuid']}",
                            )

                            new_photo = None

                            if photo_method == "Take Photo (Camera)":
                                # Use button to activate camera
                                if (
                                    f"show_camera_{member['user_uuid']}"
                                    not in st.session_state
                                ):
                                    st.session_state[
                                        f"show_camera_{member['user_uuid']}"
                                    ] = False

                                if not st.session_state[
                                    f"show_camera_{member['user_uuid']}"
                                ]:
                                    if st.button(
                                        "📷 Open Camera",
                                        key=f"open_cam_{member['user_uuid']}",
                                    ):
                                        st.session_state[
                                            f"show_camera_{member['user_uuid']}"
                                        ] = True
                                        st.rerun()
                                else:
                                    new_photo = st.camera_input(
                                        "Take a photo",
                                        key=f"camera_{member['user_uuid']}",
                                    )
                                    if new_photo:
                                        st.image(
                                            new_photo, width=150, caption="Preview"
                                        )
                                    if st.button(
                                        "❌ Cancel",
                                        key=f"cancel_cam_{member['user_uuid']}",
                                    ):
                                        st.session_state[
                                            f"show_camera_{member['user_uuid']}"
                                        ] = False
                                        st.rerun()
                            else:
                                new_photo = st.file_uploader(
                                    "Choose photo",
                                    type=["jpg", "jpeg", "png"],
                                    key=f"file_{member['user_uuid']}",
                                )
                                # Clear camera state if switching to file
                                if (
                                    f"show_camera_{member['user_uuid']}"
                                    in st.session_state
                                ):
                                    del st.session_state[
                                        f"show_camera_{member['user_uuid']}"
                                    ]

                                # Preview
                                if new_photo:
                                    st.image(new_photo, width=150, caption="Preview")

                            # Action buttons - always shown regardless of method
                            col_update, col_delete = st.columns(2)

                            with col_update:
                                update_clicked = st.button(
                                    "📤 Update Photo",
                                    key=f"update_photo_{member['user_uuid']}",
                                    use_container_width=True,
                                )

                            with col_delete:
                                delete_clicked = st.button(
                                    "🗑️ Delete Photo",
                                    key=f"delete_photo_{member['user_uuid']}",
                                    use_container_width=True,
                                    type="secondary",
                                )

                            # Handle update
                            if update_clicked:
                                if new_photo:
                                    try:
                                        files = {
                                            "file": (
                                                new_photo.name,
                                                new_photo.getvalue(),
                                                new_photo.type,
                                            )
                                        }

                                        response = requests.post(
                                            f"{BASE_URL}/users/{member['user_uuid']}/photo",
                                            files=files,
                                        )

                                        if response.status_code == 200:
                                            result = response.json()
                                            st.success("✅ Photo updated successfully!")
                                            st.rerun()
                                        else:
                                            error_detail = response.json().get(
                                                "detail", "Unknown error"
                                            )
                                            st.error(f"❌ Failed: {error_detail}")
                                    except Exception as e:
                                        st.error(f"⚠️ Upload error: {e}")
                                else:
                                    st.warning("Please select or capture a photo first")

                            # Handle delete
                            if delete_clicked:
                                if not member.get("profile_image_url"):
                                    st.warning("No photo to delete")
                                else:
                                    try:
                                        response = requests.delete(
                                            f"{BASE_URL}/users/{member['user_uuid']}/photo"
                                        )

                                        if response.status_code == 200:
                                            st.success("✅ Photo deleted successfully!")
                                            st.rerun()
                                        else:
                                            error_detail = response.json().get(
                                                "detail", "Unknown error"
                                            )
                                            st.error(f"❌ Failed: {error_detail}")
                                    except Exception as e:
                                        st.error(f"⚠️ Delete error: {e}")

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

            st.divider()
            st.subheader("🎯 Manual User Target Adjustments")
            st.caption(
                "Add bonus/penalty points or custom target adjustments for individual users"
            )

            # Fetch users and terms for the adjustment form
            users_res = requests.get(f"{BASE_URL}/users/")
            if users_res.status_code == 200:
                users_list = users_res.json()
                user_map = {
                    f"{u['first_name']} {u['last_name']} ({u['email']})": u["user_uuid"]
                    for u in users_list
                    if u.get("is_current", True)
                }

                # Create subtabs for Add and View
                adj_tab_add, adj_tab_view = st.tabs(
                    ["➕ Add Adjustment", "📋 View Adjustments"]
                )

                with adj_tab_add:
                    with st.form("user_target_adjustment_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            adj_user = st.selectbox(
                                "Select User", list(user_map.keys()), key="adj_user"
                            )
                            adj_term = st.selectbox(
                                "Term", list(term_map.keys()), key="adj_term"
                            )
                        with col2:
                            adj_amount = st.number_input(
                                "Adjustment Amount",
                                min_value=-1000.0,
                                max_value=1000.0,
                                value=0.0,
                                step=0.5,
                                help="Positive for bonus points, negative for penalties",
                            )
                            adj_reason = st.text_input(
                                "Reason (optional)",
                                placeholder="e.g., Competition winner, Attendance bonus",
                            )

                        submitted = st.form_submit_button(
                            "💾 Save Adjustment", type="primary"
                        )
                        if submitted:
                            try:
                                response = requests.post(
                                    f"{BASE_URL}/user-target-adjustments/",
                                    json={
                                        "user_uuid": user_map[adj_user],
                                        "term_id": term_map[adj_term],
                                        "adjustment": adj_amount,
                                        "reason": adj_reason if adj_reason else None,
                                    },
                                )
                                if response.status_code == 200:
                                    st.success(f"✅ Adjustment saved successfully!")
                                    st.rerun()
                                else:
                                    error_detail = response.json().get(
                                        "detail", "Unknown error"
                                    )
                                    st.error(
                                        f"❌ Failed to save adjustment: {error_detail}"
                                    )
                            except Exception as e:
                                st.error(f"⚠️ Error: {str(e)}")

                with adj_tab_view:
                    # Fetch all adjustments
                    try:
                        adj_res = requests.get(f"{BASE_URL}/user-target-adjustments/")
                        if adj_res.status_code == 200:
                            adjustments = adj_res.json()
                            if adjustments:
                                # Create a readable dataframe
                                adj_data = []
                                for adj in adjustments:
                                    user_info = next(
                                        (
                                            u
                                            for u in users_list
                                            if u["user_uuid"] == adj["user_uuid"]
                                        ),
                                        {},
                                    )
                                    term_info = next(
                                        (
                                            t
                                            for t in terms_res.json()
                                            if t["id"] == adj["term_id"]
                                        ),
                                        {},
                                    )
                                    adj_data.append(
                                        {
                                            "ID": adj["id"],
                                            "User": f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}",
                                            "Term": term_info.get(
                                                "term_name", "Unknown"
                                            ),
                                            "Adjustment": adj["adjustment"],
                                            "Reason": adj.get("reason", "-"),
                                            "Created": adj["created_at"][:10]
                                            if adj.get("created_at")
                                            else "-",
                                        }
                                    )

                                df_adj = pd.DataFrame(adj_data)
                                st.dataframe(df_adj, width="stretch", hide_index=True)

                                # Summary metrics
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    total_adj = len(adjustments)
                                    st.metric("Total Adjustments", total_adj)
                                with col2:
                                    positive_adj = sum(
                                        1 for a in adjustments if a["adjustment"] > 0
                                    )
                                    st.metric("Bonus Adjustments", positive_adj)
                                with col3:
                                    negative_adj = sum(
                                        1 for a in adjustments if a["adjustment"] < 0
                                    )
                                    st.metric("Penalty Adjustments", negative_adj)
                            else:
                                st.info("No manual adjustments have been created yet.")
                    except Exception as e:
                        st.error(f"Error loading adjustments: {str(e)}")
            else:
                st.error("Could not load users for adjustment form")
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

    # --- 8. PERFORMANCE ANALYTICS ---
    with tab_performance:
        st.header("📈 Performance Analytics")
        st.markdown("View student and teacher performance metrics")

        # Fetch data
        try:
            users = requests.get(f"{BASE_URL}/users/").json()
            terms = requests.get(f"{BASE_URL}/terms/").json()
            targets = requests.get(f"{BASE_URL}/term-targets/").json()
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            users, terms, targets = [], [], []

        if not users:
            st.warning("No users found. Please add members first.")
        else:
            # Sidebar filters for analytics
            st.subheader("🔍 Filter Analytics")

            # Map full names to user objects
            user_map = {f"{u['first_name']} {u['last_name']}": u for u in users}
            selected_student_name = st.selectbox(
                "Select Student", options=list(user_map.keys())
            )

            term_map = {t["term_name"]: t for t in terms}
            term_options = ["All Time"] + list(term_map.keys())
            selected_term_name = st.selectbox("Filter by Term", options=term_options)

            # Get selected user details
            user = user_map[selected_student_name]
            user_uuid = user["user_uuid"]

            # Check user's roles
            try:
                user_roles_res = requests.get(f"{BASE_URL}/roles/user/{user_uuid}")
                user_roles = (
                    user_roles_res.json() if user_roles_res.status_code == 200 else []
                )
                user_role_names = [r["role_name"] for r in user_roles]
            except:
                user_role_names = []

            # Determine analytics view
            is_teacher = "Teacher" in user_role_names

            # Add analytics type selector
            if is_teacher:
                analytics_type = st.radio(
                    "View Analytics As:",
                    ["Student", "Teacher"],
                    help="Select which analytics view to display",
                )
            else:
                analytics_type = "Student"

            # Date range logic
            if selected_term_name != "All Time":
                term = term_map[selected_term_name]
                start_dt = term["start_date"]
                end_dt = term["end_date"]
            else:
                # Default to last 365 days for "All Time"
                start_dt = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                end_dt = datetime.now().strftime("%Y-%m-%d")

            st.divider()

            # Fetch attendance data
            attendance_data = []
            try:
                att_res = requests.get(
                    f"{BASE_URL}/attendance/user/{user_uuid}?start={start_dt}&end={end_dt}"
                )
                if att_res.status_code == 200:
                    raw_data = att_res.json()
                    if isinstance(raw_data, list):
                        attendance_data = raw_data
            except Exception as e:
                st.error(f"Connection Error: {e}")

            # --- STUDENT ANALYTICS ---
            if analytics_type == "Student":
                st.header(
                    f"Student Performance: {selected_student_name} ({user['rank']})"
                )
                kpi1, kpi2, chart_col = st.columns([1, 1, 2])

                # Initialize totals
                total_points = 0.0
                total_classes = 0

                if attendance_data:
                    df_att = pd.DataFrame(attendance_data)
                    points_col = "points"

                    # Convert to numeric to ensure we can sum safely
                    if points_col in df_att.columns:
                        df_att[points_col] = pd.to_numeric(
                            df_att[points_col], errors="coerce"
                        ).fillna(0)
                        total_points = float(df_att[points_col].sum())

                    total_classes = len(attendance_data)

                with kpi1:
                    st.metric("Total Mat Points", f"{total_points:.1f}")
                with kpi2:
                    st.metric("Total Sessions", total_classes)

                with chart_col:
                    # Target lookup
                    target_val = 50.0  # Fallback
                    if selected_term_name != "All Time":
                        relevant_target = next(
                            (
                                t
                                for t in targets
                                if t["term_id"] == term["id"]
                                and t["rank"] == user["rank"]
                            ),
                            None,
                        )
                        if relevant_target:
                            target_val = float(relevant_target["target"])

                    # GAUGE: Comparing Sum of Weightings to Term Target
                    fig_gauge = go.Figure(
                        go.Indicator(
                            mode="gauge+number+delta",
                            value=total_points,
                            title={
                                "text": f"Mat Point Goal: {target_val}",
                                "font": {"size": 18},
                            },
                            delta={
                                "reference": target_val,
                                "increasing": {"color": "#00cc96"},
                            },
                            gauge={
                                "axis": {
                                    "range": [
                                        None,
                                        max(target_val * 1.2, total_points + 5),
                                    ]
                                },
                                "bar": {"color": "#1f77b4"},
                                "steps": [
                                    {"range": [0, target_val], "color": "#e5ecf6"},
                                    {
                                        "range": [target_val, target_val * 1.2],
                                        "color": "#d1f2eb",
                                    },
                                ],
                                "threshold": {
                                    "line": {"color": "red", "width": 4},
                                    "thickness": 0.75,
                                    "value": target_val,
                                },
                            },
                        )
                    )
                    fig_gauge.update_layout(
                        height=300, margin=dict(l=30, r=30, t=50, b=20)
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # --- VISUALIZATIONS ---
                st.divider()
                col_left, col_right = st.columns(2)

                if attendance_data:
                    df_att = pd.DataFrame(attendance_data)

                    # Dynamic Column Identification
                    time_col = next(
                        (
                            c
                            for c in ["check_in_time", "timestamp", "created_at"]
                            if c in df_att.columns
                        ),
                        None,
                    )
                    name_col = next(
                        (
                            c
                            for c in ["class_name", "name", "label"]
                            if c in df_att.columns
                        ),
                        None,
                    )
                    points_col = "points"

                    # Validation: Ensure we have at least the basics
                    if "points" not in df_att.columns:
                        df_att["points"] = 1.0

                    if time_col:
                        df_att["date"] = pd.to_datetime(df_att[time_col]).dt.date

                        with col_left:
                            st.subheader("Attendance History")
                            # Group by date and sum points
                            daily_points = (
                                df_att.groupby("date")[points_col].sum().reset_index()
                            )
                            daily_points["cumulative"] = daily_points[
                                points_col
                            ].cumsum()

                            fig_line = px.area(
                                daily_points,
                                x="date",
                                y="cumulative",
                                title="Cumulative Points Accumulation",
                                color_discrete_sequence=["#1f77b4"],
                            )
                            st.plotly_chart(fig_line, use_container_width=True)

                    with col_right:
                        st.subheader("Class Distribution")
                        if name_col:
                            fig_pie = px.pie(
                                df_att,
                                names=name_col,
                                values=points_col,
                                hole=0.4,
                                title="Points by Class Type",
                            )
                            st.plotly_chart(fig_pie, use_container_width=True)
                        else:
                            st.info("No class names found to categorize distribution.")

                    # --- DETAILED LOG ---
                    st.divider()
                    st.subheader("📋 Detailed Attendance Log")

                    display_cols = [
                        c
                        for c in [time_col, name_col, "day", points_col]
                        if c in df_att.columns
                    ]
                    df_display = df_att[display_cols].copy()

                    if time_col in df_display.columns:
                        df_display[time_col] = pd.to_datetime(
                            df_display[time_col]
                        ).dt.strftime("%b %d, %Y - %H:%M")

                    st.dataframe(df_display, width="stretch", hide_index=True)

                else:
                    st.info("No attendance data to display for the selected criteria.")

            # --- TEACHER ANALYTICS ---
            elif analytics_type == "Teacher":
                st.header(f"Teacher Performance: {selected_student_name}")

                # Fetch teacher class summary
                try:
                    teacher_res = requests.get(
                        f"{BASE_URL}/attendance/teacher/{user_uuid}/classes",
                        params={"start_date": start_dt, "end_date": end_dt},
                    )

                    if teacher_res.status_code == 200:
                        teacher_data = teacher_res.json()

                        if teacher_data:
                            df_teacher = pd.DataFrame(teacher_data)

                            # KPIs
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Classes Taught", len(df_teacher))
                            with col2:
                                st.metric(
                                    "Total Students",
                                    int(df_teacher["student_count"].sum()),
                                )
                            with col3:
                                st.metric(
                                    "Avg Students/Class",
                                    f"{df_teacher['student_count'].mean():.1f}",
                                )

                            st.divider()

                            # Class breakdown
                            col_left, col_right = st.columns(2)

                            with col_left:
                                st.subheader("Classes Taught by Type")
                                class_summary = (
                                    df_teacher.groupby("class_name")
                                    .agg(
                                        {"class_date": "count", "student_count": "sum"}
                                    )
                                    .reset_index()
                                )
                                class_summary.columns = [
                                    "Class Type",
                                    "Sessions",
                                    "Total Students",
                                ]

                                theme = get_chart_theme()
                                fig = px.bar(
                                    class_summary,
                                    x="Class Type",
                                    y="Sessions",
                                    title="Classes Taught by Type",
                                    color="Total Students",
                                    color_continuous_scale="Blues",
                                    template=theme["template"],
                                )
                                fig.update_layout(
                                    paper_bgcolor=theme["paper_bgcolor"],
                                    plot_bgcolor=theme["plot_bgcolor"],
                                    font_color=theme["font_color"],
                                )
                                st.plotly_chart(fig, use_container_width=True)

                            with col_right:
                                st.subheader("Student Attendance Trend")
                                df_teacher["class_date"] = pd.to_datetime(
                                    df_teacher["class_date"]
                                )
                                daily_students = (
                                    df_teacher.groupby("class_date")["student_count"]
                                    .sum()
                                    .reset_index()
                                )

                                theme = get_chart_theme()
                                fig_line = px.line(
                                    daily_students,
                                    x="class_date",
                                    y="student_count",
                                    title="Students per Day",
                                    template=theme["template"],
                                )
                                fig_line.update_layout(
                                    paper_bgcolor=theme["paper_bgcolor"],
                                    plot_bgcolor=theme["plot_bgcolor"],
                                    font_color=theme["font_color"],
                                )
                                st.plotly_chart(fig_line, use_container_width=True)

                            # Detailed log
                            st.divider()
                            st.subheader("📋 Teaching Log")
                            df_teacher["class_date"] = pd.to_datetime(
                                df_teacher["class_date"]
                            ).dt.strftime("%Y-%m-%d")
                            display_df = df_teacher[
                                ["class_date", "class_name", "student_count"]
                            ]
                            display_df.columns = ["Date", "Class", "Students"]
                            st.dataframe(display_df, hide_index=True, width="stretch")
                        else:
                            st.info("No teaching records found for this period")
                    else:
                        st.error("Failed to fetch teacher analytics")
                except Exception as e:
                    st.error(f"Error fetching teacher analytics: {e}")

    # --- 9. FEEDBACK ANALYTICS ---
    with tab_feedback:
        st.header("📊 Comprehensive Feedback Analytics")
        st.markdown(
            "Admin view of all student feedback across all classes and teachers"
        )

        # Fetch all feedback
        try:
            feedback_res = requests.get(
                f"{BASE_URL}/feedback/admin/comprehensive-stats"
            )

            if feedback_res.status_code == 200:
                all_feedback = feedback_res.json()

                if not all_feedback:
                    st.info("📭 No feedback has been submitted yet")
                else:
                    # Convert to DataFrame
                    df_feedback = pd.DataFrame(all_feedback)

                    # --- METRICS ROW ---
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

                    with col_m1:
                        st.metric("Total Feedback", len(df_feedback))

                    with col_m2:
                        positive_count = len(
                            df_feedback[df_feedback["rating"] == "thumbs_up"]
                        )
                        total = len(df_feedback)
                        positive_pct = (
                            (positive_count / total * 100) if total > 0 else 0
                        )
                        st.metric("👍 Positive", f"{positive_pct:.1f}%")

                    with col_m3:
                        # Most active student by feedback count
                        student_counts = df_feedback["student_name"].value_counts()
                        most_active = (
                            student_counts.index[0]
                            if len(student_counts) > 0
                            else "N/A"
                        )
                        st.metric("Most Active", most_active)

                    with col_m4:
                        # Average rating (1 = positive, 0 = negative)
                        ratings = df_feedback["rating"].apply(
                            lambda x: 1 if x == "thumbs_up" else 0
                        )
                        avg_rating = ratings.mean() * 100 if len(ratings) > 0 else 0
                        st.metric("Avg Rating", f"{avg_rating:.1f}%")

                    st.divider()

                    # --- FILTERS ---
                    with st.expander("🔍 Filters", expanded=False):
                        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(
                            4
                        )

                        with filter_col1:
                            # Date range
                            df_feedback["class_date"] = pd.to_datetime(
                                df_feedback["class_date"]
                            )
                            min_date = df_feedback["class_date"].min().date()
                            max_date = df_feedback["class_date"].max().date()

                            date_filter = st.date_input(
                                "Date Range",
                                value=(min_date, max_date),
                                min_value=min_date,
                                max_value=max_date,
                                key="feedback_date_filter",
                            )

                        with filter_col2:
                            # Class filter
                            all_classes = sorted(df_feedback["class_name"].unique())
                            class_filter = st.multiselect(
                                "Classes",
                                options=all_classes,
                                default=all_classes,
                                key="feedback_class_filter",
                            )

                        with filter_col3:
                            # Teacher filter
                            all_teachers = sorted(
                                df_feedback["teacher_name"].dropna().unique()
                            )
                            teacher_filter = st.multiselect(
                                "Teachers",
                                options=["(Unassigned)"] + list(all_teachers),
                                default=["(Unassigned)"] + list(all_teachers),
                                key="feedback_teacher_filter",
                            )

                        with filter_col4:
                            # Rating filter
                            rating_filter = st.selectbox(
                                "Rating",
                                options=["All", "👍 Positive", "👎 Negative"],
                                key="feedback_rating_filter",
                            )

                    # Apply filters
                    df_filtered = df_feedback.copy()

                    if date_filter and len(date_filter) == 2:
                        df_filtered = df_filtered[
                            (df_filtered["class_date"].dt.date >= date_filter[0])
                            & (df_filtered["class_date"].dt.date <= date_filter[1])
                        ]

                    if class_filter:
                        df_filtered = df_filtered[
                            df_filtered["class_name"].isin(class_filter)
                        ]

                    if teacher_filter:
                        if "(Unassigned)" in teacher_filter:
                            df_filtered = df_filtered[
                                (df_filtered["teacher_name"].isin(teacher_filter))
                                | (df_filtered["teacher_name"].isna())
                            ]
                        else:
                            df_filtered = df_filtered[
                                df_filtered["teacher_name"].isin(teacher_filter)
                            ]

                    if rating_filter == "👍 Positive":
                        df_filtered = df_filtered[df_filtered["rating"] == "thumbs_up"]
                    elif rating_filter == "👎 Negative":
                        df_filtered = df_filtered[
                            df_filtered["rating"] == "thumbs_down"
                        ]

                    # --- DATA TABLE ---
                    st.subheader("📋 Feedback Details")

                    # Format display
                    df_display = df_filtered.copy()
                    df_display["Date"] = df_display["class_date"].dt.strftime(
                        "%Y-%m-%d"
                    )
                    df_display["Class"] = df_display["class_name"]
                    df_display["Student"] = df_display["student_name"]
                    df_display["Teacher"] = df_display["teacher_name"].fillna(
                        "Unassigned"
                    )
                    df_display["Rating"] = df_display["rating"].apply(
                        lambda x: "👍 Positive"
                        if x == "thumbs_up"
                        else "👎 Negative"
                        if x == "thumbs_down"
                        else "N/A"
                    )
                    df_display["Comment"] = df_display["comment"].fillna("No comment")

                    df_display = df_display[
                        ["Date", "Class", "Student", "Teacher", "Rating", "Comment"]
                    ]

                    st.dataframe(df_display, use_container_width=True, hide_index=True)

                    st.divider()

                    # --- VISUALIZATIONS ---
                    st.subheader("📈 Charts")

                    import plotly.express as px

                    # Get theme
                    theme = st.session_state.get("theme", "dark")
                    if theme == "dark":
                        template = "plotly_dark"
                        colors = [
                            "#4CAF50",
                            "#F44336",
                        ]  # Green for positive, red for negative
                    else:
                        template = "plotly_white"
                        colors = ["#388E3C", "#D32F2F"]

                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        # Feedback over time
                        st.markdown("**Feedback Over Time**")

                        feedback_by_date = (
                            df_filtered.groupby(
                                [df_filtered["class_date"].dt.date, "rating"]
                            )
                            .size()
                            .reset_index(name="count")
                        )
                        feedback_by_date["rating_label"] = feedback_by_date[
                            "rating"
                        ].apply(
                            lambda x: "Positive" if x == "thumbs_up" else "Negative"
                        )

                        fig1 = px.line(
                            feedback_by_date,
                            x="class_date",
                            y="count",
                            color="rating_label",
                            title="",
                            labels={
                                "class_date": "Date",
                                "count": "Count",
                                "rating_label": "Rating",
                            },
                            template=template,
                            color_discrete_sequence=colors,
                        )
                        st.plotly_chart(fig1, use_container_width=True)

                    with chart_col2:
                        # Feedback by class
                        st.markdown("**Feedback by Class**")

                        feedback_by_class = (
                            df_filtered["class_name"].value_counts().reset_index()
                        )
                        feedback_by_class.columns = ["class_name", "count"]

                        fig2 = px.bar(
                            feedback_by_class,
                            x="class_name",
                            y="count",
                            title="",
                            labels={"class_name": "Class", "count": "Feedback Count"},
                            template=template,
                            color_discrete_sequence=["#c91a2b"],  # CKB Red
                        )
                        fig2.update_xaxes(tickangle=45)
                        st.plotly_chart(fig2, use_container_width=True)

                    # Second row of charts
                    chart_col3, chart_col4 = st.columns(2)

                    with chart_col3:
                        # Feedback by teacher
                        st.markdown("**Feedback by Teacher**")

                        feedback_by_teacher = (
                            df_filtered["teacher_name"]
                            .fillna("Unassigned")
                            .value_counts()
                            .reset_index()
                        )
                        feedback_by_teacher.columns = ["teacher_name", "count"]

                        fig3 = px.bar(
                            feedback_by_teacher,
                            x="teacher_name",
                            y="count",
                            title="",
                            labels={
                                "teacher_name": "Teacher",
                                "count": "Feedback Count",
                            },
                            template=template,
                            color_discrete_sequence=["#2196F3"],  # Blue
                        )
                        fig3.update_xaxes(tickangle=45)
                        st.plotly_chart(fig3, use_container_width=True)

                    with chart_col4:
                        # Rating distribution
                        st.markdown("**Rating Distribution**")

                        rating_dist = df_filtered["rating"].value_counts().reset_index()
                        rating_dist.columns = ["rating", "count"]
                        rating_dist["rating_label"] = rating_dist["rating"].apply(
                            lambda x: "👍 Positive"
                            if x == "thumbs_up"
                            else "👎 Negative"
                        )

                        fig4 = px.pie(
                            rating_dist,
                            values="count",
                            names="rating_label",
                            title="",
                            template=template,
                            color_discrete_sequence=colors,
                        )
                        st.plotly_chart(fig4, use_container_width=True)

                    st.divider()

                    # --- CSV EXPORT ---
                    st.subheader("📥 Export Data")

                    # Prepare CSV
                    csv_data = df_display.to_csv(index=False)

                    st.download_button(
                        label="📥 Download Feedback CSV",
                        data=csv_data,
                        file_name=f"feedback_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            else:
                st.error(
                    f"Failed to fetch feedback: {feedback_res.json().get('detail', 'Unknown error')}"
                )

        except Exception as e:
            st.error(f"Error loading feedback analytics: {str(e)}")

else:
    st.stop()  # Prevents the rest of the page from running
