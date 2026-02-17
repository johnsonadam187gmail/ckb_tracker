"""
Quick Test Script for Mat-Side Workflow

Run this to test if students can check in and appear in the pending list:
    python test_workflow_quick.py
"""

import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000"


def test_workflow():
    print("=" * 60)
    print("Mat-Side Workflow Quick Test")
    print("=" * 60)
    print()

    # 1. Get a class
    print("1. Fetching classes...")
    classes_response = requests.get(f"{BASE_URL}/classes/")
    if classes_response.status_code != 200:
        print("   [X] Failed to fetch classes")
        return

    classes = classes_response.json()
    if not classes:
        print("   [X] No classes found in database")
        return

    test_class = classes[0]
    print(f"   [OK] Found class: {test_class['class_name']}")
    print()

    # 2. Get a user
    print("2. Fetching users...")
    users_response = requests.get(f"{BASE_URL}/users/")
    if users_response.status_code != 200:
        print("   [X] Failed to fetch users")
        return

    users = users_response.json()
    if not users:
        print("   [X] No users found in database")
        return

    test_user = users[0]
    print(f"   [OK] Found user: {test_user['first_name']} {test_user['last_name']}")
    print()

    # 3. Check current pending list
    today = date.today()
    print(f"3. Checking pending check-ins for {test_class['class_name']} on {today}...")
    pending_response = requests.get(
        f"{BASE_URL}/attendance/pending/{test_class['id']}/{today}"
    )

    if pending_response.status_code == 200:
        pending = pending_response.json()
        print(f"   Current pending count: {len(pending)}")
    print()

    # 4. Student self check-in
    print("4. Creating student self check-in (PENDING status)...")
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
        print(f"   [OK] Check-in created!")
        print(f"      ID: {data['id']}")
        print(f"      Status: {data['status']}")
        print(f"      User: {test_user['first_name']} {test_user['last_name']}")
    elif checkin_response.status_code == 400:
        error = checkin_response.json().get("detail", "Unknown error")
        print(f"   [!]  {error}")
        print("   (User may already be checked in)")
    else:
        print(f"   [X] Failed: {checkin_response.status_code}")
    print()

    # 5. Verify pending list again
    print("5. Verifying pending check-ins again...")
    pending_response2 = requests.get(
        f"{BASE_URL}/attendance/pending/{test_class['id']}/{today}"
    )

    if pending_response2.status_code == 200:
        pending = pending_response2.json()
        print(f"   Current pending count: {len(pending)}")

        if pending:
            print("\n   Pending students:")
            for p in pending:
                print(f"   - {p['student_name']} (checked in at {p['created_at']})")
        else:
            print("   [!]  No pending check-ins found")
    print()

    print("=" * 60)
    print("Test complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Open Teacher Dashboard (pages/4_Teacher.py)")
    print("2. Select the class and today's date")
    print("3. You should see the student in the pending list")
    print("4. Try confirming the check-in")
    print("\nIf you don't see any students:")
    print("- Check that the student checked in successfully above")
    print("- Verify you're looking at the correct class and date")
    print("- Check the browser console for any errors")


if __name__ == "__main__":
    test_workflow()
