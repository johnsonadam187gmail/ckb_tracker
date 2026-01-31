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

st.title("👨‍🏫 Teacher Dashboard")

# --- CLASS AND DATE SELECTION ---
st.header("Class Roster")

col1, col2, col3 = st.columns(3)

with col1:
    selected_date = st.date_input("Class Date", value=datetime.now())

with col2:
    # Fetch all classes
    class_res = requests.get(f"{BASE_URL}/classes/")
    classes = class_res.json() if class_res.status_code == 200 else []

    # Store full class data for easy access
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
    teachers_res = requests.get(f"{BASE_URL}/roles/users/by-role/Teacher")
    teachers = teachers_res.json() if teachers_res.status_code == 200 else []

    # Teacher selection dropdown
    teacher_options = {"-- No Teacher Assigned --": None}
    if teachers:
        teacher_options.update(
            {f"{t['first_name']} {t['last_name']}": t["user_uuid"] for t in teachers}
        )

    selected_teacher_name = st.selectbox(
        "Assign Teacher",
        options=list(teacher_options.keys()),
        help="Select the teacher who taught this class",
    )

    selected_teacher_uuid = teacher_options[selected_teacher_name]

# --- DISPLAY ENROLLED STUDENTS ---
if selected_class_name != "-- Select Class --":
    class_id = class_data[selected_class_name]["id"]
    class_name = class_data[selected_class_name]["name"]

    st.divider()
    st.subheader(f"Students Enrolled: {selected_class_name}")
    st.caption(f"Date: {selected_date.strftime('%B %d, %Y')}")

    # Fetch attendance records for this class and date
    try:
        attendance_res = requests.get(
            f"{BASE_URL}/attendance/class/{class_name}",
            params={"start_date": str(selected_date), "end_date": str(selected_date)},
        )

        if attendance_res.status_code == 200:
            attendance_data = attendance_res.json()

            if attendance_data:
                # Create DataFrame for display
                df_attendance = pd.DataFrame(attendance_data)

                # Display metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Students", len(df_attendance))
                with col2:
                    if "weighting" in df_attendance.columns:
                        total_points = df_attendance["weighting"].sum()
                        st.metric("Total Points", f"{total_points:.1f}")
                with col3:
                    # Show current teacher if assigned
                    if (
                        selected_teacher_uuid
                        and selected_teacher_name != "-- No Teacher Assigned --"
                    ):
                        st.metric(
                            "Assigned Teacher",
                            selected_teacher_name.replace(
                                "-- No Teacher Assigned --", "None"
                            ),
                        )
                    elif (
                        "teacher_name" in df_attendance.columns
                        and df_attendance["teacher_name"].notna().any()
                    ):
                        teacher_name = df_attendance["teacher_name"].iloc[0]
                        st.metric(
                            "Current Teacher",
                            teacher_name if teacher_name else "Not Assigned",
                        )
                    else:
                        st.metric("Current Teacher", "Not Assigned")

                st.divider()

                # Button to assign teacher to all students in this class
                if (
                    selected_teacher_uuid
                    and selected_teacher_name != "-- No Teacher Assigned --"
                ):
                    if st.button(
                        f"✅ Assign {selected_teacher_name} to All Students",
                        type="primary",
                    ):
                        success_count = 0
                        error_count = 0

                        with st.spinner("Updating attendance records..."):
                            for _, row in df_attendance.iterrows():
                                try:
                                    # Update attendance record with teacher
                                    update_url = (
                                        f"{BASE_URL}/attendance/{row['id']}/teacher"
                                    )
                                    update_res = requests.put(
                                        update_url,
                                        json={"teacher_uuid": selected_teacher_uuid},
                                    )

                                    if update_res.status_code == 200:
                                        success_count += 1
                                    else:
                                        error_count += 1
                                except Exception as e:
                                    error_count += 1

                        if error_count == 0:
                            st.success(
                                f"✅ Successfully assigned teacher to {success_count} students!"
                            )
                            st.rerun()
                        else:
                            st.warning(
                                f"⚠️ Assigned teacher to {success_count} students, {error_count} failed"
                            )

                st.divider()

                # Display student roster
                st.subheader("📋 Student Roster")

                # Format display columns
                display_columns = ["userfullname", "rank_at_time", "weighting"]
                if "teacher_name" in df_attendance.columns:
                    display_columns.append("teacher_name")

                display_df = df_attendance[display_columns].copy()
                display_df.columns = (
                    ["Student Name", "Rank", "Points", "Assigned Teacher"]
                    if "teacher_name" in df_attendance.columns
                    else ["Student Name", "Rank", "Points"]
                )

                st.dataframe(display_df, hide_index=True, width="stretch")

                # Export option
                st.download_button(
                    label="📥 Download Roster (CSV)",
                    data=display_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"roster_{selected_date}_{class_name.replace(' ', '_')}.csv",
                    mime="text/csv",
                )

                st.divider()

                # --- LESSON INFORMATION SECTION ---
                st.subheader("📚 Lesson Information")

                try:
                    # Fetch class instance (lesson) for this class and date
                    lesson_res = requests.get(
                        f"{BASE_URL}/class-instances/by-date/",
                        params={"class_id": class_id, "class_date": str(selected_date)},
                    )

                    if lesson_res.status_code == 200:
                        lesson = lesson_res.json()

                        # Display lesson title if exists
                        if lesson.get("lesson_title"):
                            st.markdown(f"### {lesson['lesson_title']}")
                        else:
                            st.info("No lesson title set for this class")

                        # Display lesson resources
                        col_lesson1, col_lesson2 = st.columns(2)

                        with col_lesson1:
                            if lesson.get("lesson_plan_url"):
                                st.link_button(
                                    "📄 Open Lesson Plan",
                                    lesson["lesson_plan_url"],
                                    use_container_width=True,
                                )
                            else:
                                st.info("📄 No lesson plan available")

                        with col_lesson2:
                            if lesson.get("video_folder_url"):
                                st.link_button(
                                    "🎥 Open Video Folder",
                                    lesson["video_folder_url"],
                                    use_container_width=True,
                                )
                            else:
                                st.info("🎥 No video folder available")

                        # Show lesson metadata
                        with st.expander("📋 Lesson Details"):
                            st.write(f"**Class:** {lesson.get('class_name', 'N/A')}")
                            st.write(f"**Date:** {lesson.get('class_date', 'N/A')}")
                            st.write(
                                f"**Teacher:** {lesson.get('teacher_name', 'Not assigned')}"
                            )
                            if lesson.get("lesson_plan_url"):
                                st.code(lesson["lesson_plan_url"], language=None)
                            if lesson.get("video_folder_url"):
                                st.code(lesson["video_folder_url"], language=None)

                    elif lesson_res.status_code == 404:
                        st.info("ℹ️ No lesson plan has been created for this class yet")
                        st.caption(
                            "Admins can add lesson plans in the Settings page under the Lessons tab"
                        )

                    else:
                        st.warning(
                            f"⚠️ Could not fetch lesson information: {lesson_res.status_code}"
                        )

                except Exception as e:
                    st.warning(f"⚠️ Could not load lesson information: {e}")
                    st.caption("Lesson information may not be available")

            else:
                st.info("ℹ️ No students checked in for this class on the selected date.")
                st.caption("Students must check in via the Attendance page first.")

        elif attendance_res.status_code == 500:
            st.error("⚠️ Server error fetching attendance data")
            st.caption(
                "This might be due to missing data. Please contact support if this persists."
            )
            with st.expander("Technical Details"):
                st.code(attendance_res.text)
        else:
            st.error(
                f"❌ Failed to fetch attendance data: {attendance_res.status_code}"
            )
            st.caption(f"Status: {attendance_res.status_code}")

    except Exception as e:
        st.error(f"⚠️ Connection error: {e}")
        st.caption("Please check that the backend server is running.")

else:
    st.info("👆 Please select a class and date to view enrolled students")
