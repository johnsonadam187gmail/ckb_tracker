"""
Integration Tests for Mat-Side Workflow

These tests verify the complete end-to-end workflow:
1. Student self check-in (creates PENDING)
2. Teacher views pending check-ins
3. Teacher confirms attendance
4. Auto-expiry of old pending records

Run with: pytest tests/test_mat_side_integration.py -v
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
from app.auth import get_password_hash

client = TestClient(app)


class TestMatSideIntegrationWorkflow:
    """Integration tests for complete mat-side workflow."""

    def setup_method(self):
        """Set up test data before each test."""
        db = next(get_db())
        try:
            # Create test student
            self.student = (
                db.query(models.User)
                .filter(
                    models.User.email == "test_student_workflow@example.com",
                    models.User.is_current == True,
                )
                .first()
            )

            if not self.student:
                # Create new test student
                self.student = models.User(
                    user_uuid="test-student-workflow-uuid",
                    first_name="Test",
                    last_name="StudentWorkflow",
                    email="test_student_workflow@example.com",
                    password_hash=get_password_hash("password123"),
                    rank="White",
                    is_current=True,
                )
                db.add(self.student)
                db.flush()

                # Assign Student role
                student_role = (
                    db.query(models.Role).filter(models.Role.name == "Student").first()
                )
                if student_role:
                    user_role = models.UserRole(
                        user_uuid=self.student.user_uuid,
                        role_id=student_role.id,
                        is_current=True,
                    )
                    db.add(user_role)
                db.commit()

            # Create test teacher
            self.teacher = (
                db.query(models.User)
                .filter(
                    models.User.email == "test_teacher_workflow@example.com",
                    models.User.is_current == True,
                )
                .first()
            )

            if not self.teacher:
                self.teacher = models.User(
                    user_uuid="test-teacher-workflow-uuid",
                    first_name="Test",
                    last_name="TeacherWorkflow",
                    email="test_teacher_workflow@example.com",
                    password_hash=get_password_hash("password123"),
                    rank="Black",
                    is_current=True,
                )
                db.add(self.teacher)
                db.flush()

                # Assign Teacher role
                teacher_role = (
                    db.query(models.Role).filter(models.Role.name == "Teacher").first()
                )
                if teacher_role:
                    user_role = models.UserRole(
                        user_uuid=self.teacher.user_uuid,
                        role_id=teacher_role.id,
                        is_current=True,
                    )
                    db.add(user_role)
                db.commit()

            # Get or create test class
            self.test_class = db.query(models.ClassSchedule).first()

            # Get teacher token for auth
            login_response = client.post(
                "/auth/teacher-login",
                data={"username": self.teacher.email, "password": "password123"},
            )
            if login_response.status_code == 200:
                self.teacher_token = login_response.json()["access_token"]
            else:
                self.teacher_token = None

        finally:
            db.close()

    def teardown_method(self):
        """Clean up test data after each test."""
        db = next(get_db())
        try:
            # Clean up attendance records
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid.in_(
                    ["test-student-workflow-uuid", "test-teacher-workflow-uuid"]
                )
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def test_complete_workflow_student_to_teacher(self):
        """Test complete workflow: Student check-in → Teacher confirmation."""
        if not self.test_class:
            pytest.skip("No test class available")

        today = date.today()

        # Step 1: Student self check-in (creates PENDING)
        check_in_response = client.post(
            "/attendance/check-in",
            json={
                "user_uuid": self.student.user_uuid,
                "class_id": self.test_class.id,
                "attendance_date": str(today),
            },
        )

        assert check_in_response.status_code == 200
        attendance_data = check_in_response.json()
        assert attendance_data["status"] == "pending"
        attendance_id = attendance_data["id"]

        # Step 2: Teacher views pending check-ins
        pending_response = client.get(
            f"/attendance/pending/{self.test_class.id}/{today}"
        )

        assert pending_response.status_code == 200
        pending_list = pending_response.json()
        assert len(pending_list) >= 1
        assert any(p["user_uuid"] == self.student.user_uuid for p in pending_list)

        # Step 3: Teacher confirms attendance
        if self.teacher_token:
            confirm_response = client.post(
                f"/attendance/{attendance_id}/confirm",
                headers={"Authorization": f"Bearer {self.teacher_token}"},
            )

            assert confirm_response.status_code == 200
            confirmed_data = confirm_response.json()
            assert confirmed_data["status"] == "confirmed"
            assert confirmed_data["confirmed_by"] == self.teacher.user_uuid
            assert confirmed_data["confirmed_at"] is not None

        # Step 4: Verify no longer in pending list
        pending_response2 = client.get(
            f"/attendance/pending/{self.test_class.id}/{today}"
        )

        assert pending_response2.status_code == 200
        pending_list2 = pending_response2.json()
        assert not any(p["user_uuid"] == self.student.user_uuid for p in pending_list2)

    def test_bulk_confirm_workflow(self):
        """Test bulk confirmation of multiple students."""
        if not self.test_class:
            pytest.skip("No test class available")

        if not self.teacher_token:
            pytest.skip("No teacher token available")

        today = date.today()
        db = next(get_db())

        try:
            # Create multiple test check-ins
            attendance_ids = []
            for i in range(3):
                response = client.post(
                    "/attendance/check-in",
                    json={
                        "user_uuid": f"test-student-bulk-{i}",
                        "class_id": self.test_class.id,
                        "attendance_date": str(today),
                    },
                )
                if response.status_code == 200:
                    attendance_ids.append(response.json()["id"])

            if len(attendance_ids) < 2:
                pytest.skip("Could not create enough test records")

            # Bulk confirm
            bulk_response = client.post(
                "/attendance/bulk-confirm",
                json={"attendance_ids": attendance_ids},
                headers={"Authorization": f"Bearer {self.teacher_token}"},
            )

            assert bulk_response.status_code == 200
            confirmed_records = bulk_response.json()
            assert len(confirmed_records) == len(attendance_ids)

            for record in confirmed_records:
                assert record["status"] == "confirmed"
                assert record["confirmed_by"] == self.teacher.user_uuid

        finally:
            # Clean up
            db.query(models.FactAttendance).filter(
                models.FactAttendance.user_uuid.like("test-student-bulk-%")
            ).delete(synchronize_session=False)
            db.commit()
            db.close()

    def test_teacher_direct_add_student(self):
        """Test teacher adding student directly (bypasses self check-in)."""
        if not self.test_class:
            pytest.skip("No test class available")

        if not self.teacher_token:
            pytest.skip("No teacher token available")

        today = date.today()

        # Teacher adds student directly
        direct_response = client.post(
            "/attendance/direct",
            json={
                "user_uuid": self.student.user_uuid,
                "class_id": self.test_class.id,
                "attendance_date": str(today),
            },
            headers={"Authorization": f"Bearer {self.teacher_token}"},
        )

        assert direct_response.status_code == 200
        attendance_data = direct_response.json()
        assert (
            attendance_data["status"] == "confirmed"
        )  # Direct add is confirmed immediately
        assert attendance_data["confirmed_by"] == self.teacher.user_uuid

    def test_student_cancel_own_check_in(self):
        """Test student cancelling their own pending check-in."""
        if not self.test_class:
            pytest.skip("No test class available")

        today = date.today()

        # Student checks in
        check_in_response = client.post(
            "/attendance/check-in",
            json={
                "user_uuid": self.student.user_uuid,
                "class_id": self.test_class.id,
                "attendance_date": str(today),
            },
        )

        assert check_in_response.status_code == 200
        attendance_id = check_in_response.json()["id"]

        # Student cancels their check-in
        cancel_response = client.delete(
            f"/attendance/{attendance_id}/cancel",
            params={"user_uuid": self.student.user_uuid},
        )

        assert cancel_response.status_code == 200

        # Verify it's removed
        db = next(get_db())
        try:
            record = (
                db.query(models.FactAttendance)
                .filter(models.FactAttendance.id == attendance_id)
                .first()
            )
            assert record is None
        finally:
            db.close()

    def test_expire_old_pending_records(self):
        """Test auto-expiry of old pending check-ins."""
        db = next(get_db())

        try:
            # Create an old pending record (7 hours ago)
            old_time = datetime.now(timezone.utc) - timedelta(hours=7)

            old_record = models.FactAttendance(
                user_uuid=self.student.user_uuid,
                class_id=1,
                attendance_date=date.today(),
                status="pending",
                created_at=old_time,
            )
            db.add(old_record)
            db.commit()
            db.refresh(old_record)
            old_id = old_record.id

            # Call expire-old endpoint
            expire_response = client.post("/attendance/expire-old")

            assert expire_response.status_code == 200
            data = expire_response.json()
            assert data["deleted_count"] >= 1

            # Verify old record is deleted
            deleted_record = (
                db.query(models.FactAttendance)
                .filter(models.FactAttendance.id == old_id)
                .first()
            )
            assert deleted_record is None

        finally:
            db.close()


class TestUserSearchIntegration:
    """Integration tests for user search functionality."""

    def test_search_users_by_name(self):
        """Test searching users by first or last name."""
        db = next(get_db())

        try:
            # Get first user
            user = db.query(models.User).filter(models.User.is_current == True).first()

            if not user:
                pytest.skip("No users in database")

            # Search by first name
            response = client.get(f"/users/search?query={user.first_name[:3]}")

            assert response.status_code == 200
            results = response.json()
            assert len(results) >= 1
            assert any(r["user_uuid"] == user.user_uuid for r in results)

            # Search by last name
            response2 = client.get(f"/users/search?query={user.last_name[:3]}")

            assert response2.status_code == 200
            results2 = response2.json()
            assert len(results2) >= 1

        finally:
            db.close()

    def test_search_users_case_insensitive(self):
        """Test that search is case insensitive."""
        db = next(get_db())

        try:
            user = db.query(models.User).filter(models.User.is_current == True).first()

            if not user:
                pytest.skip("No users in database")

            # Search with different cases
            response_lower = client.get(
                f"/users/search?query={user.first_name.lower()[:3]}"
            )
            response_upper = client.get(
                f"/users/search?query={user.first_name.upper()[:3]}"
            )

            assert response_lower.status_code == 200
            assert response_upper.status_code == 200

            # Both should return results
            assert len(response_lower.json()) >= 1
            assert len(response_upper.json()) >= 1

        finally:
            db.close()

    def test_search_min_length_validation(self):
        """Test that search requires minimum 2 characters."""
        response = client.get("/users/search?query=a")

        assert response.status_code == 400
        assert "at least 2 characters" in response.json()["detail"].lower()


class TestKioskPinIntegration:
    """Integration tests for kiosk PIN functionality."""

    def test_verify_default_pin(self):
        """Test verifying the default kiosk PIN."""
        response = client.post("/kiosk/verify-pin", json={"pin": "1234"})

        # Note: This may fail if PIN has been changed
        # The test is informational
        if response.status_code == 200:
            assert response.json()["valid"] == True
        elif response.status_code == 401:
            pytest.skip("Default PIN has been changed")

    def test_verify_invalid_pin(self):
        """Test verifying an invalid PIN."""
        response = client.post("/kiosk/verify-pin", json={"pin": "0000"})

        assert response.status_code == 401

    def test_update_pin_requires_current(self):
        """Test that updating PIN requires current PIN."""
        response = client.put(
            "/kiosk/update-pin", json={"current_pin": "wrong_pin", "new_pin": "5678"}
        )

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
