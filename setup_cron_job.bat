@echo off
REM Windows Task Scheduler Setup Script for CKB Tracker Cron Job
REM Run this script as Administrator to set up automatic cleanup of old pending check-ins

echo ========================================
echo CKB Tracker - Cron Job Setup
echo ========================================
echo.
echo This will create a scheduled task to run every hour
echo to clean up old pending check-ins (older than 6 hours).
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Please right-click and select "Run as Administrator"
    pause
    exit /b 1
)

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%cron_expire_old_pending.py"

REM Verify the Python script exists
if not exist "%PYTHON_SCRIPT%" (
    echo ERROR: Could not find cron_expire_old_pending.py
    echo Expected location: %PYTHON_SCRIPT%
    pause
    exit /b 1
)

REM Find Python executable
where python >nul 2>&1
if %errorLevel% neq 0 (
    where python3 >nul 2>&1
    if %errorLevel% neq 0 (
        echo ERROR: Python not found in PATH
        echo Please ensure Python is installed and added to PATH
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python3"
    )
) else (
    set "PYTHON_CMD=python"
)

echo Found Python: %PYTHON_CMD%
echo Script location: %PYTHON_SCRIPT%
echo.

REM Create the scheduled task
schtasks /create /tn "CKB Tracker - Expire Old Pending Check-ins" /tr "'%PYTHON_CMD%' '%PYTHON_SCRIPT%'" /sc hourly /f

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Failed to create scheduled task
    echo You may need to run this script as Administrator
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Scheduled task created.
echo ========================================
echo.
echo Task Details:
echo   Name: CKB Tracker - Expire Old Pending Check-ins
echo   Schedule: Every hour
echo   Action: Run expire-old cleanup
echo   Log file: logs\cron_expire.log
echo.
echo The task will start running immediately.
echo.
echo To verify the task is running:
echo   1. Open Task Scheduler (taskschd.msc)
echo   2. Look for "CKB Tracker - Expire Old Pending Check-ins"
echo   3. Check the logs at: %SCRIPT_DIR%logs\cron_expire.log
echo.
echo To remove the task later, run:
echo   schtasks /delete /tn "CKB Tracker - Expire Old Pending Check-ins" /f
echo.
pause
