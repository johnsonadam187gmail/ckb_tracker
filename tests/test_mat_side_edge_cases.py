"""
Edge Case Tests for Mat-Side Workflow

These tests cover edge cases and error conditions:
- Duplicate check-ins
- Unauthorized access
- Invalid inputs
- Boundary conditions
- Race conditions

Run with: pytest tests/test_mat_side_edge_cases.py -v
"""

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient

import sys

sys.path.insert(0, "..")

from app.main import app
from app.database import get_db
from app import models
from app.auth import get_password_hash

client = TestClient(app)


class TestDuplicateCheckInEdgeCases:
    """Test edge cases around duplicate check-ins."""

    def test_check_in_already_confirmed(self):
        """Test that student cannot check in again if already confirmed."""
        db = next(get_db())

        try:
            # Get a user and class
            user = db.query(models.User).filter(models.User.is_current == True).first()
            class_schedule = db.query(models.ClassSchedule).first()

            if not user or not class_schedule:
                pytest.skip("No test data available")

            today = date.today()

            # Clean up any existing records
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid == user.user_uuid,
                models.FactAttendance.class_id == class_schedule.id,
                models.FactAttendance.attendance_date == today,
            ).delete(synchronize_session=False)
            db.commit()

            # Create a confirmed attendance record directly
            confirmed_record = models.FactAttendance(
                user_uuid=user.user_uuid,
                class_id=class_schedule.id,
                attendance_date=today,
                status="confirmed",
                confirmed_by="test-teacher",
                confirmed_at=datetime.now(),
            )
            db.add(confirmed_record)
            db.commit()

            # Try to check in again (should fail)
            response = client.post(
                "/attendance/check-in",
                json={
                    "user_uuid": user.user_uuid,
                    "class_id": class_schedule.id,
                    "attendance_date": str(today),
                },
            )

            # Should return error or existing record with confirmed status
            if response.status_code == 400:
                assert "already" in response.json()["detail"].lower()
            elif response.status_code == 200:
                # If it returns existing, status should be confirmed
                assert response.json()["status"] == "confirmed"

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid == user.user_uuid,
                models.FactAttendance.class_id == class_schedule.id,
            ).delete(synchronize_session=False)
            db.commit()

        finally:
            db.close()

    def test_pending_check_in_is_idempotent(self):
        """Test that multiple pending check-ins return the same record."""
        db = next(get_db())

        try:
            user = db.query(models.User).filter(models.User.is_current == True).first()
            class_schedule = db.query(models.ClassSchedule).first()

            if not user or not class_schedule:
                pytest.skip("No test data available")

            today = date.today()

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid == user.user_uuid,
                models.FactAttendance.class_id == class_schedule.id,
            ).delete(synchronize_session=False)
            db.commit()

            # First check-in
            response1 = client.post(
                "/attendance/check-in",
                json={
                    "user_uuid": user.user_uuid,
                    "class_id": class_schedule.id,
                    "attendance_date": str(today),
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
                    "attendance_date": str(today),
                },
            )

            assert response2.status_code == 200
            second_id = response2.json()["id"]

            # Both should return the same ID
            assert first_id == second_id

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.id == first_id
            ).delete(synchronize_session=False)
            db.commit()

        finally:
            db.close()


