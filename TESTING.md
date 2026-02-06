# 🧪 TESTING GUIDE - Teacher Authentication & Feedback Analytics

## Prerequisites

1. **Start Backend Server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   Verify at: http://127.0.0.1:8000/ (should return `{"message": "Attendance API is live!"}`)

2. **Start Streamlit Frontend:**
   ```bash
   streamlit run Attendance.py
   ```
   Access at: http://localhost:8501

3. **Test Credentials (from seed data):**
   - **Admin**: admin@ckb.com / admin123
   - **Teacher**: teacher@ckb.com / teacher123
   - **Student**: student@ckb.com / student123

---

## Test Checklist

### ✅ Phase 1: Backend API Endpoints

**1.1 Test Teacher Login:**
```bash
curl -X POST http://127.0.0.1:8000/auth/teacher-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=teacher@ckb.com&password=teacher123"
```
**Expected:** Returns JWT token + user info

**1.2 Test Session Verification:**
```bash
curl -X POST http://127.0.0.1:8000/auth/verify-session \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN_HERE"}'
```
**Expected:** Returns new extended token

**1.3 Test Admin Feedback Stats:**
```bash
curl http://127.0.0.1:8000/feedback/admin/comprehensive-stats
```
**Expected:** Returns array (empty if no feedback exists)

**1.4 Test Teacher Feedback:**
```bash
curl http://127.0.0.1:8000/feedback/teacher/TEACHER_UUID_HERE
```
**Expected:** Returns array (empty if teacher has no feedback)

---

### ✅ Phase 2: User Creation with Password

