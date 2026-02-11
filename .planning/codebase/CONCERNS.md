# Codebase Concerns

**Analysis Date:** 2026-02-11

## Tech Debt

**Hardcoded Admin Credentials:**
- Issue: Admin password hardcoded directly in Settings page (`pages/3_Settings.py` lines 86-87)
- Files: `pages/3_Settings.py`
- Impact: Security vulnerability - credentials "admin"/"ckb2026" exposed in source code
- Fix approach: Move to environment variables or implement proper authentication via backend API with JWT tokens (similar to Teacher dashboard pattern)

**Deprecated Teacher Field in FactAttendance:**
- Issue: `FactAttendance.teacher_uuid` field marked as deprecated but still present in model and queries
- Files: `app/models.py` (line 275-277), `app/routers/attendance.py` (lines 116-119, 164-167)
- Impact: Data duplication and confusion about which field is authoritative source for teacher assignment
- Fix approach: Remove deprecated field after confirming all queries use `class_instance.teacher_uuid`, run migration to drop column

**Double Image Upload Pattern:**
- Issue: User creation requires uploading photo twice - once with temp UUID, then re-upload with actual UUID
- Files: `app/routers/users.py` (lines 127-149)
- Impact: Wastes Cloudinary bandwidth and API calls, increases creation latency
- Fix approach: Generate user_uuid before database commit or use transaction rollback pattern if photo upload fails

**Password Validation Complexity Mismatch:**
- Issue: Settings page has strict validation (8+ chars, uppercase, lowercase, digit, special char), but backend only enforces minimum length
- Files: `pages/3_Settings.py` (lines 9-36), `app/routers/auth.py` (no equivalent validation)
- Impact: Backend accepts weak passwords if API called directly, bypassing frontend validation
- Fix approach: Implement Pydantic validator in `schemas.SetPasswordRequest` to enforce consistent rules

**Duplicate Dependencies in pyproject.toml:**
- Issue: `passlib[bcrypt]` and `psycopg2-binary` listed twice in dependencies
- Files: `pyproject.toml` (lines 14, 22-23)
- Impact: Potential version conflicts if different versions specified, confusing for developers
- Fix approach: Remove duplicate entries, consolidate to single declaration

**Manual Secret Key Generation:**
- Issue: Secret key auto-generated and appended to `.env` file at runtime if missing
- Files: `app/auth.py` (lines 15-22)
- Impact: File I/O during auth initialization, potential race condition with multiple workers
- Fix approach: Require SECRET_KEY in environment, fail fast if not set, document in setup instructions

**No Database Migrations:**
- Issue: Schema changes require manual `reset_db.py` execution, losing all data
- Files: `reset_db.py`, no migration framework detected
- Impact: Cannot evolve production schema without data loss
- Fix approach: Integrate Alembic for SQLAlchemy migrations, create initial migration from current schema

## Known Bugs

**Teacher Analytics Endpoint Field Name Error:**
- Symptoms: API endpoint returns field named `total_weighting` but code uses `total_points` in aggregation
- Files: `app/routers/attendance.py` (line 194 sums `points` but line 234 references `total_weighting`)
- Trigger: Accessing `/attendance/teacher/{uuid}/classes` endpoint
- Workaround: Frontend likely fails to display points correctly for teacher analytics

**SCD Type 2 Query Inconsistency:**
- Symptoms: Only 17 out of many queries filter by `is_current == True` for User and ClassSchedule tables
- Files: Multiple routers - `app/routers/users.py`, `app/routers/attendance.py`, `app/routers/classes.py`
- Trigger: Fetching historical records when only current should be returned
- Workaround: May return duplicate or historical user/class records in some endpoints

**Nullable Password Hash with Required Password:**
- Symptoms: User model has `password_hash` as nullable, but user creation now requires password
- Files: `app/models.py` (line 34), `app/routers/users.py` (line 28)
- Trigger: Database allows null passwords but API rejects them, inconsistent constraint
- Workaround: Update model to `nullable=False` and run migration for existing users

**Missing Error Rollback in Some Routes:**
- Symptoms: Some endpoints catch exceptions but don't explicitly rollback transactions
- Files: `app/routers/users.py` (lines 81, 85, 95, 145, 219, 223, 239, 306, 310, 377)
- Trigger: Exception during database operation may leave transaction open
- Workaround: Add explicit `db.rollback()` in all exception handlers before raising HTTPException

## Security Considerations

**Hardcoded Admin Credentials:**
- Risk: Anyone with source access knows admin password for Settings page
- Files: `pages/3_Settings.py` (lines 86-88)
- Current mitigation: None - plain text comparison in client code
- Recommendations: Implement proper backend authentication endpoint, use environment variables, add rate limiting

**Missing JWT Token Validation:**
- Risk: Teacher token has 5-minute expiry but no signature verification in some paths
- Files: `app/auth.py` (lines 60-72)
- Current mitigation: JWT decode with secret key verification
- Recommendations: Add token blacklist for logout, implement refresh token pattern for longer sessions

