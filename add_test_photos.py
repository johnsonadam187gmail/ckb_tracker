"""Add photos to test users."""

import requests
from PIL import Image, ImageDraw, ImageFont
import io

BASE_URL = "http://127.0.0.1:8000"


def create_test_photo(name, color):
    """Create a simple test photo with name."""
    img = Image.new("RGB", (400, 400), color=color)
    draw = ImageDraw.Draw(img)

    # Draw name
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # Center text
    bbox = draw.textbbox((0, 0), name, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (400 - text_width) // 2
    y = (400 - text_height) // 2

    draw.text((x, y), name, fill="white", font=font)

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=90)
    img_bytes.seek(0)

    return img_bytes.getvalue()


def add_photos():
    print("Adding photos to test users...")

    # Get all users
    response = requests.get(f"{BASE_URL}/users/")
    if response.status_code != 200:
        print(f"Error fetching users: {response.text}")
        return

    users = response.json()

    # Photo config
    photos = {
        "admin@ckb.com": ("Admin", "darkblue"),
        "teacher@ckb.com": ("Teacher", "darkgreen"),
        "student@ckb.com": ("Student", "darkred"),
    }

    for user in users:
        email = user["email"]
        if email in photos:
            name, color = photos[email]
            print(f"Adding photo for {name} ({email})...")

            try:
                # Create photo
                photo_bytes = create_test_photo(name, color)

                # Upload
                files = {
                    "file": (f"{name.lower()}_photo.jpg", photo_bytes, "image/jpeg")
                }

                response = requests.post(
                    f"{BASE_URL}/users/{user['user_uuid']}/photo", files=files
                )

                if response.status_code == 200:
                    result = response.json()
                    print(f"  Photo added: {result['photo_url'][:60]}...")
                else:
                    print(f"  Error: {response.text}")

            except Exception as e:
                print(f"  Exception: {e}")

    print("\nDone! Photos added to test users.")
    print("You can now see photos in the Daily Attendance page.")


if __name__ == "__main__":
    add_photos()
