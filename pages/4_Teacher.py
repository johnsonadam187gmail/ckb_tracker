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

col1, col2, col3, col4 = st.columns([1, 2, 2, 1.5])

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

    # Store for later use (will be set after we fetch ClassInstance)
    default_teacher_index = 0

    selected_teacher_name = st.selectbox(
        "Assign Teacher",
        options=list(teacher_options.keys()),
        index=default_teacher_index,
        help="Select the teacher who taught this class",
        key=f"teacher_select_{selected_date}_{selected_class_name}",
    )

    selected_teacher_uuid = teacher_options[selected_teacher_name]

with col4:
    # Spacer to align button with dropdowns
    st.write("")

    # Teacher Assignment Button
    if selected_class_name != "-- Select Class --":
        if (
            selected_teacher_uuid
            and selected_teacher_name != "-- No Teacher Assigned --"
        ):
            # Enabled button
            if st.button(
                "💾 Assign Teacher",
                type="primary",
                use_container_width=True,
                help=f"Assign {selected_teacher_name} to {selected_class_name} on {selected_date.strftime('%Y-%m-%d')}",
            ):
                # Get class_id from selected class
                class_id = class_data[selected_class_name]["id"]

                with st.spinner("Assigning teacher..."):
                    try:
                        # Check if ClassInstance exists
                        instance_check = requests.get(
                            f"{BASE_URL}/class-instances/by-date/",
                            params={
                                "class_id": class_id,
                                "class_date": str(selected_date),
                            },
                        )

                        if instance_check.status_code == 200:
                            # Update existing ClassInstance
                            instance_id = instance_check.json()["id"]
                            update_res = requests.put(
                                f"{BASE_URL}/class-instances/{instance_id}",
                                json={"teacher_uuid": selected_teacher_uuid},
                            )
                            action = "updated"
                        else:
                            # Create new ClassInstance
                            update_res = requests.post(
                                f"{BASE_URL}/class-instances/",
                                json={
                                    "class_id": class_id,
                                    "class_date": str(selected_date),
                                    "teacher_uuid": selected_teacher_uuid,
                                    "lesson_id": None,
                                },
                            )
                            action = "assigned"

                        if update_res.status_code == 200:
                            st.success(
                                f"✅ {selected_teacher_name} {action} successfully!"
                            )
                            st.toast(f"Teacher {action}!", icon="✅")
                            st.rerun()
                        else:
                            detail = update_res.json().get("detail", "Unknown error")
                            st.error(f"❌ Failed to assign teacher: {detail}")

                    except Exception as e:
                        st.error(f"⚠️ Connection error: {e}")
        else:
            # Disabled button - no teacher selected
            st.button(
                "💾 Assign Teacher",
                disabled=True,
                use_container_width=True,
                help="Select a teacher first",
            )
    else:
        # Disabled button - no class selected
        st.button(
            "💾 Assign Teacher",
            disabled=True,
            use_container_width=True,
            help="Select a class first",
        )