class TestAuthorizationEdgeCases:
    """Test authorization and authentication edge cases."""

    def test_confirm_without_auth_token(self):
        """Test that confirming attendance requires authentication."""
        response = client.post("/attendance/123/confirm")

        assert response.status_code == 401
        assert (
            "authentication" in response.json()["detail"].lower()
            or "required" in response.json()["detail"].lower()
        )

    def test_confirm_with_invalid_token(self):
        """Test that invalid tokens are rejected."""
        response = client.post(
            "/attendance/123/confirm", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    def test_direct_add_without_auth(self):
        """Test that direct add requires authentication."""
        response = client.post(
            "/attendance/direct",
            json={
                "user_uuid": "test-uuid",
                "class_id": 1,
                "attendance_date": str(date.today()),
            },
        )

        assert response.status_code == 401

    def test_bulk_confirm_without_auth(self):
        """Test that bulk confirm requires authentication."""
        response = client.post(
            "/attendance/bulk-confirm", json={"attendance_ids": [1, 2, 3]}
        )

        assert response.status_code == 401


class TestInputValidationEdgeCases:
    """Test input validation edge cases."""

    def test_user_search_single_character(self):
        """Test that single character search is rejected."""
        response = client.get("/users/search?query=a")

        assert response.status_code == 400
        assert "2 characters" in response.json()["detail"].lower()

    def test_user_search_empty_string(self):
        """Test that empty search is handled."""
        response = client.get("/users/search?query=")

        # Should either return empty results or error
        assert response.status_code in [200, 400]

    def test_check_in_invalid_date_format(self):
        """Test check-in with invalid date format."""
        db = next(get_db())

        try:
            user = db.query(models.User).filter(models.User.is_current == True).first()
            class_schedule = db.query(models.ClassSchedule).first()

            if not user or not class_schedule:
                pytest.skip("No test data available")

            # Try with invalid date
            response = client.post(
                "/attendance/check-in",
                json={
                    "user_uuid": user.user_uuid,
                    "class_id": class_schedule.id,
                    "attendance_date": "invalid-date",
                },
            )

            # Should fail validation
            assert response.status_code == 422

        finally:
            db.close()

    def test_check_in_nonexistent_user(self):
        """Test check-in with non-existent user."""
        db = next(get_db())

        try:
            class_schedule = db.query(models.ClassSchedule).first()

            if not class_schedule:
                pytest.skip("No test class available")

            response = client.post(
                "/attendance/check-in",
                json={
                    "user_uuid": "nonexistent-user-uuid-12345",
                    "class_id": class_schedule.id,
                    "attendance_date": str(date.today()),
                },
            )

            # Should handle gracefully (might create record or fail)
            assert response.status_code in [200, 400, 404, 422]

        finally:
            db.close()

    def test_check_in_nonexistent_class(self):
        """Test check-in with non-existent class."""
        db = next(get_db())

        try:
            user = db.query(models.User).filter(models.User.is_current == True).first()

            if not user:
                pytest.skip("No test user available")

            response = client.post(
                "/attendance/check-in",
                json={
                    "user_uuid": user.user_uuid,
                    "class_id": 99999,  # Non-existent class
                    "attendance_date": str(date.today()),
                },
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 404]

        finally:
            db.close()


class TestCancellationEdgeCases:
    """Test edge cases around cancellation."""

    def test_cancel_wrong_student(self):
        """Test that students can only cancel their own check-ins."""
        db = next(get_db())

        try:
            users = (
                db.query(models.User)
                .filter(models.User.is_current == True)
                .limit(2)
                .all()
            )
            class_schedule = db.query(models.ClassSchedule).first()

            if len(users) < 2 or not class_schedule:
                pytest.skip("Need at least 2 users and 1 class")

            student1 = users[0]
            student2 = users[1]
            today = date.today()

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid.in_(
                    [student1.user_uuid, student2.user_uuid]
                ),
                models.FactAttendance.class_id == class_schedule.id,
            ).delete(synchronize_session=False)
            db.commit()

            # Student 1 checks in
            response = client.post(
                "/attendance/check-in",
                json={
                    "user_uuid": student1.user_uuid,
                    "class_id": class_schedule.id,
                    "attendance_date": str(today),
                },
            )

            assert response.status_code == 200
            attendance_id = response.json()["id"]

            # Student 2 tries to cancel Student 1's check-in
            cancel_response = client.delete(
                f"/attendance/{attendance_id}/cancel",
                params={"user_uuid": student2.user_uuid},
            )

            # Should be forbidden
            assert cancel_response.status_code in [403, 400]

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.id == attendance_id
            ).delete(synchronize_session=False)
            db.commit()

        finally:
            db.close()

    def test_cancel_already_confirmed(self):
        """Test that confirmed attendance cannot be cancelled."""
        db = next(get_db())

        try:
            user = db.query(models.User).filter(models.User.is_current == True).first()
            class_schedule = db.query(models.ClassSchedule).first()

            if not user or not class_schedule:
                pytest.skip("No test data available")

            today = date.today()

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid == user.user_uuid,
                models.FactAttendance.class_id == class_schedule.id,
            ).delete(synchronize_session=False)
            db.commit()

            # Create confirmed record
            confirmed = models.FactAttendance(
                user_uuid=user.user_uuid,
                class_id=class_schedule.id,
                attendance_date=today,
                status="confirmed",
                confirmed_by="test-teacher",
                confirmed_at=datetime.now(),
            )
            db.add(confirmed)
            db.commit()
            db.refresh(confirmed)

            # Try to cancel confirmed record
            cancel_response = client.delete(
                f"/attendance/{confirmed.id}/cancel",
                params={"user_uuid": user.user_uuid},
            )

            # Should fail
            assert cancel_response.status_code == 400
            assert "confirmed" in cancel_response.json()["detail"].lower()

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.id == confirmed.id
            ).delete(synchronize_session=False)
            db.commit()

        finally:
            db.close()


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_pin_validation_length_boundaries(self):
        """Test PIN length validation boundaries."""
        # Too short (3 digits)
        response = client.post("/kiosk/verify-pin", json={"pin": "123"})
        # Should fail validation or authentication
        assert response.status_code in [400, 401]

        # Valid length (4 digits)
        response = client.post("/kiosk/verify-pin", json={"pin": "1234"})
        # May succeed or fail based on current PIN
        assert response.status_code in [200, 401]

        # Maximum length (6 digits)
        response = client.post("/kiosk/verify-pin", json={"pin": "123456"})
        assert response.status_code in [200, 401]

        # Too long (7 digits)
        response = client.post("/kiosk/verify-pin", json={"pin": "1234567"})
        assert response.status_code in [400, 401]

    def test_pin_non_numeric(self):
        """Test that non-numeric PINs are rejected."""
        response = client.post("/kiosk/verify-pin", json={"pin": "abcd"})

        assert response.status_code in [400, 422, 401]

    def test_bulk_confirm_empty_list(self):
        """Test bulk confirm with empty list."""
        db = next(get_db())

        try:
            # Get teacher token
            teacher = (
                db.query(models.User)
                .filter(
                    models.User.email == "test_teacher_workflow@example.com",
                    models.User.is_current == True,
                )
                .first()
            )

            if not teacher:
                pytest.skip("No test teacher available")

            login_response = client.post(
                "/auth/teacher-login",
                data={"username": teacher.email, "password": "password123"},
            )

            if login_response.status_code != 200:
                pytest.skip("Could not authenticate teacher")

            token = login_response.json()["access_token"]

            # Try bulk confirm with empty list
            response = client.post(
                "/attendance/bulk-confirm",
                json={"attendance_ids": []},
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 404]

        finally:
            db.close()