**No HTTPS Enforcement:**
- Risk: BASE_URL uses http:// in all frontend pages, credentials sent in plain text
- Files: `Attendance.py` (line 8), `pages/3_Settings.py` (line 119), `pages/4_Teacher.py` (line 8)
- Current mitigation: None - development server only
- Recommendations: Enforce HTTPS in production, add CORS configuration, set secure cookie flags

**Cloudinary Credentials in Environment:**
- Risk: API keys stored in `.env` file without encryption
- Files: `app/config.py` (lines 35-38), `.env` (not committed but exists)
- Current mitigation: `.env` in `.gitignore`
- Recommendations: Use secrets manager in production (AWS Secrets Manager, Azure Key Vault), rotate keys regularly

**No Rate Limiting:**
- Risk: Authentication endpoints vulnerable to brute force attacks
- Files: `app/routers/auth.py` (endpoints lack rate limiting)
- Current mitigation: None detected
- Recommendations: Add FastAPI rate limiting middleware (slowapi), implement account lockout after failed attempts

**SQL Injection Risk (Low):**
- Risk: All queries use SQLAlchemy ORM which parameterizes queries
- Files: All routers use ORM, no raw SQL detected
- Current mitigation: SQLAlchemy ORM prevents SQL injection by default
- Recommendations: Maintain ORM usage, avoid `text()` queries with string concatenation

**Password Reset No Email Verification:**
- Risk: `/auth/set-password` endpoint allows password changes without verifying user identity
- Files: `app/routers/auth.py` (lines 118-143)
- Current mitigation: None - endpoint is open
- Recommendations: Add authentication requirement or email verification token system

## Performance Bottlenecks

