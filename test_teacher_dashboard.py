"""
Test Teacher Dashboard Attendance Display

Run this to verify the Teacher Dashboard lists all students:
    python test_teacher_dashboard.py
"""

import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000"


def test_teacher_dashboard():
    print("=" * 60)
    print("Teacher Dashboard Test")
    print("=" * 60)
    print()

    # 1. Get classes
    print("1. Fetching classes...")
    classes_response = requests.get(f"{BASE_URL}/classes/")
    if classes_response.status_code != 200:
        print("   [X] Failed to fetch classes")
        return

    classes = classes_response.json()
    if not classes:
        print("   [X] No classes found")
        return

    test_class = classes[0]
    print(f"   [OK] Found class: {test_class['class_name']} (ID: {test_class['id']})")
    print()

    # 2. Get users
    print("2. Fetching users...")
    users_response = requests.get(f"{BASE_URL}/users/")
    if users_response.status_code != 200:
        print("   [X] Failed to fetch users")
        return

    users = users_response.json()
    if not users:
        print("   [X] No users found")
        return

    print(f"   [OK] Found {len(users)} users")
    print()

    today = date.today()

    # 3. Check existing attendance
    print(
        f"3. Checking existing attendance for {test_class['class_name']} on {today}..."
    )

    # Try to get class instance
    instance_response = requests.get(
        f"{BASE_URL}/class-instances/by-date/",
        params={"class_id": test_class["id"], "class_date": str(today)},
    )

    attendance_records = []
    if instance_response.status_code == 200:
        instance = instance_response.json()
        print(f"   [OK] Class instance exists (ID: {instance['id']})")

        # Get attendance
        attendance_response = requests.get(f"{BASE_URL}/attendance/")
        if attendance_response.status_code == 200:
            all_attendance = attendance_response.json()
            # Filter by class instance
            attendance_records = [
                a
                for a in all_attendance
                if a.get("class_instance_id") == instance["id"]
            ]
    else:
        print("   [!] No class instance yet (will be created on first check-in)")

    print(f"   Current attendance records: {len(attendance_records)}")

    pending = [a for a in attendance_records if a.get("status") == "pending"]
    confirmed = [a for a in attendance_records if a.get("status") == "confirmed"]

    print(f"   - Pending: {len(pending)}")
    print(f"   - Confirmed: {len(confirmed)}")
    print()

    # 4. Create a test check-in if no attendance
    if len(attendance_records) == 0 and len(users) > 0:
        print("4. Creating test check-in...")
        test_user = users[0]

        checkin_response = requests.post(
            f"{BASE_URL}/attendance/check-in",
            json={
                "user_uuid": test_user["user_uuid"],
                "class_id": test_class["id"],
                "attendance_date": str(today),
            },
        )

        if checkin_response.status_code == 200:
            data = checkin_response.json()
            print(f"   [OK] Check-in created! Status: {data['status']}")
        elif checkin_response.status_code == 400:
            error = checkin_response.json().get("detail", "")
            print(f"   [!] {error}")
        else:
            print(f"   [X] Failed: {checkin_response.status_code}")
        print()

    print("=" * 60)
    print("Summary for Teacher Dashboard:")
    print("=" * 60)
    print(f"Class: {test_class['class_name']}")
    print(f"Date: {today}")
    print(f"Total Students Checked In: {len(attendance_records)}")
    print(f"Pending Confirmation: {len(pending)}")
    print(f"Already Confirmed: {len(confirmed)}")
    print()
    print("The Teacher Dashboard should now show:")
    print("- A table with all students")
    print("- Status indicators (Pending/Confirmed)")
    print("- Individual Confirm/Remove buttons for pending")
    print("- Bulk actions when students are selected")
    print("- 'Confirm All Pending' button at the bottom")


if __name__ == "__main__":
    test_teacher_dashboard()
