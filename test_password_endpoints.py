"""
Functional test script for password management endpoints.
Run this with backend server running at http://127.0.0.1:8000
"""

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_password_management():
    """Test the password management endpoints functionality."""

    # Step 1: Create a test user
    print("1. Creating test user...")
    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"testuser_{__import__('uuid').uuid4().hex[:8]}@test.com",
        "rank": "White Belt",
        "password": "testpass123",
    }

    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    if response.status_code == 200:
        user = response.json()
        user_uuid = user["user_uuid"]
        print(f"✅ User created: {user_uuid}")
    else:
        print(f"❌ Failed to create user: {response.status_code} - {response.text}")
        return False

    # Step 2: Check password status
    print("\n2. Checking initial password status...")
    response = requests.get(f"{BASE_URL}/auth/check-password/{user_uuid}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Password check successful: has_password={data['has_password']}")
        if not data["has_password"]:
            print("⚠️ Warning: Password should be set but check shows False")
    else:
        print(f"❌ Failed to check password: {response.status_code} - {response.text}")
        return False

    # Step 3: Update password
    print("\n3. Updating password...")
    password_data = {"user_uuid": user_uuid, "password": "newpassword456"}
    response = requests.post(f"{BASE_URL}/auth/set-password", json=password_data)
    if response.status_code == 200:
        print(f"✅ Password updated successfully")
    else:
        print(f"❌ Failed to update password: {response.status_code} - {response.text}")
        return False

    # Step 4: Check password status again
    print("\n4. Verifying password after update...")
    response = requests.get(f"{BASE_URL}/auth/check-password/{user_uuid}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Password check after update: has_password={data['has_password']}")
        if not data["has_password"]:
            print("❌ ERROR: Password should be set!")
            return False
    else:
        print(f"❌ Failed to check password: {response.status_code} - {response.text}")
        return False

    # Step 5: Remove password
    print("\n5. Removing password...")
    response = requests.delete(f"{BASE_URL}/auth/remove-password/{user_uuid}")
    if response.status_code == 200:
        print(f"✅ Password removed successfully")
    else:
        print(f"❌ Failed to remove password: {response.status_code} - {response.text}")
        return False

    # Step 6: Check password status after removal
    print("\n6. Verifying password removed...")
    response = requests.get(f"{BASE_URL}/auth/check-password/{user_uuid}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Password check after removal: has_password={data['has_password']}")
        if data["has_password"]:
            print("❌ ERROR: Password should be removed!")
            return False
    else:
        print(f"❌ Failed to check password: {response.status_code} - {response.text}")
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    return True


def check_server():
    """Check if backend server is running."""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("Password Management Endpoints - Functional Test")
    print("=" * 60)

    if not check_server():
        print("❌ Backend server is not running!")
        print("Please start the server with: uvicorn app.main:app --reload")
        exit(1)

    print("✅ Backend server is running\n")

    success = test_password_management()
    exit(0 if success else 1)
