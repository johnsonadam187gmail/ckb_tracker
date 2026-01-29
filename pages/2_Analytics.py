import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Analytics", layout="wide", page_icon="📊")


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


st.title("📊 Analytics Dashboard")


# --- 1. DATA FETCHING ---
@st.cache_data(ttl=60)
def fetch_meta_data():
    try:
        users = requests.get(f"{BASE_URL}/users/").json()
        terms = requests.get(f"{BASE_URL}/terms/").json()
        targets = requests.get(f"{BASE_URL}/term-targets/").json()
        return users, terms, targets
    except Exception as e:
        st.error(f"Failed to fetch metadata: {e}")
        return [], [], []


users, terms, targets = fetch_meta_data()

if not users:
    st.warning("No users found. Please add members in the Management Console.")
    st.stop()

# --- 2. SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filter Analytics")

# Map full names to user objects
user_map = {f"{u['first_name']} {u['last_name']}": u for u in users}
selected_student_name = st.sidebar.selectbox(
    "Select Student", options=list(user_map.keys())
)

term_map = {t["term_name"]: t for t in terms}
term_options = ["All Time"] + list(term_map.keys())
selected_term_name = st.sidebar.selectbox("Filter by Term", options=term_options)

# Get selected user details
user = user_map[selected_student_name]
user_uuid = user["user_uuid"]

# Date range logic
if selected_term_name != "All Time":
    term = term_map[selected_term_name]
    start_dt = term["start_date"]
    end_dt = term["end_date"]
else:
    # Default to last 365 days for "All Time"
    start_dt = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_dt = datetime.now().strftime("%Y-%m-%d")

# --- 3. FETCH ATTENDANCE (SAFE HANDLING) ---
attendance_data = []
try:
    att_res = requests.get(
        f"{BASE_URL}/attendance/user/{user_uuid}?start={start_dt}&end={end_dt}"
    )

    if att_res.status_code == 200:
        raw_data = att_res.json()
        # Verify we actually received a list of records
        if isinstance(raw_data, list):
            attendance_data = raw_data
        else:
            st.error("API returned an unexpected format. Expected a list.")
    else:
        st.info(f"No attendance records found for this period.")
except Exception as e:
    st.error(f"Connection Error: {e}")

# --- 4. KPI & GAUGE CHART ---
st.header(f"Performance: {selected_student_name} ({user['rank']})")
kpi1, kpi2, chart_col = st.columns([1, 1, 2])

# Initialize totals
total_points = 0.0
total_classes = 0

if attendance_data:
    df_att = pd.DataFrame(attendance_data)

    # 1. Identify the weighting column dynamically
    weight_col = next(
        (c for c in ["class_weighting", "weighting", "weight"] if c in df_att.columns),
        None,
    )

    if weight_col:
        # Convert to numeric to ensure we can sum safely
        df_att[weight_col] = pd.to_numeric(df_att[weight_col], errors="coerce").fillna(
            0
        )
        total_points = float(df_att[weight_col].sum())
    else:
        # Fallback if the column is missing: count classes as 1.0 each
        total_points = float(len(attendance_data))

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
                if t["term_id"] == term["id"] and t["rank"] == user["rank"]
            ),
            None,
        )
        if relevant_target:
            target_val = float(relevant_target["target"])

    # GAUGE: Comparing Sum of Weightings to Term Target
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=total_points,  # <--- This is now the sum of weights
            title={"text": f"Mat Point Goal: {target_val}", "font": {"size": 18}},
            delta={"reference": target_val, "increasing": {"color": "#00cc96"}},
            gauge={
                "axis": {"range": [None, max(target_val * 1.2, total_points + 5)]},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [0, target_val], "color": "#e5ecf6"},
                    {"range": [target_val, target_val * 1.2], "color": "#d1f2eb"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": target_val,
                },
            },
        )
    )
    fig_gauge.update_layout(height=300, margin=dict(l=30, r=30, t=50, b=20))
    st.plotly_chart(fig_gauge, width="stretch")

# --- 5. VISUALIZATIONS ---
st.divider()
col_left, col_right = st.columns(2)

if attendance_data:
    df_att = pd.DataFrame(attendance_data)

    # 1. Dynamic Column Identification (Matches common naming conventions)
    # Search for the most likely columns in the API response
    time_col = next(
        (
            c
            for c in ["check_in_time", "timestamp", "created_at"]
            if c in df_att.columns
        ),
        None,
    )
    name_col = next(
        (c for c in ["class_name", "name", "label"] if c in df_att.columns), None
    )
    weight_col = next(
        (c for c in ["class_weighting", "weighting", "weight"] if c in df_att.columns),
        None,
    )

    # 2. Validation: Ensure we have at least the basics
    if not weight_col:
        # Fallback: Create a weighting of 1.0 if the column is missing
        df_att["class_weighting"] = 1.0
        weight_col = "class_weighting"

    if time_col:
        df_att["date"] = pd.to_datetime(df_att[time_col]).dt.date

        with col_left:
            st.subheader("Attendance History")
            # Group by date and sum weights
            daily_points = df_att.groupby("date")[weight_col].sum().reset_index()
            daily_points["cumulative"] = daily_points[weight_col].cumsum()

            fig_line = px.area(
                daily_points,
                x="date",
                y="cumulative",
                title="Cumulative Points Accumulation",
                color_discrete_sequence=["#1f77b4"],
            )
            st.plotly_chart(fig_line, width="stretch")

    with col_right:
        st.subheader("Class Distribution")
        if name_col:
            # FIX: Only call px.pie if we have valid columns to avoid the ValueError
            fig_pie = px.pie(
                df_att,
                names=name_col,
                values=weight_col,
                hole=0.4,
                title="Points by Class Type",
            )
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("No class names found to categorize distribution.")

    # --- 6. DETAILED LOG ---
    st.divider()
    st.subheader("📋 Detailed Attendance Log")

    # Select only existing columns for the final display
    display_cols = [
        c for c in [time_col, name_col, "day", weight_col] if c in df_att.columns
    ]
    df_display = df_att[display_cols].copy()

    # Beautify the timestamp if it exists
    if time_col in df_display.columns:
        df_display[time_col] = pd.to_datetime(df_display[time_col]).dt.strftime(
            "%b %d, %Y - %H:%M"
        )

    st.dataframe(df_display, width="stretch", hide_index=True)

else:
    st.info("No attendance data to display for the selected criteria.")
