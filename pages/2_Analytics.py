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

# Check user's roles
user_roles_res = requests.get(f"{BASE_URL}/roles/user/{user_uuid}")
user_roles = user_roles_res.json() if user_roles_res.status_code == 200 else []
user_role_names = [r["role_name"] for r in user_roles]

# Determine analytics view
is_teacher = "Teacher" in user_role_names

# Add analytics type selector
if is_teacher:
    analytics_type = st.sidebar.radio(
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

# --- 4. ANALYTICS DISPLAY (BASED ON TYPE) ---
if analytics_type == "Student":
    st.header(f"Student Performance: {selected_student_name} ({user['rank']})")
    kpi1, kpi2, chart_col = st.columns([1, 1, 2])

    # Initialize totals
    total_points = 0.0
    total_classes = 0

    if attendance_data:
        df_att = pd.DataFrame(attendance_data)

        # 1. Use points column
        points_col = "points"

        # Convert to numeric to ensure we can sum safely
        df_att[points_col] = pd.to_numeric(df_att[points_col], errors="coerce").fillna(
            0
        )
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
        points_col = "points"

        # 2. Validation: Ensure we have at least the basics
        if "points" not in df_att.columns:
            # Fallback: Create points of 1.0 if the column is missing
            df_att["points"] = 1.0
            points_col = "points"

        if time_col:
            df_att["date"] = pd.to_datetime(df_att[time_col]).dt.date

            with col_left:
                st.subheader("Attendance History")
                # Group by date and sum points
                daily_points = df_att.groupby("date")[points_col].sum().reset_index()
                daily_points["cumulative"] = daily_points[points_col].cumsum()

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
                    st.metric("Total Students", int(df_teacher["student_count"].sum()))
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
                        .agg({"class_date": "count", "student_count": "sum"})
                        .reset_index()
                    )
                    class_summary.columns = ["Class Type", "Sessions", "Total Students"]

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
                    df_teacher["class_date"] = pd.to_datetime(df_teacher["class_date"])
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
                display_df = df_teacher[["class_date", "class_name", "student_count"]]
                display_df.columns = ["Date", "Class", "Students"]
                st.dataframe(display_df, hide_index=True, width="stretch")
            else:
                st.info("No teaching records found for this period")
        else:
            st.error("Failed to fetch teacher analytics")
    except Exception as e:
        st.error(f"Error fetching teacher analytics: {e}")


# ===== FEEDBACK ANALYTICS SECTION =====
st.divider()
st.header("💬 Class Feedback Analytics")

# Fetch all class instances
try:
    instances_response = requests.get(f"{BASE_URL}/class-instances/")
    if instances_response.status_code == 200:
        all_instances = instances_response.json()
    else:
        all_instances = []
except Exception as e:
    st.error(f"Failed to fetch class instances: {e}")
    all_instances = []

if not all_instances:
    st.info("No class instances found.")
else:
    # Filter instances with feedback
    instances_with_feedback = []
    feedback_stats = []

    for instance in all_instances:
        try:
            stats_response = requests.get(
                f"{BASE_URL}/feedback/class-instance/{instance['id']}/stats"
            )
            if stats_response.status_code == 200:
                stats = stats_response.json()
                if stats["total_feedback"] > 0:
                    feedback_stats.append(stats)
                    instances_with_feedback.append(instance)
        except:
            continue

    if not feedback_stats:
        st.info(
            "No feedback submitted yet. Encourage students to share their thoughts!"
        )
    else:
        df_feedback = pd.DataFrame(feedback_stats)

        # --- FEEDBACK METRICS ---
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_feedback = df_feedback["total_feedback"].sum()
            st.metric("Total Feedback", total_feedback)

        with col2:
            total_thumbs_up = df_feedback["thumbs_up_count"].sum()
            st.metric("👍 Thumbs Up", total_thumbs_up)

        with col3:
            total_thumbs_down = df_feedback["thumbs_down_count"].sum()
            st.metric("👎 Thumbs Down", total_thumbs_down)

        with col4:
            avg_feedback_rate = df_feedback["feedback_rate"].mean()
            st.metric("Avg Feedback Rate", f"{avg_feedback_rate:.1f}%")

        st.divider()

        # --- FEEDBACK TREND CHART ---
        st.subheader("📈 Feedback Trend Over Time")

        df_feedback["class_date"] = pd.to_datetime(df_feedback["class_date"])
        df_feedback_sorted = df_feedback.sort_values("class_date")

        # Create stacked bar chart
        theme = get_chart_theme()
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=df_feedback_sorted["class_date"],
                y=df_feedback_sorted["thumbs_up_count"],
                name="Thumbs Up",
                marker_color=theme["colors"][2],  # Green
            )
        )

        fig.add_trace(
            go.Bar(
                x=df_feedback_sorted["class_date"],
                y=df_feedback_sorted["thumbs_down_count"],
                name="Thumbs Down",
                marker_color=theme["colors"][0],  # Red
            )
        )

        fig.update_layout(
            barmode="stack",
            title="Feedback by Date",
            xaxis_title="Date",
            yaxis_title="Feedback Count",
            template=theme["template"],
            paper_bgcolor=theme["paper_bgcolor"],
            plot_bgcolor=theme["plot_bgcolor"],
            font_color=theme["font_color"],
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # --- FEEDBACK BY CLASS ---
        st.subheader("📊 Feedback by Class")

        # Group by class name
        class_feedback = (
            df_feedback.groupby("class_name")
            .agg(
                {
                    "thumbs_up_count": "sum",
                    "thumbs_down_count": "sum",
                    "total_feedback": "sum",
                    "feedback_rate": "mean",
                }
            )
            .reset_index()
        )

        # Create grouped bar chart
        fig2 = go.Figure()

        fig2.add_trace(
            go.Bar(
                x=class_feedback["class_name"],
                y=class_feedback["thumbs_up_count"],
                name="Thumbs Up",
                marker_color=theme["colors"][2],
            )
        )

        fig2.add_trace(
            go.Bar(
                x=class_feedback["class_name"],
                y=class_feedback["thumbs_down_count"],
                name="Thumbs Down",
                marker_color=theme["colors"][0],
            )
        )

        fig2.update_layout(
            barmode="group",
            title="Feedback Summary by Class",
            xaxis_title="Class",
            yaxis_title="Feedback Count",
            template=theme["template"],
            paper_bgcolor=theme["paper_bgcolor"],
            plot_bgcolor=theme["plot_bgcolor"],
            font_color=theme["font_color"],
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # --- DETAILED FEEDBACK TABLE ---
        st.subheader("📋 Detailed Feedback Report")

        # Prepare table
        table_df = df_feedback.copy()
        table_df["class_date"] = table_df["class_date"].dt.strftime("%Y-%m-%d")
        table_df["positive_rate"] = (
            table_df["thumbs_up_count"] / table_df["total_feedback"] * 100
        ).round(1)

        display_table = table_df[
            [
                "class_date",
                "class_name",
                "teacher_name",
                "thumbs_up_count",
                "thumbs_down_count",
                "total_feedback",
                "total_attendees",
                "feedback_rate",
                "positive_rate",
            ]
        ]

        display_table.columns = [
            "Date",
            "Class",
            "Teacher",
            "👍",
            "👎",
            "Total Feedback",
            "Total Students",
            "Response Rate %",
            "Positive %",
        ]

        st.dataframe(display_table, use_container_width=True, hide_index=True)
