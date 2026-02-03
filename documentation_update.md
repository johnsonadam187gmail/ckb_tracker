# Points Terminology Update (Formerly "weighting")

Throughout the codebase, we have standardized on using "points" instead of "weighting" for consistency and clarity. This change affects:

## Database Schema
- `ClassSchedule.points` (formerly `ClassSchedule.weighting`)

## API Schema
- `ClassBase.points` (formerly `ClassBase.weighting`)
- `ClassUpdate.points` (formerly `ClassUpdate.weighting`) 
- `UserAnalyticsResponse.points` (formerly `UserAnalyticsResponse.weighting`)
- `ClassAttendanceResponse.points` (formerly `ClassAttendanceResponse.weighting`)

## API Responses
- `/classes/` endpoint: Now returns `"points": 1.0` instead of `"weighting": 1.0`
- `/attendance/user/{user_uuid}`: Now returns `"points": 1.0` instead of `"weighting": 1.0`
- `/attendance/class/{class_name}`: Now returns `"points": 1.0` instead of `"weighting": 1.0`
- `/attendance/teacher/{teacher_uuid}/classes`: Now returns `"total_points": 10.0` instead of `"total_weighting": 10.0` 

## Frontend Pages
- Analytics page: "Total Mat Points" now calculated from "points" field
- Settings page: Class creation/editing form now uses "Points" field
- Teacher page: Student roster shows "Points" column
- Student Analytics: Fixed bug by using "points" consistently

## Migration
A database reset was performed to implement this change. The migration steps were:
1. Backup existing database
2. Update all code references
3. Reset database schema
4. Repopulate with sample data

## Benefits
- More intuitive terminology for students (they "earn points")
- Consistent naming across all components
- Fixed "KeyError: 'points_earned'" bug in Student Analytics page