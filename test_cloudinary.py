#!/usr/bin/env python3
"""Test script for Cloudinary integration."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()


def test_cloudinary_config():
    """Test that Cloudinary configuration is loaded correctly."""
    print("Testing Cloudinary Configuration...")

    from app.config import settings

    # Check that all required settings are present
    required_settings = [
        "cloudinary_cloud_name",
        "cloudinary_api_key",
        "cloudinary_api_secret",
        "cloudinary_folder",
    ]

    missing = []
    for setting in required_settings:
        value = getattr(settings, setting)
        if not value:
            missing.append(setting)
            print(f"  [X] {setting}: NOT SET")
        else:
            # Mask sensitive values
            if "secret" in setting.lower():
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"  [OK] {setting}: {display_value}")

    if missing:
        print(f"\n[X] Configuration test FAILED - Missing: {', '.join(missing)}")
        return False

    print("\n[OK] Configuration test PASSED")
    return True


def test_cloudinary_service():
    """Test that Cloudinary service can be initialized."""
    print("\nTesting Cloudinary Service Initialization...")

    try:
        from app.services.cloudinary_service import cloudinary_service

        print("  [OK] Cloudinary service initialized successfully")
        return True
    except ValueError as e:
        print(f"  [X] Failed to initialize: {e}")
        return False
    except Exception as e:
        print(f"  [X] Unexpected error: {e}")
        return False


def test_image_processing():
    """Test image processing without uploading."""
    print("\nTesting Image Processing...")

    try:
        from PIL import Image
        import io

        # Create a test image
        img = Image.new("RGB", (800, 600), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        img_bytes.seek(0)

        print("  [OK] Test image created successfully")

        # Test processing
        from app.services.cloudinary_service import cloudinary_service

        processed = cloudinary_service._process_image(
            img_bytes.getvalue(), target_size=(400, 400)
        )

        # Verify processed image
        processed_img = Image.open(io.BytesIO(processed))
        print(
            f"  [OK] Image processed: {processed_img.size[0]}x{processed_img.size[1]}"
        )

        # Check dimensions
        assert processed_img.size == (400, 400), (
            f"Expected 400x400, got {processed_img.size}"
        )
        print("  [OK] Image dimensions correct")

        return True

    except Exception as e:
        print(f"  [X] Image processing failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cloudinary_upload():
    """Test uploading an image to Cloudinary."""
    print("\nTesting Cloudinary Upload...")

    try:
        from PIL import Image
        import io
        from app.services.cloudinary_service import cloudinary_service

        # Create a test image
        img = Image.new("RGB", (800, 600), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        img_bytes.seek(0)

        print("  [UPLOAD] Uploading test image...")

        # Upload
        result = cloudinary_service.upload_profile_photo(
            image_bytes=img_bytes.getvalue(), user_uuid="test_user_123"
        )

        print(f"  [OK] Upload successful!")
        print(f"     URL: {result['url'][:60]}...")
        print(f"     Public ID: {result['public_id']}")
        print(f"     Size: {result.get('bytes', 'unknown')} bytes")

        # Test deletion
        print("  [DELETE] Deleting test image...")
        deleted = cloudinary_service.delete_photo(result["public_id"])

        if deleted:
            print("  [OK] Test image deleted successfully")
        else:
            print("  [!] Could not delete test image (may need manual cleanup)")

        return True

    except Exception as e:
        print(f"  [X] Upload test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Cloudinary Integration Test Suite")
    print("=" * 60)

    tests = [
        ("Configuration", test_cloudinary_config),
        ("Service Initialization", test_cloudinary_service),
        ("Image Processing", test_image_processing),
        ("Cloudinary Upload", test_cloudinary_upload),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[X] {name} test crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, result in results:
        status = "[OK] PASSED" if result else "[X] FAILED"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All tests passed! Cloudinary integration is working.")
        return 0
    else:
        print("\n[!] Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