**N+1 Query Problem in User Analytics:**
- Problem: Fetching attendance records without joinedload causes N+1 queries for user/class/teacher
- Files: `app/routers/attendance.py` (lines 94-103 uses joinedload, but many endpoints don't)
- Cause: Some endpoints query FactAttendance without eager loading relationships
- Improvement path: Add `joinedload()` to all attendance queries for user, class_info, teacher relationships

**Large Settings Page (85KB, 2000+ lines):**
- Problem: Settings page contains all admin functions in one monolithic file
- Files: `pages/3_Settings.py` (2000+ lines based on reading limit)
- Cause: Multiple tabs (User Admin, Classes, Gyms, Terms, Targets, Lessons, Passwords, Feedback) in single file
- Improvement path: Split into separate page modules or use Streamlit components architecture

**Cloudinary Image Processing on Every Upload:**
- Problem: Images processed locally (resize, crop, compress) before upload to Cloudinary which also processes them
- Files: `app/services/cloudinary_service.py` (lines 41-113 process image, lines 177-196 Cloudinary transformations)
- Cause: Double processing - local PIL + Cloudinary transformations
- Improvement path: Remove local processing, let Cloudinary handle all transformations server-side

**No Database Indexes on Foreign Keys:**
- Problem: Foreign key columns may lack indexes for join performance
- Files: `app/models.py` (ForeignKey columns, some have `index=True` but not all)
- Cause: Manual index specification required, not automatic in SQLAlchemy
- Improvement path: Audit all foreign keys, add `index=True` to high-traffic join columns (user_uuid, class_id, attendance_date)

**Streamlit Session State Without Caching:**
- Problem: API calls repeated on every page interaction due to `st.rerun()`
- Files: `pages/3_Settings.py` (line 136 calls st.rerun after every action)
- Cause: Streamlit reruns entire script on state change
- Improvement path: Use `@st.cache_data` decorator for API responses, implement TTL caching

## Fragile Areas

**SCD Type 2 Update Logic:**
- Files: `app/routers/users.py` (lines 190-245), `app/routers/classes.py` (similar pattern)
- Why fragile: Complex multi-step process (expire old record, create new version, preserve created_date)
- Safe modification: Always use transaction boundaries, test with existing data, verify `is_current` filters in queries
- Test coverage: `tests/test_scd_constraint_fix.py` covers basic cases but not all edge cases

**ClassInstance Auto-Creation:**
- Files: `app/routers/attendance.py` (lines 36-53)
- Why fragile: ClassInstance created on first student check-in if not exists, potential race condition
- Safe modification: Use upsert pattern with database-level locking or unique constraint handling
- Test coverage: `tests/test_class_instances.py` exists but likely doesn't test concurrent access

**Teacher Role Validation:**
- Files: `app/routers/attendance.py` (lines 291-306), `app/routers/auth.py` (lines 88-116)
- Why fragile: Multiple role checks in different endpoints, inconsistent error messages
- Safe modification: Create reusable dependency injection function for role verification
- Test coverage: `tests/test_role_system.py` and `tests/test_teacher_assignment.py` cover some cases

**Photo Upload Error Handling:**
- Files: `app/routers/users.py` (lines 53-88, 127-149), `app/services/cloudinary_service.py`
- Why fragile: Complex error path with temporary UUID, cleanup on failure, re-upload logic
- Safe modification: Wrap entire upload in try/finally to ensure cleanup, use transaction rollback
- Test coverage: No dedicated photo upload tests detected

**Feedback 7-Day Window:**
- Files: `app/routers/feedback.py` (likely contains time-based validation based on schema)
- Why fragile: Time-based logic depends on accurate timestamps, timezone handling
- Safe modification: Ensure all datetime comparisons use UTC, test across timezone boundaries
- Test coverage: No feedback-specific tests detected in test directory

## Scaling Limits

**SQLite Database:**
- Current capacity: Single-file database, no connection pooling, write lock contention
- Limit: ~100 concurrent users, 10-20 writes/second before lock timeouts
- Scaling path: Migrate to PostgreSQL (already in dependencies), enable connection pooling, add read replicas

**Local File Storage Fallback:**
- Current capacity: `static/profile_pics/` directory for local photo storage
- Limit: Filesystem I/O bottleneck, no CDN, single server storage
- Scaling path: Fully migrate to Cloudinary, remove local storage, configure CDN for assets

**Synchronous API Endpoints:**
- Current capacity: Uvicorn handles ~1000 req/sec on single core
- Limit: Blocking I/O operations (database, Cloudinary) limit throughput
- Scaling path: Use async SQLAlchemy, async Cloudinary client, horizontal scaling with load balancer

**Single Streamlit Process:**
- Current capacity: One Streamlit frontend instance
- Limit: Cannot horizontally scale frontend, session state per-process
- Scaling path: Use Streamlit Cloud or container orchestration, implement shared session backend (Redis)

**No Background Job Queue:**
- Current capacity: All operations synchronous in request/response cycle
- Limit: Photo processing, analytics aggregation block user requests
- Scaling path: Implement Celery or RQ task queue, move heavy operations to background workers

## Dependencies at Risk

**passlib with Argon2:**
- Risk: Argon2 hashing slower than bcrypt (intentional security feature)
- Impact: User creation and login endpoints have 500ms+ latency under load
- Migration plan: Acceptable for current scale, monitor if login becomes bottleneck

**python-jose JWT:**
- Risk: python-jose library has fewer stars/maintainers than alternatives (PyJWT)
- Impact: Security updates may lag, potential deprecation
- Migration plan: Consider migrating to PyJWT, both use same HS256 algorithm

**SQLAlchemy 2.0:**
- Risk: Breaking changes from 1.4, some patterns deprecated
- Impact: Uses lambda defaults instead of functions in models (lines 82, 114, etc.)
- Migration plan: Already on 2.0, ensure all queries use new style (no legacy query API)

**Streamlit Version Lock:**
- Risk: Streamlit 1.52.2+ has different caching API than older versions
- Impact: Fast-moving project, APIs change frequently
- Migration plan: Pin major version, test thoroughly before upgrading

**Pydantic v2:**
- Risk: Breaking changes from v1, different validation API
- Impact: Already migrated (`field_validator` decorator in use), but some patterns may be v1 holdovers
- Migration plan: Already on v2, audit all validators for correct syntax

## Test Coverage Gaps

**Attendance Endpoints:**
- What's not tested: ClassInstance auto-creation race conditions, duplicate check-in edge cases
- Files: `app/routers/attendance.py`
- Risk: Integrity constraint violations under concurrent access
- Priority: High - core business logic

**User Photo Upload:**
- What's not tested: Cloudinary upload failures, image validation edge cases, re-upload logic
- Files: `app/routers/users.py` (lines 23-150), `app/services/cloudinary_service.py`
- Risk: User creation fails silently or leaves orphaned photos
- Priority: High - affects user experience

**SCD Type 2 Versioning:**
- What's not tested: Concurrent updates to same user, created_date preservation, query filtering consistency
- Files: `app/routers/users.py`, `app/routers/classes.py`
- Risk: Data corruption or duplicate current records
- Priority: High - data integrity issue

**Authentication Flow:**
- What's not tested: JWT expiry handling, token refresh, role verification, session extension
- Files: `app/auth.py`, `app/routers/auth.py`
- Risk: Security bypass or authentication failures
- Priority: High - security critical

**Curriculum and Lessons:**
- What's not tested: Cascade deletion behavior, lesson assignment conflicts
- Files: `app/routers/curricula.py`, `app/routers/lessons.py`, `app/routers/class_instances.py`
- Risk: Orphaned lessons or broken references after deletion
- Priority: Medium - covered by integration tests (`test_curriculum_integration.py`)

**Feedback System:**
- What's not tested: 7-day window validation, duplicate feedback prevention, anonymous vs. admin views
- Files: `app/routers/feedback.py`
- Risk: Business rule violations or privacy leaks
- Priority: Medium - newer feature, less critical path

**Settings Page Workflows:**
- What's not tested: Multi-step user updates, role assignment UI, password management UI
- Files: `pages/3_Settings.py` (85KB+ monolithic file)
- Risk: UI breaks without backend API test coverage catching it
- Priority: Medium - frontend-heavy, manual testing required

**Analytics Queries:**
- What's not tested: Term target calculations, teacher analytics aggregations, edge cases with no data
- Files: `pages/2_Analytics.py`, `pages/5_Student_Analytics.py`, `app/routers/attendance.py`
- Risk: Incorrect metrics displayed to users
- Priority: Low - business intelligence, not transactional

---

*Concerns audit: 2026-02-11*
