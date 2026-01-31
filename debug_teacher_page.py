"""
Debug script to test Teacher Dashboard endpoint calls.
Run while server is running: python debug_teacher_page.py
"""

import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000"


def debug_teacher_dashboard():
    print("Debugging Teacher Dashboard Endpoint")
    print("=" * 60)

    try:
        # 1. Get classes
        print("\n1. Fetching classes...")
        class_res = requests.get(f"{BASE_URL}/classes/")
        if class_res.status_code == 200:
            classes = class_res.json()
            print(f"   Found {len(classes)} classes")
            if classes:
                test_class = classes[0]
                print(f"   Test class: {test_class['class_name']}")
                print(f"   Class ID: {test_class['id']}")

                # 2. Test the exact endpoint Teacher page uses
                print(f"\n2. Testing attendance endpoint...")
                class_name = test_class["class_name"]
                today = str(date.today())

                print(f"   URL: {BASE_URL}/attendance/class/{class_name}")
                print(f"   Params: start_date={today}, end_date={today}")

                attendance_res = requests.get(
                    f"{BASE_URL}/attendance/class/{class_name}",
                    params={"start_date": today, "end_date": today},
                )

                print(f"   Status Code: {attendance_res.status_code}")

                if attendance_res.status_code == 200:
                    data = attendance_res.json()
                    print(f"   ✓ Success! Found {len(data)} students")
                    if data:
                        print(f"   Sample record: {data[0]}")
                    else:
                        print("   (No students checked in for this class today)")
                elif attendance_res.status_code == 500:
                    print(f"   ✗ 500 Error!")
                    print(f"   Response: {attendance_res.text}")
                else:
                    print(f"   ✗ Error {attendance_res.status_code}")
                    print(f"   Response: {attendance_res.text}")

        else:
            print(f"   ✗ Failed to fetch classes: {class_res.status_code}")

    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to server")
        print("   Please start server with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_teacher_dashboard()