**Test Steps:**
1. Navigate to main Attendance page (http://localhost:8501)
2. In sidebar, fill out "Add New Member" form:
   - First Name: Test
   - Last Name: User
   - Email: testuser@ckb.com
   - Password: test123 (6 chars minimum)
   - Confirm Password: test123
   - Rank: White
3. Click "Create Member"

**Expected Results:**
- ✅ Success message appears
- ❌ Error if passwords don't match
- ❌ Error if password < 6 characters
- ❌ Error if required fields missing

**Verify in Database:**
```bash
sqlite3 test.db "SELECT first_name, last_name, email FROM users WHERE email='testuser@ckb.com';"
```

---

### ✅ Phase 3: Teacher Dashboard Authentication

**Test 3.1: Access Without Login**
1. Navigate to Teacher Dashboard page
2. Verify login form is displayed
3. Dashboard content should NOT be visible

**Test 3.2: Login with Invalid Credentials**
1. Enter: wrongemail@ckb.com / wrongpass
2. Click Login
3. Expected: Error message "Incorrect email or password"

**Test 3.3: Login with Student Account**
1. Enter: student@ckb.com / student123
2. Click Login
3. Expected: Error "You do not have permission to access this resource."

**Test 3.4: Login with Valid Teacher**
1. Enter: teacher@ckb.com / teacher123
2. Click Login
3. Expected:
   - ✅ Success message
   - ✅ Dashboard appears with 2 tabs
   - ✅ Sidebar shows "Logged in as: John Instructor"
   - ✅ Logout button appears

**Test 3.5: Session Management**
1. After login, refresh page
2. Expected: Should remain logged in (token verified)
3. Click Logout button
4. Expected: Returns to login form

---

### ✅ Phase 4: Teacher Dashboard - Class Roster Tab

**Prerequisites:** Logged in as teacher

**Test 4.1: Class Selection & Teacher Assignment**
1. Select today's date
2. Select a class from dropdown
3. Teacher dropdown should pre-select "John Instructor"
4. Click "💾 Assign Teacher" button
5. Expected:
   - ✅ Success message
   - ✅ Toast notification
   - ✅ Page refreshes

**Test 4.2: Student Roster Display**
1. Create some attendance records (via main Attendance page)
2. Return to Teacher Dashboard
3. Select same class and date
4. Expected: Student roster table shows checked-in students with:
   - Name
   - Rank
   - Check-in Time

---

### ✅ Phase 5: Teacher Dashboard - Feedback Tab

**Prerequisites:** 
- Logged in as teacher
- Some feedback exists for classes taught by this teacher

**Test 5.1: View Feedback**
1. Click "💬 Feedback" tab
2. Expected:
   - If no feedback: "📭 No feedback yet for classes you've taught"
   - If feedback exists: Table with Date | Class | Lesson | Rating | Comment

**Test 5.2: Verify Anonymity**
1. Check feedback table
2. Expected: Student names should NOT appear (anonymous for privacy)

**Test 5.3: Filters**
1. Click "🔍 Filters" expander
2. Test each filter:
   - Date range
   - Class multi-select
   - Rating dropdown (All/Positive/Negative)
3. Expected: Table updates based on filters

**Test 5.4: Metrics**
1. Verify metrics display:
   - Total Feedback (count)
   - 👍 Positive (count)
   - 👎 Negative (count)
2. Expected: Metrics match filtered data

---

### ✅ Phase 6: Admin Feedback Analytics

**Prerequisites:** Logged in as admin to Settings page

**Test 6.1: Access Feedback Analytics Tab**
1. Login to Settings: admin@ckb.com / admin123
2. Click "📊 Feedback Analytics" tab
3. Expected: Tab loads with full interface

**Test 6.2: Metrics Display**
1. Verify 4 metrics shown:
   - Total Feedback
   - 👍 Positive (percentage)
   - Most Active (student name)
   - Avg Rating (percentage)
2. Expected: All metrics calculate correctly

**Test 6.3: Data Table**
1. Check table columns: Date | Class | Student | Teacher | Rating | Comment
2. Expected: 
   - ✅ Full student names visible (NOT anonymous)
   - ✅ Teacher names visible
   - ✅ All data populated correctly

**Test 6.4: Filters**
1. Open "🔍 Filters" expander
2. Test all 4 filters:
   - Date Range (from/to date pickers)
   - Classes (multi-select)
   - Teachers (multi-select, includes "Unassigned")
   - Rating (All/Positive/Negative)
3. Apply various filter combinations
4. Expected: Table and charts update accordingly

**Test 6.5: Charts**
1. Verify 4 charts display:
   - **Chart 1:** Feedback Over Time (line chart)
   - **Chart 2:** Feedback by Class (bar chart)
   - **Chart 3:** Feedback by Teacher (bar chart)
   - **Chart 4:** Rating Distribution (pie chart)
2. Expected: All charts render with theme colors

**Test 6.6: CSV Export**
1. Click "📥 Download Feedback CSV" button
2. Expected: CSV file downloads with filename like `feedback_analytics_20260206_171530.csv`
3. Open CSV file
4. Expected: Contains filtered data with all columns

---

### ✅ Phase 7: End-to-End Workflow

**Complete User Journey:**

1. **Admin creates users:**
   - Create new member with password via Attendance.py
   - Assign Teacher role via Settings → User Admin

2. **Students check in:**
   - Via main Attendance page, check in multiple students to a class

3. **Teacher assigns themselves:**
   - Login to Teacher Dashboard
   - Assign themselves to the class

4. **Students submit feedback:**
   - (This requires Student Portal - if not yet implemented, seed feedback manually)

5. **Teacher views feedback:**
   - Teacher Dashboard → Feedback tab
   - Verify anonymous display

6. **Admin reviews analytics:**
   - Settings → Feedback Analytics tab
   - Verify full names visible
   - Test all filters and charts
   - Export CSV

---

## Known Limitations & Edge Cases

1. **Empty Database:**
   - All tabs should gracefully handle empty states with info messages

2. **No Teacher Assigned:**
   - Feedback Analytics should show "(Unassigned)" for teacher column
   - Filter should include "(Unassigned)" option

3. **Session Timeout:**
   - Teacher sessions expire after 5 minutes of inactivity
   - Next interaction will show "Session expired" and redirect to login

4. **Password Requirements:**
   - Minimum 6 characters (enforced at frontend and backend)
   - Both frontend and backend validate

---

## Troubleshooting

**Issue:** "Connection failed" errors
- **Fix:** Ensure backend server is running on port 8000

**Issue:** "No module named 'jose'" error
- **Fix:** Run `pip install python-jose[cryptography]`

**Issue:** Login fails with correct credentials
- **Fix:** Check database has users with passwords (run `seed_users.py`)

**Issue:** Charts not rendering
- **Fix:** Ensure plotly is installed: `pip install plotly`

**Issue:** Teacher can't login (403 Forbidden)
- **Fix:** Ensure user has Teacher role assigned in Settings → User Admin

---

## Success Criteria

✅ All backend endpoints return expected responses
✅ User creation requires passwords (frontend + backend)
✅ Teacher authentication works (login/logout)
✅ Teacher dashboard shows class roster and feedback
✅ Feedback privacy enforced (anonymous for teachers)
✅ Admin analytics shows all data with full names
✅ Filters and charts work correctly
✅ CSV export generates valid files
✅ Session management works (auto-logout after 5 min)

---

## Post-Testing Actions

After all tests pass:
1. Document any bugs found in GitHub issues
2. Update AGENTS.md with new feature documentation
3. Create comprehensive git commit
4. Merge feature branch to main

