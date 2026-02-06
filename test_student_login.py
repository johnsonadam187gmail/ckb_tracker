"""
Test script for student login endpoint.
Run with backend server at http://127.0.0.1:8000
"""

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_student_login():
    """Test the student login endpoint"""

    print("=" * 60)
    print("Student Login Test")
    print("=" * 60)

    # Step 1: Create a test student
    print("\n1. Creating test student...")
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "email": f"teststudent_{__import__('uuid').uuid4().hex[:8]}@test.com",
        "rank": "White Belt",
        "password": "student123",
    }

    response = requests.post(f"{BASE_URL}/users/", json=student_data)
    if response.status_code == 200:
        user = response.json()
        print(f"✅ Student created: {user['email']}")
        email = user["email"]
        user_uuid = user["user_uuid"]
    else:
        print(f"❌ Failed to create student: {response.status_code} - {response.text}")
        return False

    # Step 2: Try to login with correct credentials
    print("\n2. Testing login with correct credentials...")
    login_data = {"email": email, "password": "student123"}

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        user_info = response.json()
        print(f"✅ Login successful!")
        print(f"   User: {user_info['first_name']} {user_info['last_name']}")
        print(f"   Email: {user_info['email']}")
        print(f"   UUID: {user_info['user_uuid']}")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return False

    # Step 3: Try to login with wrong password
    print("\n3. Testing login with wrong password...")
    wrong_login = {"email": email, "password": "wrongpassword"}

    response = requests.post(f"{BASE_URL}/auth/login", json=wrong_login)
    if response.status_code == 401:
        print(f"✅ Correctly rejected wrong password")
    else:
        print(f"❌ Should have rejected wrong password: {response.status_code}")
        return False

    # Step 4: Remove password and try to login
    print("\n4. Testing login after password removal...")
    response = requests.delete(f"{BASE_URL}/auth/remove-password/{user_uuid}")
    if response.status_code == 200:
        print(f"✅ Password removed")
    else:
        print(f"❌ Failed to remove password: {response.status_code}")
        return False

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 401:
        print(f"✅ Correctly rejected login without password")
        error_detail = response.json().get("detail", "")
        if "No password set" in error_detail:
            print(f"   Error message: {error_detail}")
    else:
        print(f"❌ Should have rejected login without password: {response.status_code}")
        return False

    # Step 5: Set password and try again
    print("\n5. Testing login after password reset...")
    password_data = {"user_uuid": user_uuid, "password": "newpassword456"}
    response = requests.post(f"{BASE_URL}/auth/set-password", json=password_data)
    if response.status_code == 200:
        print(f"✅ Password reset")
    else:
        print(f"❌ Failed to reset password: {response.status_code}")
        return False

    new_login = {"email": email, "password": "newpassword456"}
    response = requests.post(f"{BASE_URL}/auth/login", json=new_login)
    if response.status_code == 200:
        print(f"✅ Login successful with new password")
    else:
        print(f"❌ Login failed with new password: {response.status_code}")
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    return True


def check_server():
    """Check if backend server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    if not check_server():
        print("❌ Backend server is not running!")
        print("Please start: uvicorn app.main:app --reload")
        exit(1)

    print("✅ Backend server is running\n")
    success = test_student_login()
    exit(0 if success else 1)
