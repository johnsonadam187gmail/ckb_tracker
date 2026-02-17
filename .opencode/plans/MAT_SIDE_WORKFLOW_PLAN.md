# Mat-Side Tablet Workflow - Implementation Plan

**Created**: February 12, 2026  
**Status**: Ready for Implementation  
**Objective**: Transform CKB Tracker into a mat-side tablet system with student self-check-in and teacher confirmation workflow

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Database Schema Changes](#database-schema-changes)
3. [API Endpoints](#api-endpoints)
4. [Frontend Implementation](#frontend-implementation)
5. [File Structure](#file-structure)
6. [Implementation Checklist](#implementation-checklist)
7. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### User Flow

```
TABLET LANDING PAGE
       ↓
┌──────────────────┐    ┌──────────────────┐
│ Student Check-in │    │  Teacher Login   │
│   (PIN: 4-6)     │    │  (Email/Password)│
└────────┬─────────┘    └────────┬─────────┘
         ↓                       ↓
  ┌──────────────┐      ┌──────────────────┐
  │  Search for  │      │ Confirm Attendance│
  │    Self      │      │   Tab (Primary)   │
  │ (Name/Email) │      └────────┬─────────┘
  └──────┬───────┘               ↓
         ↓              ┌──────────────────┐
  ┌──────────────┐     │ • View Pending   │
  │ Check In     │     │ • Bulk Confirm   │
  │ (PENDING)    │     │ • Add Student    │
  └──────┬───────┘     │   (Override)     │
         ↓             └──────────────────┘
  ┌──────────────┐
  │ Wait for     │
  │ Teacher      │
  │ Confirmation │
  └──────────────┘
```

### Attendance States

```
Student Check-in → PENDING (6-hour expiry)
                          ↓
              ┌───────────┴───────────┐
              ↓                       ↓
       Teacher Confirms         Student Cancels
              ↓                       ↓
         CONFIRMED              DELETED
              ↓
    Committed to Records
```

---

## Database Schema Changes

### 1. Update FactAttendance Model

**File**: `app/models.py` (Lines 262-296)

```python
class FactAttendance(Base):
    __tablename__ = "attendance"
    
    # EXISTING FIELDS (keep all)
    id = Column(Integer, primary_key=True)
    user_uuid = Column(String, ForeignKey("users.user_uuid"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    class_instance_id = Column(Integer, ForeignKey("class_instances.id"), nullable=True)
    teacher_uuid = Column(String, ForeignKey("users.user_uuid"), nullable=True)  # Deprecated
    user_role_id = Column(Integer, ForeignKey("user_roles.id"), nullable=True)
    attendance_date = Column(Date, default=datetime.now(timezone.utc).date())
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    # NEW FIELDS - Add these
    status = Column(String(20), default="pending", nullable=False, index=True)
    confirmed_by = Column(String, ForeignKey("users.user_uuid"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # NEW RELATIONSHIP
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    
    # EXISTING CONSTRAINT (keep)
    __table_args__ = (
        UniqueConstraint("user_uuid", "class_id", "attendance_date", 
                        name="_user_class_date_uc"),
    )
```

### 2. Create KioskAuth Model

**File**: `app/models.py` (Add after existing models)

```python
class KioskAuth(Base):
    """Stores the kiosk PIN for student check-in mode"""
    __tablename__ = "kiosk_auth"
    
    id = Column(Integer, primary_key=True)
    pin_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=datetime.now(timezone.utc))
```

### 3. Database Migration Strategy

**For Existing Records**:
```sql
-- Set all existing attendance to 'confirmed' for backward compatibility
UPDATE attendance SET status = 'confirmed' WHERE status IS NULL OR status = '';

-- Create default kiosk PIN (hash of '1234' - change immediately!)
INSERT INTO kiosk_auth (pin_hash, created_at) 
VALUES ('$argon2id$v=19$m=65536,t=3,p=4$...', datetime('now'));
```

---

## API Endpoints

### 1. Attendance Routes (`app/routers/attendance.py`)

#### A. Student Self Check-in
```python
@router.post("/attendance/check-in", response_model=schemas.AttendanceResponse)
def student_self_check_in(
    user_uuid: str,
    class_id: int,
    attendance_date: date,
    db: Session = Depends(get_db)
):
    """
    Student self check-in. Creates PENDING attendance record.
    Expires after 6 hours if not confirmed.
    """
    # Implementation notes:
    # 1. Check for existing pending/confirmed for this user/class/date
    # 2. If confirmed, return error (already checked in)
    # 3. If pending, return existing record (idempotent)
    # 4. Create new ClassInstance if doesn't exist
    # 5. Get user's Student role for user_role_id
    # 6. Create PENDING FactAttendance record
    # 7. Return created record
    pass
```

#### B. Get Pending Check-ins
```python
@router.get("/attendance/pending/{class_id}/{class_date}", 
            response_model=List[schemas.PendingAttendanceResponse])
def get_pending_check_ins(
    class_id: int,
    class_date: date,
    db: Session = Depends(get_db)
):
    """
    Get all pending check-ins for a specific class and date.
    Used by teacher dashboard.
    """
    # Filter by status='pending', class_id, attendance_date
    # Join with User to get name, email, photo
    # Order by created_at (oldest first)
    pass
```

#### C. Confirm Attendance
```python
@router.post("/attendance/{attendance_id}/confirm", 
            response_model=schemas.AttendanceResponse)
def confirm_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_teacher)  # JWT required
):
    """
    Teacher confirms a pending attendance record.
    Changes status from 'pending' to 'confirmed'.
    """
    # 1. Verify attendance exists and is PENDING
    # 2. Update status to 'confirmed'
    # 3. Set confirmed_by = current_user.uuid
    # 4. Set confirmed_at = now()
    # 5. Commit and return updated record
    pass
```

#### D. Cancel Own Check-in
```python
@router.delete("/attendance/{attendance_id}/cancel")
def cancel_own_check_in(
    attendance_id: int,
    user_uuid: str,  # From request body - must match attendance.user_uuid
    db: Session = Depends(get_db)
):
    """
    Student cancels their own pending check-in.
    Only allowed if status is 'pending'.
    """
    # 1. Verify attendance exists and is PENDING
    # 2. Verify user_uuid matches attendance.user_uuid
    # 3. Delete the record
    # 4. Return success message
    pass
```

#### E. Teacher Override (Direct Add)
```python
@router.post("/attendance/direct", response_model=schemas.AttendanceResponse)
def create_direct_attendance(
    user_uuid: str,
    class_id: int,
    attendance_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_teacher)  # JWT required
):
    """
    Teacher adds student directly (bypasses self check-in).
    Creates CONFIRMED attendance immediately.
    """
    # 1. Check if attendance already exists
    # 2. Create ClassInstance if needed
    # 3. Get Student role
    # 4. Create CONFIRMED FactAttendance
    # 5. Set confirmed_by and confirmed_at immediately
    pass
```

#### F. Bulk Confirm
```python
@router.post("/attendance/bulk-confirm", 
            response_model=List[schemas.AttendanceResponse])
def bulk_confirm_attendance(
    attendance_ids: List[int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_teacher)
):
    """
    Confirm multiple attendance records at once.
    """
    # 1. Update all records where id IN attendance_ids
    # 2. Set status='confirmed', confirmed_by, confirmed_at
    # 3. Return updated records
    pass
```

#### G. Expire Old Pending Records (Background Job)
```python
@router.post("/attendance/expire-old")  # Internal/scheduled use
def expire_old_pending_records(db: Session = Depends(get_db)):
    """
    Delete pending check-ins older than 6 hours.
    Call this via cron job every hour.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=6)
    db.query(FactAttendance).filter(
        FactAttendance.status == "pending",
        FactAttendance.created_at < cutoff_time
    ).delete()
    db.commit()
```

### 2. User Search Route (`app/routers/users.py`)

```python
@router.get("/users/search", response_model=List[schemas.UserSearchResponse])
def search_users(
    query: str,
    db: Session = Depends(get_db)
):
    """
    Search users by first name, last name, or email.
    Returns minimal info for disambiguation.
    Minimum 2 characters required.
    """
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    # Search in first_name, last_name, or email
    # Case-insensitive LIKE query
    # Filter is_current=True only
    # Return: user_uuid, first_name, last_name, email, profile_image_url
    pass
```

### 3. Kiosk Routes (`app/routers/kiosk.py` - NEW FILE)

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import models, database
from app.auth import verify_password, get_password_hash

router = APIRouter(prefix="/kiosk", tags=["kiosk"])

@router.post("/verify-pin")
def verify_kiosk_pin(pin: str, db: Session = Depends(database.get_db)):
    """Verify the kiosk PIN for student check-in mode"""
    kiosk_auth = db.query(models.KioskAuth).first()
    if not kiosk_auth:
        raise HTTPException(status_code=500, detail="Kiosk PIN not configured")
    
    if not verify_password(pin, kiosk_auth.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    
    return {"message": "PIN verified", "valid": True}

@router.put("/update-pin")
def update_kiosk_pin(
    current_pin: str,
    new_pin: str,
    db: Session = Depends(database.get_db),
    current_user: dict = Depends(get_current_admin)  # Admin only
):
    """Update the kiosk PIN (admin only)"""
    # Validate new_pin is 4-6 digits
    # Verify current_pin matches
    # Hash new_pin with Argon2
    # Update database
    pass
```

---

## Frontend Implementation

### 1. Create Landing Page (`pages/1_Landing.py`)

**Purpose**: Entry point for tablet. Two clear paths: Student or Teacher.

```python
import streamlit as st
import requests
import time
from datetime import datetime

st.set_page_config(
    page_title="CKB Tracker - Welcome",
    page_icon="🏋️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Clear any existing session states
for key in ['kiosk_mode', 'kiosk_expires', 'teacher_token', 'teacher_info']:
    if key in st.session_state:
        del st.session_state[key]

# Large header
st.title("🏋️ CKB Tracker")
st.markdown("<h3 style='text-align: center;'>Mat-Side Check-In</h3>", unsafe_allow_html=True)
st.markdown("---")

# Two large buttons side by side
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.subheader("🧑‍🎓 Students")
    st.write("Check in for class")
    
    # PIN entry
    pin = st.text_input(
        "Enter Gym PIN",
        type="password",
        max_chars=6,
        label_visibility="collapsed",
        placeholder="Enter 4-6 digit PIN"
    )
    
    if st.button("Enter", type="primary", use_container_width=True):
        if len(pin) < 4:
            st.error("PIN must be at least 4 digits")
        elif not pin.isdigit():
            st.error("PIN must be numbers only")
        else:
            # Verify PIN via API
            try:
                response = requests.post(
                    f"{BASE_URL}/kiosk/verify-pin",
                    json={"pin": pin},
                    timeout=5
                )
                if response.status_code == 200:
                    st.session_state.kiosk_mode = True
                    st.session_state.kiosk_expires = time.time() + 300  # 5 minutes
                    st.switch_page("Attendance.py")
                else:
                    st.error("Invalid PIN")
            except Exception as e:
                st.error("Error connecting to server")
    
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.subheader("👨‍🏫 Teachers")
    st.write("Manage class attendance")
    
    if st.button("Teacher Sign In", type="secondary", use_container_width=True):
        st.switch_page("pages/4_Teacher.py")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("CKB Martial Arts Tracker © 2026")
```

### 2. Modify Attendance.py for Kiosk Mode

**Key Changes**:
- Detect kiosk mode from session state
- Hide all member lists when in kiosk mode
- Show search-based user lookup only
- Add timeout warning
- Allow cancellation of own pending check-in

**Structure**:
```python
import streamlit as st
import requests
import time
from datetime import date, datetime

st.set_page_config(page_title="Daily Attendance", layout="wide")

BASE_URL = "http://127.0.0.1:8000"

# Check if in kiosk mode
if st.session_state.get("kiosk_mode"):
    # ===== KIOSK/STUDENT MODE =====
    render_kiosk_mode()
else:
    # ===== ADMIN MODE (existing functionality) =====
    render_admin_mode()

def render_kiosk_mode():
    """Student self check-in interface"""
    
    # Header with timeout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📝 Student Check-In")
    with col2:
        time_remaining = int(st.session_state.kiosk_expires - time.time())
        if time_remaining < 60:
            st.error(f"⏰ Expires in {time_remaining}s")
        else:
            st.info(f"⏰ {time_remaining//60}m remaining")
        
        if time_remaining <= 0:
            st.session_state.pop("kiosk_mode", None)
            st.switch_page("pages/1_Landing.py")
    
    st.markdown("---")
    
    # Class & Date Selection
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Date", value=date.today())
    with col2:
        try:
            classes_response = requests.get(f"{BASE_URL}/classes/", timeout=5)
            classes = classes_response.json()
            selected_class = st.selectbox(
                "Select Class",
                classes,
                format_func=lambda x: x["class_name"]
            )
        except:
            st.error("Error loading classes")
            return
    
    # Check for existing check-in
    if "current_student" not in st.session_state:
        check_existing_check_in(selected_class, selected_date)
    
    # Show search interface or confirmation
    if "current_student" in st.session_state:
        show_check_in_confirmation(selected_class, selected_date)
    else:
        show_user_search(selected_class, selected_date)
    
    # Exit button
    st.markdown("---")
    if st.button("⬅️ Exit Student Mode", type="secondary"):
        st.session_state.pop("kiosk_mode", None)
        st.session_state.pop("current_student", None)
        st.switch_page("pages/1_Landing.py")

def check_existing_check_in(selected_class, selected_date):
    """Check if student already has pending/confirmed check-in"""
    # Search by user_uuid if we have it stored
    pass

def show_user_search(selected_class, selected_date):
    """Search interface for finding self"""
    st.subheader("Find Yourself")
    st.write("Search by your first or last name")
    
    search_query = st.text_input(
        "Search",
        placeholder="Type at least 2 letters...",
        label_visibility="collapsed"
    )
    
    if search_query and len(search_query) >= 2:
        try:
            response = requests.get(
                f"{BASE_URL}/users/search",
                params={"query": search_query},
                timeout=5
            )
            
            if response.status_code == 200:
                users = response.json()
                
                if users:
                    st.write(f"Found {len(users)} match(es):")
                    
                    for user in users:
                        col1, col2, col3 = st.columns([1, 3, 1])
                        
                        with col1:
                            if user.get("profile_image_url"):
                                st.image(user["profile_image_url"], width=60)
                            else:
                                st.write("👤")
                        
                        with col2:
                            st.write(f"**{user['first_name']} {user['last_name']}**")
                            st.write(f"📧 {user['email']}")
                        
                        with col3:
                            if st.button("Select", key=f"select_{user['user_uuid']}", type="primary"):
                                st.session_state.selected_user = user
                                st.rerun()
                else:
                    st.info("No matches found. Try a different search.")
                    
        except Exception as e:
            st.error("Error searching users")
    
    # Show selected user
    if "selected_user" in st.session_state:
        user = st.session_state.selected_user
        st.success(f"Selected: {user['first_name']} {user['last_name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Check In Now", type="primary", use_container_width=True):
                create_pending_check_in(user, selected_class, selected_date)
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.pop("selected_user", None)
                st.rerun()

def create_pending_check_in(user, selected_class, selected_date):
    """Create PENDING attendance record"""
    try:
        response = requests.post(
            f"{BASE_URL}/attendance/check-in",
            json={
                "user_uuid": user["user_uuid"],
                "class_id": selected_class["id"],
                "attendance_date": str(selected_date)
            },
            timeout=5
        )
        
        if response.status_code == 200:
            st.session_state.current_student = user
            st.session_state.check_in_status = "pending"
            st.rerun()
        elif response.status_code == 400:
            data = response.json()
            if "already" in data.get("detail", "").lower():
                st.warning("You already checked in for this class!")
        else:
            st.error("Error checking in. Please try again.")
            
    except Exception as e:
        st.error("Error connecting to server")

def show_check_in_confirmation(selected_class, selected_date):
    """Show check-in status and allow cancellation"""
    user = st.session_state.current_student
    
    st.success(f"✅ Welcome, {user['first_name']}!")
    
    # Check current status from server
    try:
        response = requests.get(
            f"{BASE_URL}/attendance/user/{user['user_uuid']}",
            params={
                "class_id": selected_class["id"],
                "date": str(selected_date)
            },
            timeout=5
        )
        
        if response.status_code == 200:
            attendance = response.json()
            
            if attendance.get("status") == "pending":
                st.info("⏳ You're checked in! Waiting for teacher confirmation...")
                st.write("Your attendance will be confirmed when the class starts.")
                
                # Allow cancellation
                if st.button("🗑️ Cancel My Check-in", type="secondary"):
                    cancel_check_in(attendance["id"], user["user_uuid"])
                    
            elif attendance.get("status") == "confirmed":
                st.success("🎉 You're confirmed for today's class!")
                st.write("See you on the mat!")
                
                if st.button("Done", type="primary"):
                    st.session_state.pop("current_student", None)
                    st.rerun()
                    
    except Exception as e:
        st.error("Error checking status")

def cancel_check_in(attendance_id, user_uuid):
    """Cancel own pending check-in"""
    try:
        response = requests.delete(
            f"{BASE_URL}/attendance/{attendance_id}/cancel",
            params={"user_uuid": user_uuid},
            timeout=5
        )
        
        if response.status_code == 200:
            st.success("Check-in cancelled")
            time.sleep(1)
            st.session_state.pop("current_student", None)
            st.rerun()
        else:
            st.error("Error cancelling check-in")
            
    except Exception as e:
        st.error("Error connecting to server")

def render_admin_mode():
    """Existing admin functionality"""
    # Keep existing sidebar with member creation
    # But modify to hide member list in main area
    # Or show search-based interface similar to kiosk mode
    pass
```

### 3. Modify Teacher.py - Add Confirmation Tab

**New Tab 1: "✅ Confirm Attendance"** (Primary tab, first position)

```python
# In Teacher Dashboard
tab1, tab2, tab3 = st.tabs(["✅ Confirm Attendance", "📋 Class Roster", "💬 Feedback"])

with tab1:
    st.header("Confirm Student Attendance")
    
    # Class & Date Selection
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        confirm_date = st.date_input("Date", value=date.today(), key="confirm_date")
    with col2:
        try:
            classes = requests.get(f"{BASE_URL}/classes/").json()
            confirm_class = st.selectbox(
                "Class",
                classes,
                format_func=lambda x: x["class_name"],
                key="confirm_class"
            )
        except:
            st.error("Error loading classes")
            st.stop()
    with col3:
        st.write("")  # Spacer
        auto_refresh = st.checkbox("Auto-refresh", value=True)
    
    st.markdown("---")
    
    # Two-column layout: Pending list | Actions
    pending_col, action_col = st.columns([3, 1])
    
    with pending_col:
        st.subheader("⏳ Pending Check-ins")
        
        # Fetch pending check-ins
        try:
            response = requests.get(
                f"{BASE_URL}/attendance/pending/{confirm_class['id']}/{confirm_date}",
                timeout=5
            )
            
            if response.status_code == 200:
                pending = response.json()
                
                if pending:
                    st.write(f"**{len(pending)} students waiting**")
                    
                    # Select all checkbox
                    select_all = st.checkbox("Select All", key="select_all_pending")
                    
                    selected_ids = []
                    
                    for record in pending:
                        col1, col2, col3, col4 = st.columns([0.5, 2, 1.5, 1.5])
                        
                        with col1:
                            is_selected = st.checkbox(
                                "",
                                key=f"check_{record['id']}",
                                value=select_all
                            )
                            if is_selected:
                                selected_ids.append(record['id'])
                        
                        with col2:
                            if record.get("profile_image_url"):
                                st.image(record["profile_image_url"], width=40)
                            st.write(f"**{record['student_name']}**")
                        
                        with col3:
                            check_in_time = datetime.fromisoformat(record['created_at'])
                            st.write(f"🕐 {check_in_time.strftime('%H:%M')}")
                        
                        with col4:
                            # Individual actions
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✓", key=f"confirm_single_{record['id']}", 
                                           help="Confirm present"):
                                    confirm_single(record['id'])
                            with c2:
                                if st.button("✕", key=f"delete_single_{record['id']}",
                                           help="Remove check-in"):
                                    delete_single(record['id'])
                    
                    # Store selected for bulk actions
                    st.session_state.selected_pending = selected_ids
                    
                else:
                    st.info("No pending check-ins for this class and date.")
                    
        except Exception as e:
            st.error("Error loading pending check-ins")
    
    with action_col:
        st.subheader("Actions")
        
        # Bulk confirm
        selected = st.session_state.get("selected_pending", [])
        if selected:
            st.write(f"**{len(selected)} selected**")
            
            if st.button(
                f"✅ Confirm All ({len(selected)})",
                type="primary",
                use_container_width=True
            ):
                bulk_confirm(selected)
            
            if st.button(
                "🗑️ Remove All",
                type="secondary",
                use_container_width=True
            ):
                bulk_delete(selected)
        
        st.markdown("---")
        
        # Add student override
        with st.expander("➕ Add Student (Override)"):
            st.write("Add student directly:")
            
            # Fetch all users
            try:
                users_response = requests.get(f"{BASE_URL}/users/").json()
                users = [u for u in users_response if u.get("is_current")]
                
                selected_user = st.selectbox(
                    "Select Student",
                    users,
                    format_func=lambda x: f"{x['first_name']} {x['last_name']}"
                )
                
                if st.button("Add & Confirm", type="primary", use_container_width=True):
                    create_direct_attendance(selected_user, confirm_class, confirm_date)
                    
            except Exception as e:
                st.error("Error loading users")
    
    # Show confirmed attendance (collapsible)
    with st.expander("✅ View Confirmed Attendance"):
        try:
            response = requests.get(
                f"{BASE_URL}/attendance/class/{confirm_class['class_name']}",
                params={
                    "date": confirm_date,
                    "status": "confirmed"
                }
            )
            
            if response.status_code == 200:
                confirmed = response.json()
                if confirmed:
                    st.write(f"**{len(confirmed)} confirmed students**")
                    for record in confirmed:
                        st.write(f"✅ {record['student_name']}")
                else:
                    st.write("No confirmed attendance yet.")
                    
        except:
            st.error("Error loading confirmed attendance")

def confirm_single(attendance_id):
    """Confirm single attendance record"""
    try:
        response = requests.post(
            f"{BASE_URL}/attendance/{attendance_id}/confirm",
            headers={"Authorization": f"Bearer {st.session_state.teacher_token}"},
            timeout=5
        )
        if response.status_code == 200:
            st.success("Confirmed!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Error confirming")
    except:
        st.error("Connection error")

def bulk_confirm(attendance_ids):
    """Bulk confirm attendance records"""
    try:
        response = requests.post(
            f"{BASE_URL}/attendance/bulk-confirm",
            json={"attendance_ids": attendance_ids},
            headers={"Authorization": f"Bearer {st.session_state.teacher_token}"},
            timeout=5
        )
        if response.status_code == 200:
            st.success(f"Confirmed {len(attendance_ids)} students!")
            time.sleep(0.5)
            st.rerun()
    except:
        st.error("Error in bulk confirm")

def create_direct_attendance(user, class_obj, class_date):
    """Teacher override - add student directly"""
    try:
        response = requests.post(
            f"{BASE_URL}/attendance/direct",
            json={
                "user_uuid": user["user_uuid"],
                "class_id": class_obj["id"],
                "attendance_date": str(class_date)
            },
            headers={"Authorization": f"Bearer {st.session_state.teacher_token}"},
            timeout=5
        )
        if response.status_code == 200:
            st.success(f"Added {user['first_name']}!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Error adding student")
    except:
        st.error("Connection error")
```

### 4. Settings Page Updates (`pages/3_Settings.py`)

**Add Kiosk PIN Management Section**:

```python
# In Settings page, add new expander or tab

with st.expander("🔐 Kiosk PIN Management"):
    st.write("Manage the PIN students use to access the check-in kiosk.")
    st.write("PIN must be 4-6 digits.")
    
    # Verify admin is authenticated
    if not st.session_state.get("settings_authenticated"):
        st.warning("Please authenticate to manage PIN")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            current_pin = st.text_input(
                "Current PIN",
                type="password",
                max_chars=6
            )
        
        with col2:
            new_pin = st.text_input(
                "New PIN (4-6 digits)",
                type="password",
                max_chars=6
            )
            confirm_pin = st.text_input(
                "Confirm New PIN",
                type="password",
                max_chars=6
            )
        
        if st.button("Update PIN", type="primary"):
            if new_pin != confirm_pin:
                st.error("PINs do not match")
            elif len(new_pin) < 4 or len(new_pin) > 6:
                st.error("PIN must be 4-6 digits")
            elif not new_pin.isdigit():
                st.error("PIN must contain only numbers")
            else:
                # Call API to update
                try:
                    response = requests.put(
                        f"{BASE_URL}/kiosk/update-pin",
                        json={
                            "current_pin": current_pin,
                            "new_pin": new_pin
                        },
                        headers={"Authorization": f"Bearer {st.session_state.settings_token}"},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        st.success("PIN updated successfully!")
                    else:
                        st.error("Failed to update PIN. Check current PIN.")
                        
                except Exception as e:
                    st.error("Error updating PIN")
```

---

## File Structure

```
ckb_tracker/
├── pages/
│   ├── 1_Landing.py              # NEW - Entry point for tablet
│   ├── 2_Analytics.py            # Existing
│   ├── 3_Settings.py             # Modified - Add PIN management
│   └── 4_Teacher.py              # Modified - Add confirmation tab
├── app/
│   ├── models.py                 # Modified - Add status fields + KioskAuth
│   ├── schemas.py                # Modified - Add new response schemas
│   ├── routers/
│   │   ├── attendance.py         # Modified - New endpoints
│   │   ├── users.py              # Modified - Add search endpoint
│   │   ├── kiosk.py              # NEW - PIN management endpoints
│   │   └── ...
│   └── main.py                   # Modified - Include kiosk router
├── Attendance.py                 # Modified - Add kiosk mode UI
├── MAT_SIDE_WORKFLOW_PLAN.md     # This document
└── tests/
    ├── test_attendance_status.py # NEW - Status workflow tests
    ├── test_kiosk.py             # NEW - Kiosk PIN tests
    └── test_user_search.py       # NEW - Search endpoint tests
```

---

## Implementation Checklist

### Phase 1: Backend Foundation
- [ ] Update `app/models.py` - Add `status`, `confirmed_by`, `confirmed_at` to FactAttendance
- [ ] Create `KioskAuth` model in `app/models.py`
- [ ] Create database migration script
- [ ] Add new schemas to `app/schemas.py`
- [ ] Create `app/routers/kiosk.py` with PIN endpoints
- [ ] Add search endpoint to `app/routers/users.py`

### Phase 2: Attendance API
- [ ] Add `/attendance/check-in` endpoint (POST)
- [ ] Add `/attendance/pending/{class_id}/{date}` endpoint (GET)
- [ ] Add `/attendance/{id}/confirm` endpoint (POST)
- [ ] Add `/attendance/{id}/cancel` endpoint (DELETE)
- [ ] Add `/attendance/direct` endpoint (POST - teacher override)
- [ ] Add `/attendance/bulk-confirm` endpoint (POST)
- [ ] Add `/attendance/expire-old` endpoint (POST - for cron job)

### Phase 3: Frontend
- [ ] Create `pages/1_Landing.py`
- [ ] Modify `Attendance.py` - Add `render_kiosk_mode()` function
- [ ] Modify `Attendance.py` - Add user search interface
- [ ] Modify `Attendance.py` - Add self check-in flow
- [ ] Modify `Attendance.py` - Add cancellation button
- [ ] Modify `pages/4_Teacher.py` - Add confirmation tab
- [ ] Modify `pages/4_Teacher.py` - Add pending list view
- [ ] Modify `pages/4_Teacher.py` - Add bulk confirm UI
- [ ] Modify `pages/4_Teacher.py` - Add teacher override (add student)
- [ ] Modify `pages/3_Settings.py` - Add PIN management section

### Phase 4: Integration
- [ ] Include kiosk router in `app/main.py`
- [ ] Set up cron job for `expire-old` endpoint (every hour)
- [ ] Create default PIN in database (seed data)
- [ ] Test complete workflow end-to-end

### Phase 5: Testing
- [ ] Write tests for new attendance endpoints
- [ ] Write tests for user search
- [ ] Write tests for kiosk PIN verification
- [ ] Write integration tests for full workflow
- [ ] Test edge cases (duplicate check-ins, timeouts, etc.)

---

## Testing Strategy

### Unit Tests

**Test File**: `tests/test_attendance_status.py`

```python
def test_student_self_check_in_creates_pending():
    """Verify check-in creates PENDING record with correct fields"""

def test_duplicate_check_in_returns_existing():
    """Verify duplicate check-in returns existing record (idempotent)"""

def test_teacher_confirm_changes_status():
    """Verify confirmation updates status to CONFIRMED"""

def test_confirmed_by_tracks_teacher():
    """Verify confirmed_by and confirmed_at are set"""

def test_student_can_cancel_own_pending():
    """Verify student can delete their PENDING check-in"""

def test_student_cannot_cancel_others():
    """Verify student cannot cancel someone else's check-in"""

def test_teacher_override_creates_confirmed():
    """Verify teacher direct-add creates CONFIRMED record"""

def test_bulk_confirm_updates_multiple():
    """Verify bulk confirm updates all selected records"""

def test_pending_expires_after_six_hours():
    """Verify expire-old endpoint removes old pending records"""
```

**Test File**: `tests/test_kiosk.py`

```python
def test_kiosk_pin_verification_success():
    """Verify correct PIN returns success"""

def test_kiosk_pin_verification_failure():
    """Verify incorrect PIN returns 401"""

def test_kiosk_pin_update_requires_current():
    """Verify PIN update requires current PIN"""

def test_kiosk_pin_must_be_numeric():
    """Verify PIN validation rejects non-numeric"""

def test_kiosk_pin_length_validation():
    """Verify PIN must be 4-6 digits"""
```

**Test File**: `tests/test_user_search.py`

```python
def test_search_requires_min_two_chars():
    """Verify search rejects queries < 2 characters"""

def test_search_matches_first_name():
    """Verify search finds by first name"""

def test_search_matches_last_name():
    """Verify search finds by last name"""

def test_search_matches_email():
    """Verify search finds by email"""

def test_search_case_insensitive():
    """Verify search is case-insensitive"""

def test_search_returns_only_current_users():
    """Verify search excludes non-current (SCD) users"""
```

### Integration Tests

**Test File**: `tests/test_mat_side_workflow.py`

```python
def test_complete_student_teacher_flow():
    """
    Full workflow test:
    1. Student searches and finds self
    2. Student checks in (PENDING)
    3. Teacher sees pending list
    4. Teacher confirms attendance
    5. Record is CONFIRMED
    """

def test_teacher_override_flow():
    """
    Teacher override test:
    1. Teacher selects student from full list
    2. Teacher adds student directly
    3. Record is immediately CONFIRMED
    """

def test_student_cancellation_flow():
    """
    Cancellation test:
    1. Student checks in
    2. Student cancels check-in
    3. Record is deleted
    4. Teacher sees empty pending list
    """

def test_expiry_cleanup_flow():
    """
    Expiry test:
    1. Create pending check-in with old timestamp
    2. Call expire-old endpoint
    3. Verify record is removed
    """
```

---

## Cron Job Setup

**Schedule**: Every hour  
**Command**:
```bash
# Add to crontab (Linux/Mac)
0 * * * * curl -X POST http://127.0.0.1:8000/attendance/expire-old -H "Authorization: Bearer INTERNAL_TOKEN"

# Or use Python script
0 * * * * /path/to/venv/bin/python /path/to/cleanup_script.py
```

**cleanup_script.py**:
```python
import requests
response = requests.post("http://127.0.0.1:8000/attendance/expire-old")
print(f"Cleanup completed: {response.status_code}")
```

---

## Configuration

**Environment Variables** (add to `.env`):
```
# Existing variables
SECRET_KEY=<existing>
CLOUDINARY_CLOUD_NAME=<existing>

# New variables
KIOSK_PIN_HASH=$argon2id$v=19$m=65536,t=3,p=4$...
KIOSK_TIMEOUT_MINUTES=5
PENDING_EXPIRY_HOURS=6
```

**app/config.py**:
```python
KIOSK_MODE_TIMEOUT = 300  # 5 minutes in seconds
KIOSK_PIN_MIN_LENGTH = 4
KIOSK_PIN_MAX_LENGTH = 6
PENDING_CHECKIN_EXPIRY_HOURS = 6
```

---

## Security Considerations

1. **PIN Security**:
   - Argon2 hashing (same as passwords)
   - Rate limiting: Max 5 attempts per minute
   - No lockout, just delays

2. **Attendance Integrity**:
   - Once CONFIRMED, cannot be deleted (only marked absent - not implemented)
   - Audit trail: confirmed_by, confirmed_at
   - Students can only cancel their own PENDING records

3. **Session Management**:
   - Kiosk mode: 5-minute timeout
   - Teacher mode: Existing JWT with rolling expiry
   - Auto-clear sensitive data on timeout

4. **Data Privacy**:
   - Kiosk mode: Students see only search results (name + email)
   - No access to full member list
   - Search requires minimum 2 characters (prevents enumeration)

---

## Deployment Notes

1. **Database Migration**:
   - Backup database before migration
   - Run migration script to add new columns
   - Set default status='confirmed' for existing records
   - Create initial kiosk PIN (change immediately after!)

2. **Initial Setup**:
   - Set kiosk PIN in Settings page
   - Train staff on new workflow
   - Place tablet at mat-side location
   - Test complete workflow before go-live

3. **Post-Deployment**:
   - Monitor for errors
   - Check pending expiry is working
   - Collect feedback from students and teachers

---

## Future Enhancements (Out of Scope)

- QR code check-in
- Face recognition
- Push notifications when confirmed
- Real-time updates (WebSockets)
- Mobile app version
- Multiple kiosk PINs for different locations

---

## Support & Troubleshooting

**Common Issues**:

1. **PIN not working**: Check PIN is set in database
2. **Students can't find themselves**: Ensure user is_current=True
3. **Pending not expiring**: Check cron job is running
4. **Teacher can't confirm**: Verify teacher role and JWT token

**Debug Commands**:
```bash
# Check pending records
sqlite3 test.db "SELECT * FROM attendance WHERE status='pending';"

# Check kiosk PIN exists
sqlite3 test.db "SELECT * FROM kiosk_auth;"

# Reset kiosk PIN
sqlite3 test.db "UPDATE kiosk_auth SET pin_hash='NEW_HASH';"
```

---

**Plan Version**: 1.0  
**Last Updated**: February 12, 2026  
**Ready for Implementation**: ✅ Yes
