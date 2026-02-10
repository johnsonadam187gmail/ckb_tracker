"""Cloudinary service for image upload and management."""

import io
import re
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path

import cloudinary
import cloudinary.uploader
from PIL import Image, ExifTags

from ..config import settings


class CloudinaryService:
    """Service for handling image uploads to Cloudinary."""

    def __init__(self):
        """Initialize Cloudinary configuration."""
        if not all(
            [
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key,
                settings.cloudinary_api_secret,
            ]
        ):
            raise ValueError(
                "Cloudinary credentials not configured. "
                "Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, "
                "and CLOUDINARY_API_SECRET environment variables."
            )

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

    def _process_image(
        self,
        image_bytes: bytes,
        target_size: Tuple[int, int] = (400, 400),
        quality: int = 80,
    ) -> bytes:
        """
        Process image: resize, compress, strip EXIF data.

        Args:
            image_bytes: Raw image bytes
            target_size: Target dimensions (width, height)
            quality: JPEG quality (1-100)

        Returns:
            Processed image bytes
        """
        # Open image from bytes
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (handles PNG with transparency)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Auto-rotate based on EXIF orientation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == "Orientation":
                    break
            exif = img._getexif()
            if exif is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # No EXIF data or orientation tag
            pass

        # Calculate crop dimensions to maintain aspect ratio
        width, height = img.size
        target_width, target_height = target_size

        # Calculate scaling factors
        scale_w = target_width / width
        scale_h = target_height / height
        scale = max(scale_w, scale_h)

        # Calculate new dimensions
        new_width = int(width * scale)
        new_height = int(height * scale)

        # Resize image
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate crop box for center crop
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # Crop to target size
        img = img.crop((left, top, right, bottom))

        # Save to bytes with compression
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)

        return output.getvalue()

    def _validate_image(self, image_bytes: bytes, max_size_mb: int = 5) -> None:
        """
        Validate image before processing.

        Args:
            image_bytes: Raw image bytes
            max_size_mb: Maximum file size in MB

        Raises:
            ValueError: If validation fails
        """
        # Check file size
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValueError(f"Image too large: {size_mb:.1f}MB (max {max_size_mb}MB)")

        # Check image format
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.format not in ["JPEG", "JPG", "PNG"]:
                raise ValueError(f"Unsupported format: {img.format}. Use JPEG or PNG.")
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")

    def upload_profile_photo(
        self, image_bytes: bytes, user_uuid: str, old_public_id: Optional[str] = None
    ) -> dict:
        """
        Upload a profile photo to Cloudinary.

        Args:
            image_bytes: Raw image bytes
            user_uuid: User's UUID for naming
            old_public_id: Public ID of old photo to delete (optional)

        Returns:
            Dictionary with 'url', 'public_id', 'thumbnail_url'

        Raises:
            ValueError: If image validation fails
            Exception: If upload fails
        """
        # Validate image
        self._validate_image(image_bytes)

        # Process image
        processed_bytes = self._process_image(image_bytes)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        public_id = f"{settings.cloudinary_folder}/{user_uuid}_{timestamp}"

        # Delete old photo if exists
        if old_public_id:
            try:
                cloudinary.uploader.destroy(old_public_id)
            except Exception:
                # Continue even if delete fails
                pass

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            io.BytesIO(processed_bytes),
            public_id=public_id,
            folder=settings.cloudinary_folder,
            resource_type="image",
            eager=[
                {"width": 100, "height": 100, "crop": "fill", "quality": "auto"},
                {
                    "width": 400,
                    "height": 400,
                    "crop": "fill",
                    "quality": "auto",
                    "fetch_format": "auto",
                },
            ],
            transformation=[
                {"width": 400, "height": 400, "crop": "fill"},
                {"quality": "auto"},
                {"fetch_format": "auto"},
            ],
        )

        # Generate thumbnail URL
        thumbnail_url = cloudinary.utils.cloudinary_url(
            public_id,
            width=100,
            height=100,
            crop="fill",
            quality="auto",
            fetch_format="auto",
        )[0]

        return {
            "url": upload_result["secure_url"],
            "public_id": public_id,
            "thumbnail_url": thumbnail_url,
            "width": upload_result.get("width"),
            "height": upload_result.get("height"),
            "bytes": upload_result.get("bytes"),
            "format": upload_result.get("format"),
        }

    def delete_photo(self, public_id: str) -> bool:
        """
        Delete a photo from Cloudinary.

        Args:
            public_id: The public ID of the image to delete

        Returns:
            True if deletion was successful
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception:
            return False

    def extract_public_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract Cloudinary public ID from a URL.

        Args:
            url: Cloudinary image URL

        Returns:
            Public ID string or None if not a Cloudinary URL
        """
        # Pattern to match Cloudinary URL and extract public_id
        # Example: https://res.cloudinary.com/cloudname/image/upload/v1234567890/folder/image.jpg
        pattern = r"/upload/(?:v\d+/)?(.+?)(?:\.[^.]+)?$"
        match = re.search(pattern, url)

        if match:
            return match.group(1)
        return None


# Global service instance
cloudinary_service = CloudinaryService()
