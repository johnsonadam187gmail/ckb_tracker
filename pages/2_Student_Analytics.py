"""
Student Analytics Page - Personal dashboard for students to view their progress and submit feedback.

Students log in with email/password to access their personal analytics and submit class feedback.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from pathlib import Path

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Student Portal", layout="wide", page_icon="👤")


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


# --- SESSION STATE INITIALIZATION ---
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None


# --- AUTHENTICATION ---
def login(email: str, password: str):
    """Authenticate user via API"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login", json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None


def logout():
    """Log out the current user"""
    st.session_state.logged_in_user = None
    st.rerun()


# --- LOGIN FORM ---
if not st.session_state.logged_in_user:
    st.title("👤 Student Portal")
    st.markdown("### 🔐 Login to view your analytics and submit feedback")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="student@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if not email or not password:
                st.error("Please enter both email and password")
            else:
                user = login(email, password)
                if user:
                    st.session_state.logged_in_user = user
                    st.success(f"Welcome, {user['first_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")

    st.info(
        "💡 **Need access?** Ask your instructor to set up a password for your account."
    )
    st.stop()


# --- LOGGED IN VIEW ---
user = st.session_state.logged_in_user
st.title(f"👤 Welcome, {user['first_name']} {user['last_name']}!")

# Logout button in sidebar
with st.sidebar:
    if st.button("🚪 Logout"):
        logout()

    st.divider()
    st.markdown("### 📋 Quick Info")
    st.markdown(f"**Email:** {user['email']}")
    st.markdown(f"**Rank:** {user.get('rank', 'Not set')}")
    if user.get("nicknames"):
        st.markdown(f"**Nickname:** {user['nicknames']}")


# --- TAB NAVIGATION ---
tab1, tab2 = st.tabs(["📊 My Analytics", "💬 Submit Feedback"])