class TestConcurrentAccess:
    """Test concurrent access scenarios (basic)."""

    def test_multiple_students_same_class(self):
        """Test multiple students checking in to the same class."""
        db = next(get_db())

        try:
            users = (
                db.query(models.User)
                .filter(models.User.is_current == True)
                .limit(5)
                .all()
            )

            class_schedule = db.query(models.ClassSchedule).first()

            if len(users) < 3 or not class_schedule:
                pytest.skip("Need at least 3 users and 1 class")

            today = date.today()

            # Clean up existing records
            db.query(models.FactAttendance).filter(
                models.FactAttendance.class_id == class_schedule.id,
                models.FactAttendance.attendance_date == today,
            ).delete(synchronize_session=False)
            db.commit()

            # Multiple students check in
            attendance_ids = []
            for user in users[:3]:
                response = client.post(
                    "/attendance/check-in",
                    json={
                        "user_uuid": user.user_uuid,
                        "class_id": class_schedule.id,
                        "attendance_date": str(today),
                    },
                )

                if response.status_code == 200:
                    attendance_ids.append(response.json()["id"])

            # All should succeed
            assert len(attendance_ids) == 3

            # Verify all are in pending list
            pending_response = client.get(
                f"/attendance/pending/{class_schedule.id}/{today}"
            )

            assert pending_response.status_code == 200
            pending_list = pending_response.json()
            assert len(pending_list) == 3

            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.id.in_(attendance_ids)
            ).delete(synchronize_session=False)
            db.commit()

        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
