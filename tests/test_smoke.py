"""
Basic smoke tests to ensure critical functionality works.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test that the root endpoint returns a response."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_get_users_endpoint():
    """Test that the users endpoint is accessible."""
    response = client.get("/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_classes_endpoint():
    """Test that the classes endpoint is accessible."""
    response = client.get("/classes/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_terms_endpoint():
    """Test that the terms endpoint is accessible."""
    response = client.get("/terms/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_gyms_endpoint():
    """Test that the gyms endpoint is accessible."""
    response = client.get("/gyms/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_class_types_endpoint():
    """Test that the class types endpoint is accessible."""
    response = client.get("/class-types/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_term_targets_endpoint():
    """Test that the term targets endpoint is accessible."""
    response = client.get("/term-targets/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_attendance_endpoint():
    """Test that the attendance endpoint is accessible."""
    response = client.get("/attendance/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