# ===== TAB 1: MY ANALYTICS =====
with tab1:
    st.header("📊 My Training Progress")

    # Fetch attendance data
    try:
        attendance_response = requests.get(
            f"{BASE_URL}/attendance/user/{user['user_uuid']}"
        )
        if attendance_response.status_code == 200:
            attendance_records = attendance_response.json()
        else:
            attendance_records = []
    except Exception as e:
        st.error(f"Failed to fetch attendance: {e}")
        attendance_records = []

    if not attendance_records:
        st.info(
            "No attendance records found. Start attending classes to see your progress!"
        )
    else:
        df = pd.DataFrame(attendance_records)
        df["attendance_date"] = pd.to_datetime(df["attendance_date"])

        # --- METRICS ROW ---
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_classes = len(df)
            st.metric("Total Classes", total_classes)

        with col2:
            total_points = df["points"].sum()
            st.metric("Total Points", f"{total_points:.1f}")

        with col3:
            # Classes this month
            now = datetime.now()
            month_start = datetime(now.year, now.month, 1)
            classes_this_month = len(df[df["attendance_date"] >= month_start])
            st.metric("Classes This Month", classes_this_month)

        with col4:
            # Last class date
            last_class = df["attendance_date"].max()
            days_since = (datetime.now() - last_class).days
            st.metric("Last Class", f"{days_since} days ago")

        st.divider()

        # --- ATTENDANCE CHART ---
        st.subheader("📈 Attendance Trend (Last 90 Days)")

        # Filter last 90 days
        ninety_days_ago = datetime.now() - timedelta(days=90)
        df_recent = df[df["attendance_date"] >= ninety_days_ago].copy()

        if not df_recent.empty:
            # Group by date and count
            daily_counts = (
                df_recent.groupby(df_recent["attendance_date"].dt.date)
                .size()
                .reset_index(name="Classes")
            )
            daily_counts.columns = ["Date", "Classes"]

            # Create chart
            theme = get_chart_theme()
            fig = px.bar(
                daily_counts,
                x="Date",
                y="Classes",
                title="Classes Attended per Day",
                template=theme["template"],
                color_discrete_sequence=[theme["colors"][0]],
            )
            fig.update_layout(
                paper_bgcolor=theme["paper_bgcolor"],
                plot_bgcolor=theme["plot_bgcolor"],
                font_color=theme["font_color"],
                xaxis_title="Date",
                yaxis_title="Number of Classes",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No attendance in the last 90 days.")

        st.divider()

        # --- ATTENDANCE HISTORY TABLE ---
        st.subheader("📜 Recent Attendance History")

        # Prepare table
        table_df = df.copy()
        table_df = table_df.sort_values("attendance_date", ascending=False).head(20)
        table_df["attendance_date"] = table_df["attendance_date"].dt.strftime(
            "%Y-%m-%d"
        )

        # Select columns
        display_cols = [
            "attendance_date",
            "class_name",
            "points",
            "teacher_name",
        ]
        table_df = table_df[display_cols]
        table_df.columns = ["Date", "Class", "Points", "Teacher"]

        st.dataframe(table_df, use_container_width=True, hide_index=True)


# ===== TAB 2: SUBMIT FEEDBACK =====
with tab2:
    st.header("💬 Submit Class Feedback")
    st.markdown(
        "Share your thoughts on recent classes. Feedback must be submitted within **7 days** of attending."
    )

    # Fetch recent attendance (last 7 days) without feedback
    try:
        attendance_response = requests.get(
            f"{BASE_URL}/attendance/user/{user['user_uuid']}"
        )
        if attendance_response.status_code == 200:
            all_attendance = attendance_response.json()
        else:
            all_attendance = []
    except Exception as e:
        st.error(f"Failed to fetch attendance: {e}")
        all_attendance = []

    if not all_attendance:
        st.info("No recent classes found.")
        st.stop()

    # Filter last 7 days
    df_attendance = pd.DataFrame(all_attendance)
    df_attendance["attendance_date"] = pd.to_datetime(df_attendance["attendance_date"])
    seven_days_ago = datetime.now() - timedelta(days=7)
    df_recent = df_attendance[df_attendance["attendance_date"] >= seven_days_ago].copy()

    if df_recent.empty:
        st.info(
            "No classes attended in the last 7 days. Feedback window is 7 days after class date."
        )
        st.stop()

    # Fetch existing feedback
    try:
        feedback_response = requests.get(
            f"{BASE_URL}/feedback/user/{user['user_uuid']}"
        )
        existing_feedback = (
            feedback_response.json() if feedback_response.status_code == 200 else []
        )
        existing_feedback_ids = {fb["attendance_id"] for fb in existing_feedback}
    except Exception as e:
        st.warning(f"Could not fetch existing feedback: {e}")
        existing_feedback_ids = set()

    # Filter out classes with feedback
    df_recent["has_feedback"] = df_recent["id"].isin(existing_feedback_ids)

    st.subheader("📝 Classes Awaiting Feedback")

    # Show classes without feedback
    no_feedback = df_recent[~df_recent["has_feedback"]].copy()

    if no_feedback.empty:
        st.success("✅ You've submitted feedback for all recent classes!")
    else:
        for idx, row in no_feedback.iterrows():
            with st.expander(
                f"📅 {row['class_name']} - {row['attendance_date'].strftime('%Y-%m-%d')} (Teacher: {row.get('teacher_name', 'N/A')})"
            ):
                with st.form(f"feedback_form_{row['id']}"):
                    rating = st.radio(
                        "How was this class?",
                        options=["thumbs_up", "thumbs_down"],
                        format_func=lambda x: "👍 Thumbs Up"
                        if x == "thumbs_up"
                        else "👎 Thumbs Down",
                        key=f"rating_{row['id']}",
                    )

                    comment = st.text_area(
                        "Comments (optional)",
                        placeholder="Share your thoughts on what you learned, enjoyed, or would like to improve...",
                        key=f"comment_{row['id']}",
                    )

                    submit_feedback = st.form_submit_button("Submit Feedback")

                    if submit_feedback:
                        # Submit to API
                        feedback_data = {
                            "attendance_id": int(row["id"]),
                            "rating": rating,
                            "comment": comment if comment else None,
                        }

                        try:
                            response = requests.post(
                                f"{BASE_URL}/feedback/", json=feedback_data
                            )
                            if response.status_code == 201:
                                st.success("✅ Feedback submitted successfully!")
                                st.rerun()
                            else:
                                st.error(f"Failed to submit feedback: {response.text}")
                        except Exception as e:
                            st.error(f"Error submitting feedback: {e}")

    st.divider()

    # --- VIEW SUBMITTED FEEDBACK ---
    st.subheader("📋 Your Submitted Feedback")

    if not existing_feedback:
        st.info("You haven't submitted any feedback yet.")
    else:
        feedback_df = pd.DataFrame(existing_feedback)
        feedback_df["created_at"] = pd.to_datetime(feedback_df["created_at"])
        feedback_df = feedback_df.sort_values("created_at", ascending=False)

        for idx, fb in feedback_df.iterrows():
            rating_emoji = "👍" if fb["rating"] == "thumbs_up" else "👎"
            with st.expander(
                f"{rating_emoji} {fb['class_name']} - {fb['class_date']} (Teacher: {fb.get('teacher_name', 'N/A')})"
            ):
                st.markdown(f"**Rating:** {rating_emoji}")
                if fb.get("comment"):
                    st.markdown(f"**Comment:** {fb['comment']}")
                st.caption(
                    f"Submitted on: {fb['created_at'].strftime('%Y-%m-%d %H:%M')}"
                )