# --- DISPLAY ENROLLED STUDENTS ---
if selected_class_name != "-- Select Class --":
    class_id = class_data[selected_class_name]["id"]
    class_name = class_data[selected_class_name]["name"]

    st.divider()
    st.subheader(f"Students Enrolled: {selected_class_name}")
    st.caption(f"Date: {selected_date.strftime('%B %d, %Y')}")

    # Fetch ClassInstance to get current teacher assignment
    current_instance = None
    try:
        instance_res = requests.get(
            f"{BASE_URL}/class-instances/by-date/",
            params={"class_id": class_id, "class_date": str(selected_date)},
        )
        if instance_res.status_code == 200:
            current_instance = instance_res.json()
    except Exception:
        # ClassInstance may not exist yet - that's okay
        pass

    # Fetch attendance records for this class and date
    try:
        attendance_res = requests.get(
            f"{BASE_URL}/attendance/class/{class_name}",
            params={"start_date": str(selected_date), "end_date": str(selected_date)},
        )

        if attendance_res.status_code == 200:
            attendance_data = attendance_res.json()

            # Always show teacher assignment interface, even if no students
            # Create DataFrame for display (empty if no students)
            df_attendance = (
                pd.DataFrame(attendance_data) if attendance_data else pd.DataFrame()
            )

            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Students", len(df_attendance))
            with col2:
                if len(df_attendance) > 0 and "points" in df_attendance.columns:
                    total_points = df_attendance["points"].sum()
                    st.metric("Total Points", f"{total_points:.1f}")
                else:
                    st.metric("Total Points", "0.0")
            with col3:
                # Show current teacher from ClassInstance
                if current_instance and current_instance.get("teacher_name"):
                    st.metric("Current Teacher", current_instance["teacher_name"])
                else:
                    st.metric("Current Teacher", "Not Assigned")

            st.divider()

            # Show info if no students checked in yet
            if len(df_attendance) == 0:
                st.info(
                    "ℹ️ No students have checked in yet. Teacher can be assigned using the button at the top."
                )

            # Display student roster only if there are students
            if attendance_data:
                st.subheader("📋 Student Roster")

                # Format display columns
                display_columns = ["userfullname", "rank_at_time", "points"]
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
            # Always show lesson section (uses ClassInstance we already fetched)
            st.subheader("📚 Lesson Information")

            if current_instance:
                # Display lesson title if exists
                if current_instance.get("lesson_title"):
                    st.markdown(f"### {current_instance['lesson_title']}")
                else:
                    st.info("No lesson title set for this class")

                # Display lesson resources
                col_lesson1, col_lesson2 = st.columns(2)

                with col_lesson1:
                    if current_instance.get("lesson_plan_url"):
                        st.link_button(
                            "📄 Open Lesson Plan",
                            current_instance["lesson_plan_url"],
                            use_container_width=True,
                        )
                    else:
                        st.info("📄 No lesson plan available")

                with col_lesson2:
                    if current_instance.get("video_folder_url"):
                        st.link_button(
                            "🎥 Open Video Folder",
                            current_instance["video_folder_url"],
                            use_container_width=True,
                        )
                    else:
                        st.info("🎥 No video folder available")

                # Show lesson metadata
                with st.expander("📋 Lesson Details"):
                    st.write(f"**Class:** {current_instance.get('class_name', 'N/A')}")
                    st.write(f"**Date:** {current_instance.get('class_date', 'N/A')}")
                    st.write(
                        f"**Teacher:** {current_instance.get('teacher_name', 'Not assigned')}"
                    )
                    if current_instance.get("lesson_plan_url"):
                        st.code(current_instance["lesson_plan_url"], language=None)
                    if current_instance.get("video_folder_url"):
                        st.code(current_instance["video_folder_url"], language=None)

            else:
                st.info("ℹ️ No lesson plan has been created for this class yet")
                st.caption(
                    "Admins can add lesson plans in the Settings page under the Lessons tab"
                )

            st.divider()

            # --- FEEDBACK SECTION ---
            st.subheader("💬 Student Feedback")

            # Get feedback stats for this class instance
            if current_instance:
                try:
                    feedback_res = requests.get(
                        f"{BASE_URL}/feedback/class-instance/{current_instance['id']}/stats"
                    )
                    if feedback_res.status_code == 200:
                        feedback_stats = feedback_res.json()

                        # Display metrics
                        col_fb1, col_fb2, col_fb3, col_fb4 = st.columns(4)

                        with col_fb1:
                            st.metric(
                                "Total Feedback",
                                feedback_stats["total_feedback"],
                            )

                        with col_fb2:
                            st.metric("👍 Thumbs Up", feedback_stats["thumbs_up_count"])

                        with col_fb3:
                            st.metric(
                                "👎 Thumbs Down", feedback_stats["thumbs_down_count"]
                            )

                        with col_fb4:
                            st.metric(
                                "Response Rate",
                                f"{feedback_stats['feedback_rate']:.1f}%",
                            )

                        # Calculate sentiment
                        if feedback_stats["total_feedback"] > 0:
                            positive_rate = (
                                feedback_stats["thumbs_up_count"]
                                / feedback_stats["total_feedback"]
                                * 100
                            )

                            if positive_rate >= 80:
                                sentiment = "🎉 Excellent!"
                                sentiment_color = "green"
                            elif positive_rate >= 60:
                                sentiment = "😊 Good"
                                sentiment_color = "blue"
                            elif positive_rate >= 40:
                                sentiment = "😐 Mixed"
                                sentiment_color = "orange"
                            else:
                                sentiment = "😔 Needs Improvement"
                                sentiment_color = "red"

                            st.markdown(
                                f"**Overall Sentiment:** :{sentiment_color}[{sentiment}]"
                            )

                            # Fetch individual feedback comments
                            try:
                                # Get all feedback for this class instance (need to fetch individually)
                                comments = []
                                if attendance_data:
                                    for att in attendance_data:
                                        try:
                                            fb_res = requests.get(
                                                f"{BASE_URL}/feedback/attendance/{att['id']}"
                                            )
                                            if fb_res.status_code == 200:
                                                fb_data = fb_res.json()
                                                if fb_data.get("comment"):
                                                    comments.append(
                                                        {
                                                            "student": fb_data[
                                                                "user_full_name"
                                                            ],
                                                            "rating": fb_data["rating"],
                                                            "comment": fb_data[
                                                                "comment"
                                                            ],
                                                        }
                                                    )
                                        except:
                                            continue

                                if comments:
                                    with st.expander("📝 View Comments"):
                                        for comment in comments:
                                            rating_emoji = (
                                                "👍"
                                                if comment["rating"] == "thumbs_up"
                                                else "👎"
                                            )
                                            st.markdown(
                                                f"{rating_emoji} **{comment['student']}**: {comment['comment']}"
                                            )
                                            st.markdown("---")
                            except Exception as e:
                                st.caption(f"Could not load comments: {e}")

                        else:
                            st.info(
                                "No feedback submitted yet for this class. Encourage students to share their thoughts!"
                            )

                    else:
                        st.info("No feedback available for this class yet")

                except Exception as e:
                    st.warning(f"Could not load feedback: {e}")
            else:
                st.info(
                    "Select a class and date to view feedback (class instance must exist)"
                )

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
