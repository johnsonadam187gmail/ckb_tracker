"""
Test file for mat-side workflow endpoints (Phase 2).

Tests the new attendance endpoints:
- POST /attendance/check-in
- GET /attendance/pending/{class_id}/{date}
- POST /attendance/{id}/confirm
- DELETE /attendance/{id}/cancel
- POST /attendance/direct
- POST /attendance/bulk-confirm
- POST /attendance/expire-old
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys

sys.path.insert(0, "..")

from app.main import app
from app.database import get_db
from app import models
from app.auth import get_password_hash, create_teacher_token

client = TestClient(app)


def get_test_db():
    """Get database session for testing."""
    db = next(get_db())
    try:
        return db
    finally:
        db.close()


class TestMatSideWorkflow:
    """Test class for mat-side workflow endpoints."""

    def test_student_self_check_in_creates_pending(self):
        """Verify student self check-in creates PENDING record."""
        db = get_test_db()

        # Find a test user and class
        user = db.query(models.User).filter(models.User.is_current == True).first()
        class_schedule = db.query(models.ClassSchedule).first()

        if not user or not class_schedule:
            pytest.skip("No test data available")

        # Clean up any existing attendance
        db.query(models.FactAttendance).filter(
            models.FactAttendance.user_uuid == user.user_uuid,
            models.FactAttendance.class_id == class_schedule.id,
        ).delete()
        db.commit()

        # Make check-in request
        response = client.post(
            "/attendance/check-in",
            json={
                "user_uuid": user.user_uuid,
                "class_id": class_schedule.id,
                "attendance_date": str(date.today()),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["user_uuid"] == user.user_uuid
        assert data["class_id"] == class_schedule.id

        # Cleanup
        db.query(models.FactAttendance).filter(
            models.FactAttendance.id == data["id"]
        ).delete()
        db.commit()

    def test_duplicate_check_in_returns_existing(self):
        """Verify duplicate check-in returns existing record (idempotent)."""
        db = get_test_db()

        user = db.query(models.User).filter(models.User.is_current == True).first()
        class_schedule = db.query(models.ClassSchedule).first()

        if not user or not class_schedule:
            pytest.skip("No test data available")

        # Clean up
        db.query(models.FactAttendance).filter(
            models.FactAttendance.user_uuid == user.user_uuid,
            models.FactAttendance.class_id == class_schedule.id,
        ).delete()
        db.commit()

        # First check-in
        response1 = client.post(
            "/attendance/check-in",
            json={
                "user_uuid": user.user_uuid,
                "class_id": class_schedule.id,
                "attendance_date": str(date.today()),
            },
        )

        assert response1.status_code == 200
        first_id = response1.json()["id"]

        # Second check-in (should return same record)
        response2 = client.post(
            "/attendance/check-in",
            json={
                "user_uuid": user.user_uuid,
                "class_id": class_schedule.id,
                "attendance_date": str(date.today()),
            },
        )

        assert response2.status_code == 200
        assert response2.json()["id"] == first_id

        # Cleanup
        db.query(models.FactAttendance).filter(
            models.FactAttendance.id == first_id
        ).delete()
        db.commit()

    def test_get_pending_check_ins(self):
        """Verify getting pending check-ins for a class."""
        db = get_test_db()

        class_schedule = db.query(models.ClassSchedule).first()
        if not class_schedule:
            pytest.skip("No test classes available")

        # Get pending check-ins
        response = client.get(f"/attendance/pending/{class_schedule.id}/{date.today()}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_cancel_own_check_in(self):
        """Verify student can cancel their own pending check-in."""
        db = get_test_db()

        user = db.query(models.User).filter(models.User.is_current == True).first()
        class_schedule = db.query(models.ClassSchedule).first()

        if not user or not class_schedule:
            pytest.skip("No test data available")

        # Create a pending check-in
        response = client.post(
            "/attendance/check-in",
            json={
                "user_uuid": user.user_uuid,
                "class_id": class_schedule.id,
                "attendance_date": str(date.today()),
            },
        )

        assert response.status_code == 200
        attendance_id = response.json()["id"]

        # Cancel it
        response = client.delete(
            f"/attendance/{attendance_id}/cancel",
            params={"user_uuid": user.user_uuid},
        )

        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()

        # Verify it's deleted
        attendance = (
            db.query(models.FactAttendance)
            .filter(models.FactAttendance.id == attendance_id)
            .first()
        )
        assert attendance is None


class TestMatSideWorkflowWithAuth:
    """Test class for authenticated mat-side workflow endpoints."""

    def test_confirm_attendance_requires_auth(self):
        """Verify confirming attendance requires authentication."""
        # Try without auth header
        response = client.post("/attendance/123/confirm")

        assert response.status_code == 401

    def test_bulk_confirm_requires_auth(self):
        """Verify bulk confirm requires authentication."""
        response = client.post(
            "/attendance/bulk-confirm",
            json={"attendance_ids": [1, 2, 3]},
        )

        assert response.status_code == 401

    def test_direct_attendance_requires_auth(self):
        """Verify direct attendance requires authentication."""
        response = client.post(
            "/attendance/direct",
            json={
                "user_uuid": "test-uuid",
                "class_id": 1,
                "attendance_date": str(date.today()),
            },
        )

        assert response.status_code == 401


class TestExpireOldPending:
    """Test the expire-old endpoint."""

    def test_expire_old_pending(self):
        """Verify old pending records are expired."""
        response = client.post("/attendance/expire-old")

        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
