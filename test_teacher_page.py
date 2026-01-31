"""
Test script to verify Teacher page functionality.
Prerequisites: FastAPI server must be running on port 8000
Run: python test_teacher_page.py
"""

import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000"


def test_teacher_workflow():
    print("Testing Teacher Page Workflow")
    print("=" * 60)

    try:
        # 1. Get all teachers
        print("\n1. Fetching teachers...")
        teachers_res = requests.get(f"{BASE_URL}/roles/users/by-role/Teacher")
        if teachers_res.status_code == 200:
            teachers = teachers_res.json()
            print(f"   Found {len(teachers)} teachers")
            if teachers:
                for t in teachers:
                    print(f"   - {t['first_name']} {t['last_name']} ({t['user_uuid']})")
        else:
            print(f"   Error fetching teachers: {teachers_res.status_code}")
            return False

        # 2. Get all classes
        print("\n2. Fetching classes...")
        classes_res = requests.get(f"{BASE_URL}/classes/")
        if classes_res.status_code == 200:
            classes = classes_res.json()
            print(f"   Found {len(classes)} classes")
            if classes:
                for c in classes:
                    print(f"   - {c['class_name']} ({c['time']})")
        else:
            print(f"   Error fetching classes: {classes_res.status_code}")
            return False

        # 3. Get attendance for a class
        if classes:
            print(f"\n3. Fetching attendance for class: {classes[0]['class_name']}...")
            attendance_res = requests.get(
                f"{BASE_URL}/attendance/class/{classes[0]['class_name']}",
                params={"start_date": str(date.today()), "end_date": str(date.today())},
            )

            if attendance_res.status_code == 200:
                attendance = attendance_res.json()
                print(f"   Found {len(attendance)} attendance records for today")

                # 4. Test updating teacher (if attendance exists and teachers exist)
                if attendance and teachers:
                    print(f"\n4. Testing teacher assignment...")
                    attendance_id = attendance[0]["id"]
                    teacher_uuid = teachers[0]["user_uuid"]

                    update_res = requests.put(
                        f"{BASE_URL}/attendance/{attendance_id}/teacher",
                        json={"teacher_uuid": teacher_uuid},
                    )

                    if update_res.status_code == 200:
                        print(
                            f"   ✓ Successfully assigned teacher to attendance record {attendance_id}"
                        )
                        print(f"   Response: {update_res.json()}")
                    else:
                        print(
                            f"   ✗ Failed to assign teacher: {update_res.status_code}"
                        )
                        print(f"   Error: {update_res.text}")
                        return False
                else:
                    print("   [SKIP] No attendance records or teachers to test with")
            else:
                print(f"   Error fetching attendance: {attendance_res.status_code}")

        print("\n" + "=" * 60)
        print("✓ Teacher page workflow test complete!")
        print("=" * 60)
        return True

    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to FastAPI server")
        print("  Please start the server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_teacher_workflow()
