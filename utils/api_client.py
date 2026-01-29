"""
Centralized API client for Streamlit frontend.
Eliminates duplicate request handling across pages.
"""

import requests
from typing import Dict, Any, Optional, List
from datetime import date


class CKBAPIClient:
    """Client for interacting with CKB Tracker FastAPI backend."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict] = None,
    ) -> requests.Response:
        """Generic request handler with error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            if method.upper() == "GET":
                return requests.get(url, params=data)
            elif method.upper() == "POST":
                if files:
                    return requests.post(url, data=data, files=files)
                return requests.post(url, json=data)
            elif method.upper() == "PUT":
                return requests.put(url, json=data)
            elif method.upper() == "DELETE":
                return requests.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Cannot connect to API at {self.base_url}")

    # --- User Endpoints ---
    def get_users(self) -> List[Dict]:
        """Fetch all active users."""
        response = self._request("GET", "/users/")
        response.raise_for_status()
        return response.json()

    def create_user(self, user_data: Dict, profile_image: Optional[Any] = None) -> Dict:
        """Create a new user."""
        files = None
        if profile_image:
            files = {"file": profile_image}
        response = self._request("POST", "/users/", data=user_data, files=files)
        response.raise_for_status()
        return response.json()

    def update_user(self, user_uuid: str, user_data: Dict) -> Dict:
        """Update existing user (SCD Type 2)."""
        response = self._request("PUT", f"/users/{user_uuid}", data=user_data)
        response.raise_for_status()
        return response.json()

    # --- Class Endpoints ---
    def get_classes(self) -> List[Dict]:
        """Fetch all active classes."""
        response = self._request("GET", "/classes/")
        response.raise_for_status()
        return response.json()

    def create_class(self, class_data: Dict) -> Dict:
        """Create new class schedule."""
        response = self._request("POST", "/classes/", data=class_data)
        response.raise_for_status()
        return response.json()

    # --- Attendance Endpoints ---
    def record_attendance(
        self, user_uuid: str, class_id: int, attendance_date: date
    ) -> Dict:
        """Record attendance for a user."""
        data = {
            "user_uuid": user_uuid,
            "class_id": class_id,
            "attendance_date": str(attendance_date),
        }
        response = self._request("POST", "/attendance/", data=data)
        response.raise_for_status()
        return response.json()

    def get_attendance_by_user(self, user_uuid: str) -> List[Dict]:
        """Get all attendance records for a specific user."""
        response = self._request("GET", f"/attendance/user/{user_uuid}")
        response.raise_for_status()
        return response.json()

    # --- Gym Endpoints ---
    def get_gyms(self) -> List[Dict]:
        """Fetch all gym locations."""
        response = self._request("GET", "/gyms/")
        response.raise_for_status()
        return response.json()

    def create_gym(self, gym_data: Dict) -> Dict:
        """Create new gym location."""
        response = self._request("POST", "/gyms/", data=gym_data)
        response.raise_for_status()
        return response.json()

    # --- Class Type Endpoints ---
    def get_class_types(self) -> List[Dict]:
        """Fetch all class types."""
        response = self._request("GET", "/class-types/")
        response.raise_for_status()
        return response.json()

    def create_class_type(self, type_data: Dict) -> Dict:
        """Create new class type."""
        response = self._request("POST", "/class-types/", data=type_data)
        response.raise_for_status()
        return response.json()

    # --- Term Endpoints ---
    def get_terms(self) -> List[Dict]:
        """Fetch all terms."""
        response = self._request("GET", "/terms/")
        response.raise_for_status()
        return response.json()

    def create_term(self, term_data: Dict) -> Dict:
        """Create new term."""
        response = self._request("POST", "/terms/", data=term_data)
        response.raise_for_status()
        return response.json()

    # --- Term Target Endpoints ---
    def get_term_targets(self, term_id: Optional[int] = None) -> List[Dict]:
        """Fetch term targets, optionally filtered by term_id."""
        endpoint = f"/term-targets/term/{term_id}" if term_id else "/term-targets/"
        response = self._request("GET", endpoint)
        response.raise_for_status()
        return response.json()

    def set_term_target(self, target_data: Dict) -> Dict:
        """Create or update term target."""
        response = self._request("POST", "/term-targets/", data=target_data)
        response.raise_for_status()
        return response.json()
