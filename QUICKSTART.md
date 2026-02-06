# 🚀 QUICK START GUIDE

## You're All Set! The Database is Populated with Test Data

### ✅ What's Been Created

**Users:**
- 1 Admin (Settings page access)
- 1 Teacher (Teacher Dashboard access)
- 5 Students (can check in and view analytics)

**Classes:**
- 6 scheduled classes (Fundamentals 1 & 2, Advanced Gi, No-Gi Basics, Competition, Open Mat)
- 2 gym locations (Main Gym, North Location)
- 3 class types (Gi, No-Gi, Competition)

**Data:**
- 84 attendance records over the past 7 days
- 15 feedback entries (mix of positive and negative)
- 1 curriculum with 3 lessons
- 1 term with targets for all ranks

---

## 🎯 START THE APPLICATION

### Step 1: Start Backend Server
Open a terminal and run:
```bash
uvicorn app.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 2: Start Frontend (New Terminal)
Open a **second terminal** and run:
```bash
streamlit run Attendance.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

## 🔑 TEST CREDENTIALS

### Admin Account (Settings Page)
```
Email: admin@ckb.com
Password: admin123
```

**What you can test:**
- Navigate to Settings page (sidebar)
- Click "📊 Feedback Analytics" tab
- View comprehensive feedback with full student names
- Test filters (date range, classes, teachers, rating)
- View 4 charts (feedback over time, by class, by teacher, distribution)
- Export CSV file

### Teacher Account (Teacher Dashboard)
```
Email: teacher@ckb.com
Password: teacher123
```

**What you can test:**
- Navigate to Teacher Dashboard (sidebar)
- Login with teacher credentials
- **Tab 1 - Class Roster:**
  - Select a date (past 7 days have data)
  - Select a class
  - View student roster
  - Assign teacher to class
- **Tab 2 - Feedback:**
  - View feedback for classes you taught
  - Verify student names are ANONYMOUS
  - Test filters (date range, classes, rating)
  - Check metrics (total, positive, negative)

### Student Account (Main Page)
```
Email: student@ckb.com
Password: student123
```

**Additional students:**
- sarah.martinez@ckb.com / student123
- james.anderson@ckb.com / student123
- emma.wilson@ckb.com / student123
- david.thompson@ckb.com / student123

---

## 🧪 TESTING CHECKLIST

### ✅ Test 1: View Existing Data
1. Open http://localhost:8501
2. Main page should show:
   - All 7 members in the system
   - Classes dropdown with 6 classes
3. Select a date from past 7 days
4. Select a class
5. See students who checked in

### ✅ Test 2: Create New User with Password
1. In sidebar "Add New Member" form
2. Fill all fields including:
   - First Name: Test
   - Last Name: User
   - Email: testuser@ckb.com
   - **Password: test123** ← Required
   - **Confirm Password: test123** ← Must match
3. Click "Create Member"
4. Should see success message

### ✅ Test 3: Teacher Authentication
1. Click "Teacher Dashboard" in sidebar
2. Should see login form
3. Enter: teacher@ckb.com / teacher123
4. Click Login
5. Should see dashboard with 2 tabs
6. Test logout button

### ✅ Test 4: Teacher Feedback (Anonymous)
1. After logging in as teacher
2. Click "💬 Feedback" tab
3. Should see 15 feedback entries
4. **VERIFY:** No student names shown (anonymous)
5. Test filters (date, class, rating)
6. Check metrics display

### ✅ Test 5: Admin Feedback Analytics
1. Click "Settings" in sidebar
2. Login: admin@ckb.com / admin123
3. Click "📊 Feedback Analytics" tab
4. Should see:
   - 4 metrics at top
   - Filters section
   - Data table with **FULL student names**
   - 4 charts (line, bar, bar, pie)
5. Test filters:
   - Change date range
   - Select specific classes
   - Filter by teacher
   - Change rating filter
6. Click "📥 Download Feedback CSV"
7. Should download CSV file

### ✅ Test 6: Teacher Assignment
1. Login to Teacher Dashboard
2. Select today's date
3. Select "Fundamentals 1" class
4. Teacher dropdown should pre-select "John Instructor"
5. Click "💾 Assign Teacher"
6. Should see success message + toast
7. Page refreshes

---

## 📊 WHAT TO LOOK FOR

### Feedback Privacy
- **Teacher View:** Student names should be completely hidden (anonymous)
- **Admin View:** Full student names visible (e.g., "Mike Student", "Sarah Martinez")

### Charts
- Should render with your current theme (dark/light)
- All 4 charts should be interactive (hover to see details)
- Colors should match theme (red/green for ratings)

### Filters
- Should update table/charts dynamically
- Multiple filters can be combined
- Metrics should recalculate based on filters

### CSV Export
- Downloads with timestamp filename
- Contains all filtered data
- Opens correctly in Excel/Google Sheets

---

## 🐛 TROUBLESHOOTING

**Issue:** "Connection failed" errors
- **Fix:** Make sure backend server is running (uvicorn)

**Issue:** Login fails with correct credentials
- **Fix:** Check if user has Teacher role assigned
- Run: `python seed_complete_data.py` again

**Issue:** No feedback showing
- **Fix:** Database has 15 feedback entries for teacher@ckb.com
- Check if viewing correct date range

**Issue:** Charts not rendering
- **Fix:** May take a few seconds to load
- Check browser console for errors

---

## 📝 SAMPLE WORKFLOWS

### Workflow 1: Teacher Views Their Feedback
1. Login as teacher@ckb.com / teacher123
2. Click "Feedback" tab
3. See 15 feedback entries (anonymous)
4. Filter to "Positive" only
5. See ~12 positive feedback entries
6. Filter to specific class
7. View metrics update

### Workflow 2: Admin Analyzes Feedback
1. Login to Settings as admin@ckb.com / admin123
2. Go to "Feedback Analytics" tab
3. See all 15 entries with full names
4. Filter to last 3 days
5. See subset of feedback
6. View "Feedback Over Time" chart
7. Export filtered data to CSV

### Workflow 3: Check Attendance History
1. On main page
2. Select yesterday's date
3. Select "Fundamentals 1"
4. See 4 students checked in
5. View their ranks and check-in times

---

## ✨ NEXT STEPS

After testing:
1. Verify all features work as expected
2. Check TESTING.md for comprehensive test checklist
3. If everything works, merge branch to main:
   ```bash
   git checkout main
   git merge feature/teacher-auth-feedback-v2
   git push origin main
   ```

---

## 🎉 YOU'RE READY TO TEST!

All data is loaded. Both servers should be running. Open http://localhost:8501 and start testing!

**Quick Access:**
- Main Page: http://localhost:8501
- Teacher Dashboard: http://localhost:8501/Teacher (sidebar link)
- Settings: http://localhost:8501/Settings (sidebar link)
- API Docs: http://127.0.0.1:8000/docs

**Happy Testing! 🚀**
