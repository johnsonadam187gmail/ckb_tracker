"""Simple seed script without unicode characters."""

import requests

BASE_URL = "http://127.0.0.1:8000"


def seed_data():
    print("Seeding test data...")

    # Create test users
    users = [
        {
            "first_name": "Admin",
            "last_name": "User",
            "email": "admin@ckb.com",
            "password": "admin123",
            "rank": "Black",
        },
        {
            "first_name": "Teacher",
            "last_name": "User",
            "email": "teacher@ckb.com",
            "password": "teacher123",
            "rank": "Brown",
        },
        {
            "first_name": "Student",
            "last_name": "User",
            "email": "student@ckb.com",
            "password": "student123",
            "rank": "Blue",
        },
    ]

    created_users = []
    for user_data in users:
        try:
            response = requests.post(f"{BASE_URL}/users/", data=user_data)
            if response.status_code == 200:
                user = response.json()
                created_users.append(user)
                print(f"Created user: {user['first_name']} {user['last_name']}")
            else:
                print(f"Error creating {user_data['first_name']}: {response.text}")
        except Exception as e:
            print(f"Exception creating {user_data['first_name']}: {e}")

    # Assign roles
    if created_users:
        print("\nAssigning roles...")

        # Get roles
        roles_res = requests.get(f"{BASE_URL}/roles/")
        if roles_res.status_code == 200:
            roles = {r["name"]: r["id"] for r in roles_res.json()}

            # Assign Teacher role to teacher user
            teacher = next(
                (u for u in created_users if u["email"] == "teacher@ckb.com"), None
            )
            if teacher:
                requests.put(
                    f"{BASE_URL}/roles/user/{teacher['user_uuid']}",
                    json={"role_ids": [roles["Student"], roles["Teacher"]]},
                )
                print(f"Assigned Teacher role to {teacher['first_name']}")

            # Assign Admin role to admin user
            admin = next(
                (u for u in created_users if u["email"] == "admin@ckb.com"), None
            )
            if admin:
                requests.put(
                    f"{BASE_URL}/roles/user/{admin['user_uuid']}",
                    json={
                        "role_ids": [roles["Student"], roles["Teacher"], roles["Admin"]]
                    },
                )
                print(f"Assigned Admin role to {admin['first_name']}")

    print(f"\nDone! Created {len(created_users)} users.")
    print("\nTest accounts:")
    print("  Admin: admin@ckb.com / admin123")
    print("  Teacher: teacher@ckb.com / teacher123")
    print("  Student: student@ckb.com / student123")


if __name__ == "__main__":
    seed_data()
