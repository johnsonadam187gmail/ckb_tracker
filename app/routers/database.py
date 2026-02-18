"""
Database Management Router

Handles database export, backup, restore, and reset operations.
"""

import json
import shutil
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db, engine, SessionLocal
from app.models import (
    Base,
    User,
    Role,
    UserRole,
    ClassSchedule,
    GymLocation,
    ClassType,
    Term,
    TermTarget,
    Curriculum,
    Lesson,
    ClassInstance,
    FactAttendance,
    ClassFeedback,
    KioskAuth,
)
from app.config import settings

router = APIRouter(prefix="/database", tags=["database"])

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
SEEDS_DIR = PROJECT_ROOT / "seeds"
BACKUPS_DIR = PROJECT_ROOT / "backups"

# Ensure directories exist
SEEDS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)


def get_db_path() -> Path:
    """Get the database file path from settings."""
    db_url = settings.database_url
    if not db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=400,
            detail="Database operations only supported for SQLite databases",
        )

    db_path = Path(db_url.replace("sqlite:///", "").replace("sqlite://", ""))
    if db_path.is_absolute():
        return db_path
    else:
        return PROJECT_ROOT / db_path


@router.get("/stats")
def get_database_stats(db: Session = Depends(get_db)):
    """Get database statistics including record counts and size."""
    try:
        db_path = get_db_path()

        # Get file size
        size_bytes = db_path.stat().st_size if db_path.exists() else 0
        size_mb = size_bytes / (1024 * 1024)

        # Get record counts
        counts = {
            "users": db.query(User).count(),
            "user_roles": db.query(UserRole).count(),
            "classes": db.query(ClassSchedule).count(),
            "gym_locations": db.query(GymLocation).count(),
            "class_types": db.query(ClassType).count(),
            "terms": db.query(Term).count(),
            "term_targets": db.query(TermTarget).count(),
            "curricula": db.query(Curriculum).count(),
            "lessons": db.query(Lesson).count(),
            "class_instances": db.query(ClassInstance).count(),
            "attendance": db.query(FactAttendance).count(),
            "class_feedback": db.query(ClassFeedback).count(),
            "kiosk_auth": db.query(KioskAuth).count(),
        }

        # Get last backup time
        backups = sorted(
            BACKUPS_DIR.glob("backup_*.db*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        last_backup = None
        if backups:
            last_backup = datetime.fromtimestamp(backups[0].stat().st_mtime).isoformat()

        return {
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2),
            "record_counts": counts,
            "last_backup": last_backup,
            "database_path": str(db_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.post("/export-seed")
def export_seed_data(db: Session = Depends(get_db)):
    """Export current database data as JSON seed file."""
    try:
        # Gather all data
        data = {
            "metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "application": "CKB Tracker",
            },
            "data": {},
        }

        # Export gym locations
        gyms = db.query(GymLocation).all()
        data["data"]["gym_locations"] = [
            {
                "id": g.id,
                "name": g.name,
                "address": g.address,
            }
            for g in gyms
        ]

        # Export class types
        types = db.query(ClassType).all()
        data["data"]["class_types"] = [
            {
                "id": t.id,
                "name": t.name,
            }
            for t in types
        ]

        # Export terms
        terms = db.query(Term).all()
        data["data"]["terms"] = [
            {
                "id": t.id,
                "term_name": t.term_name,
                "start_date": t.start_date.isoformat(),
                "end_date": t.end_date.isoformat(),
                "created_at": t.created_at.isoformat(),
            }
            for t in terms
        ]

        # Export term targets
        targets = db.query(TermTarget).all()
        data["data"]["term_targets"] = [
            {
                "id": t.id,
                "term_id": t.term_id,
                "rank": t.rank,
                "target": t.target,
            }
            for t in targets
        ]

        # Export users
        users = db.query(User).all()
        data["data"]["users"] = [
            {
                "id": u.id,
                "user_uuid": u.user_uuid,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "password_hash": u.password_hash,
                "rank": u.rank,
                "last_graded_date": u.last_graded_date.isoformat()
                if u.last_graded_date
                else None,
                "comments": u.comments,
                "nicknames": u.nicknames,
                "profile_image_url": u.profile_image_url,
                "is_current": u.is_current,
                "effective_date": u.effective_date.isoformat(),
                "end_date": u.end_date.isoformat() if u.end_date else None,
                "created_date": u.created_date.isoformat(),
                "updated_date": u.updated_date.isoformat(),
            }
            for u in users
        ]

        # Export user roles
        user_roles = db.query(UserRole).all()
        data["data"]["user_roles"] = [
            {
                "id": ur.id,
                "user_uuid": ur.user_uuid,
                "role_id": ur.role_id,
                "is_current": ur.is_current,
                "effective_date": ur.effective_date.isoformat(),
                "end_date": ur.end_date.isoformat() if ur.end_date else None,
                "created_date": ur.created_date.isoformat(),
                "updated_date": ur.updated_date.isoformat(),
            }
            for ur in user_roles
        ]

        # Export class schedules
        classes = db.query(ClassSchedule).all()
        data["data"]["classes"] = [
            {
                "id": c.id,
                "class_uuid": c.class_uuid,
                "class_name": c.class_name,
                "day": c.day,
                "time": c.time,
                "description": c.description,
                "points": c.points,
                "gym_id": c.gym_id,
                "class_type_id": c.class_type_id,
                "is_current": c.is_current,
                "effective_date": c.effective_date.isoformat(),
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "created_date": c.created_date.isoformat(),
            }
            for c in classes
        ]

        # Export curricula
        curricula = db.query(Curriculum).all()
        data["data"]["curricula"] = [
            {
                "id": c.id,
                "class_id": c.class_id,
                "name": c.name,
                "description": c.description,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in curricula
        ]

        # Export lessons
        lessons = db.query(Lesson).all()
        data["data"]["lessons"] = [
            {
                "id": l.id,
                "curriculum_id": l.curriculum_id,
                "title": l.title,
                "description": l.description,
                "lesson_plan_url": l.lesson_plan_url,
                "video_folder_url": l.video_folder_url,
                "created_at": l.created_at.isoformat(),
                "updated_at": l.updated_at.isoformat(),
            }
            for l in lessons
        ]

        # Export class instances
        instances = db.query(ClassInstance).all()
        data["data"]["class_instances"] = [
            {
                "id": ci.id,
                "class_id": ci.class_id,
                "class_date": ci.class_date.isoformat(),
                "teacher_uuid": ci.teacher_uuid,
                "lesson_id": ci.lesson_id,
                "created_at": ci.created_at.isoformat(),
                "updated_at": ci.updated_at.isoformat(),
            }
            for ci in instances
        ]

        # Export attendance records
        attendance = db.query(FactAttendance).all()
        data["data"]["attendance"] = [
            {
                "id": a.id,
                "user_uuid": a.user_uuid,
                "class_id": a.class_id,
                "class_instance_id": a.class_instance_id,
                "teacher_uuid": a.teacher_uuid,
                "user_role_id": a.user_role_id,
                "attendance_date": a.attendance_date.isoformat(),
                "created_at": a.created_at.isoformat(),
                "status": a.status,
                "confirmed_by": a.confirmed_by,
                "confirmed_at": a.confirmed_at.isoformat() if a.confirmed_at else None,
            }
            for a in attendance
        ]

        # Export feedback
        feedback = db.query(ClassFeedback).all()
        data["data"]["class_feedback"] = [
            {
                "id": f.id,
                "user_uuid": f.user_uuid,
                "attendance_id": f.attendance_id,
                "class_instance_id": f.class_instance_id,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
            }
            for f in feedback
        ]

        # Export kiosk auth (if any)
        kiosk = db.query(KioskAuth).all()
        data["data"]["kiosk_auth"] = [
            {
                "id": k.id,
                "pin_hash": k.pin_hash,
                "created_at": k.created_at.isoformat(),
                "updated_at": k.updated_at.isoformat(),
            }
            for k in kiosk
        ]

        # Calculate record counts
        data["metadata"]["record_counts"] = {
            table: len(records) for table, records in data["data"].items()
        }

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed_filename = f"seed_{timestamp}.json"
        seed_path = SEEDS_DIR / seed_filename

        with open(seed_path, "w") as f:
            json.dump(data, f, indent=2)

        return {
            "message": "Seed file created successfully",
            "filename": seed_filename,
            "path": str(seed_path),
            "record_counts": data["metadata"]["record_counts"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting seed: {str(e)}")


@router.get("/list-seeds")
def list_seed_files():
    """List all available seed files."""
    try:
        seeds = sorted(
            SEEDS_DIR.glob("seed_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        result = []
        for seed in seeds:
            stat = seed.stat()
            result.append(
                {
                    "filename": seed.name,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                }
            )

        return {"seeds": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing seeds: {str(e)}")


@router.get("/download-seed/{filename}")
def download_seed_file(filename: str):
    """Download a specific seed file."""
    try:
        seed_path = SEEDS_DIR / filename

        if not seed_path.exists():
            raise HTTPException(status_code=404, detail="Seed file not found")

        return FileResponse(
            path=seed_path, filename=filename, media_type="application/json"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading seed: {str(e)}")


@router.post("/create-backup")
def create_database_backup():
    """Create a backup of the database file."""
    try:
        db_path = get_db_path()

        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database file not found")

        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = BACKUPS_DIR / backup_filename

        shutil.copy2(db_path, backup_path)

        size_mb = backup_path.stat().st_size / (1024 * 1024)

        return {
            "message": "Backup created successfully",
            "filename": backup_filename,
            "path": str(backup_path),
            "size_mb": round(size_mb, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")


@router.get("/list-backups")
def list_backup_files():
    """List all available backup files."""
    try:
        backups = sorted(
            BACKUPS_DIR.glob("backup_*.db*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        result = []
        for backup in backups:
            stat = backup.stat()
            result.append(
                {
                    "filename": backup.name,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                }
            )

        return {"backups": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing backups: {str(e)}")


@router.get("/download-backup/{filename}")
def download_backup_file(filename: str):
    """Download a specific backup file."""
    try:
        backup_path = BACKUPS_DIR / filename

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")

        return FileResponse(
            path=backup_path, filename=filename, media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading backup: {str(e)}"
        )


@router.post("/restore")
async def restore_database(
    file: UploadFile = File(...), confirm_phrase: str = Form(...)
):
    """Restore database from uploaded file (JSON seed or .db backup)."""
    try:
        # Verify confirmation phrase
        if confirm_phrase != "RESTORE DATABASE":
            raise HTTPException(
                status_code=400,
                detail="Invalid confirmation phrase. Type 'RESTORE DATABASE' to confirm.",
            )

        db_path = get_db_path()

        # Save uploaded file temporarily
        temp_path = (
            BACKUPS_DIR / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # Check file type
            if file.filename.endswith(".json"):
                # It's a JSON seed file
                with open(temp_path, "r") as f:
                    seed_data = json.load(f)

                # Validate seed structure
                if "data" not in seed_data:
                    raise HTTPException(
                        status_code=400, detail="Invalid seed file format"
                    )

                # Use the loader script logic (but in-memory)
                # Reset database
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)

                # Seed roles
                db = SessionLocal()
                try:
                    roles = [
                        Role(name="Student", description="Member attending classes"),
                        Role(name="Teacher", description="Instructor teaching classes"),
                        Role(
                            name="Admin", description="Administrator with full access"
                        ),
                    ]
                    for role in roles:
                        db.add(role)
                    db.commit()

                    # Load all data from seed
                    data = seed_data["data"]

                    # Load data in correct order (respecting foreign keys)
                    # Gyms
                    if "gym_locations" in data:
                        for g in data["gym_locations"]:
                            db.add(
                                GymLocation(
                                    id=g.get("id"),
                                    name=g["name"],
                                    address=g.get("address"),
                                )
                            )

                    # Class types
                    if "class_types" in data:
                        for t in data["class_types"]:
                            db.add(ClassType(id=t.get("id"), name=t["name"]))

                    # Terms
                    if "terms" in data:
                        from datetime import date

                        for t in data["terms"]:
                            db.add(
                                Term(
                                    id=t.get("id"),
                                    term_name=t["term_name"],
                                    start_date=date.fromisoformat(t["start_date"]),
                                    end_date=date.fromisoformat(t["end_date"]),
                                    created_at=datetime.fromisoformat(t["created_at"]),
                                )
                            )

                    # Users
                    if "users" in data:
                        from datetime import date

                        for u in data["users"]:
                            db.add(
                                User(
                                    id=u.get("id"),
                                    user_uuid=u["user_uuid"],
                                    first_name=u["first_name"],
                                    last_name=u["last_name"],
                                    email=u["email"],
                                    password_hash=u.get("password_hash"),
                                    rank=u.get("rank"),
                                    last_graded_date=date.fromisoformat(
                                        u["last_graded_date"]
                                    )
                                    if u.get("last_graded_date")
                                    else None,
                                    comments=u.get("comments"),
                                    nicknames=u.get("nicknames"),
                                    profile_image_url=u.get("profile_image_url"),
                                    is_current=u.get("is_current", True),
                                    effective_date=datetime.fromisoformat(
                                        u["effective_date"]
                                    ),
                                    end_date=datetime.fromisoformat(u["end_date"])
                                    if u.get("end_date")
                                    else None,
                                    created_date=datetime.fromisoformat(
                                        u["created_date"]
                                    ),
                                    updated_date=datetime.fromisoformat(
                                        u["updated_date"]
                                    ),
                                )
                            )

                    # ... (continue loading other tables)

                    db.commit()

                finally:
                    db.close()

                return {"message": "Database restored from seed file successfully"}

            elif file.filename.endswith(".db") or file.filename.endswith(".sqlite"):
                # It's a database file - replace directly
                # Stop any active connections (SQLite specific)
                engine.dispose()

                # Replace database file
                shutil.copy2(temp_path, db_path)

                return {"message": "Database restored from backup file successfully"}
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Use .json (seed) or .db (backup)",
                )

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error restoring database: {str(e)}"
        )


@router.post("/restore-from-backup/{filename}")
def restore_from_backup(filename: str, confirm_phrase: str = Form(...)):
    """Restore database from an existing backup file."""
    try:
        # Verify confirmation phrase
        if confirm_phrase != "RESTORE DATABASE":
            raise HTTPException(
                status_code=400,
                detail="Invalid confirmation phrase. Type 'RESTORE DATABASE' to confirm.",
            )

        db_path = get_db_path()
        backup_path = BACKUPS_DIR / filename

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")

        # Check if it's a JSON seed or .db file
        if filename.endswith(".json"):
            # Load as seed
            with open(backup_path, "r") as f:
                seed_data = json.load(f)

            # Validate and load
            if "data" not in seed_data:
                raise HTTPException(status_code=400, detail="Invalid seed file format")

            # Reset and load
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

            db = SessionLocal()
            try:
                # Seed roles
                roles = [
                    Role(name="Student", description="Member attending classes"),
                    Role(name="Teacher", description="Instructor teaching classes"),
                    Role(name="Admin", description="Administrator with full access"),
                ]
                for role in roles:
                    db.add(role)
                db.commit()

                data = seed_data["data"]

                # Load gyms
                if "gym_locations" in data:
                    for g in data["gym_locations"]:
                        db.add(
                            GymLocation(
                                id=g.get("id"), name=g["name"], address=g.get("address")
                            )
                        )

                # Load class types
                if "class_types" in data:
                    for t in data["class_types"]:
                        db.add(ClassType(id=t.get("id"), name=t["name"]))

                # Load terms
                if "terms" in data:
                    from datetime import date

                    for t in data["terms"]:
                        db.add(
                            Term(
                                id=t.get("id"),
                                term_name=t["term_name"],
                                start_date=date.fromisoformat(t["start_date"]),
                                end_date=date.fromisoformat(t["end_date"]),
                                created_at=datetime.fromisoformat(t["created_at"]),
                            )
                        )

                # Load term targets
                if "term_targets" in data:
                    for t in data["term_targets"]:
                        db.add(
                            TermTarget(
                                id=t.get("id"),
                                term_id=t["term_id"],
                                rank=t["rank"],
                                target=t["target"],
                            )
                        )

                # Load users
                if "users" in data:
                    from datetime import date

                    for u in data["users"]:
                        db.add(
                            User(
                                id=u.get("id"),
                                user_uuid=u["user_uuid"],
                                first_name=u["first_name"],
                                last_name=u["last_name"],
                                email=u["email"],
                                password_hash=u.get("password_hash"),
                                rank=u.get("rank"),
                                last_graded_date=date.fromisoformat(
                                    u["last_graded_date"]
                                )
                                if u.get("last_graded_date")
                                else None,
                                comments=u.get("comments"),
                                nicknames=u.get("nicknames"),
                                profile_image_url=u.get("profile_image_url"),
                                is_current=u.get("is_current", True),
                                effective_date=datetime.fromisoformat(
                                    u["effective_date"]
                                ),
                                end_date=datetime.fromisoformat(u["end_date"])
                                if u.get("end_date")
                                else None,
                                created_date=datetime.fromisoformat(u["created_date"]),
                                updated_date=datetime.fromisoformat(u["updated_date"]),
                            )
                        )

                # Load user roles
                if "user_roles" in data:
                    for ur in data["user_roles"]:
                        db.add(
                            UserRole(
                                id=ur.get("id"),
                                user_uuid=ur["user_uuid"],
                                role_id=ur["role_id"],
                                is_current=ur.get("is_current", True),
                                effective_date=datetime.fromisoformat(
                                    ur["effective_date"]
                                ),
                                end_date=datetime.fromisoformat(ur["end_date"])
                                if ur.get("end_date")
                                else None,
                                created_date=datetime.fromisoformat(ur["created_date"]),
                                updated_date=datetime.fromisoformat(ur["updated_date"]),
                            )
                        )

                # Load classes
                if "classes" in data:
                    for c in data["classes"]:
                        db.add(
                            ClassSchedule(
                                id=c.get("id"),
                                class_uuid=c["class_uuid"],
                                class_name=c["class_name"],
                                day=c["day"],
                                time=c["time"],
                                description=c.get("description"),
                                points=c.get("points", 1.0),
                                gym_id=c["gym_id"],
                                class_type_id=c["class_type_id"],
                                is_current=c.get("is_current", True),
                                effective_date=datetime.fromisoformat(
                                    c["effective_date"]
                                ),
                                end_date=datetime.fromisoformat(c["end_date"])
                                if c.get("end_date")
                                else None,
                                created_date=datetime.fromisoformat(c["created_date"]),
                            )
                        )

                # Load curricula
                if "curricula" in data:
                    for c in data["curricula"]:
                        db.add(
                            Curriculum(
                                id=c.get("id"),
                                class_id=c["class_id"],
                                name=c["name"],
                                description=c.get("description"),
                                created_at=datetime.fromisoformat(c["created_at"]),
                                updated_at=datetime.fromisoformat(c["updated_at"]),
                            )
                        )

                # Load lessons
                if "lessons" in data:
                    for l in data["lessons"]:
                        db.add(
                            Lesson(
                                id=l.get("id"),
                                curriculum_id=l["curriculum_id"],
                                title=l["title"],
                                description=l.get("description"),
                                lesson_plan_url=l.get("lesson_plan_url"),
                                video_folder_url=l.get("video_folder_url"),
                                created_at=datetime.fromisoformat(l["created_at"]),
                                updated_at=datetime.fromisoformat(l["updated_at"]),
                            )
                        )

                # Load class instances
                if "class_instances" in data:
                    from datetime import date

                    for ci in data["class_instances"]:
                        db.add(
                            ClassInstance(
                                id=ci.get("id"),
                                class_id=ci["class_id"],
                                class_date=date.fromisoformat(ci["class_date"]),
                                teacher_uuid=ci.get("teacher_uuid"),
                                lesson_id=ci.get("lesson_id"),
                                created_at=datetime.fromisoformat(ci["created_at"]),
                                updated_at=datetime.fromisoformat(ci["updated_at"]),
                            )
                        )

                # Load attendance
                if "attendance" in data:
                    from datetime import date

                    for a in data["attendance"]:
                        db.add(
                            FactAttendance(
                                id=a.get("id"),
                                user_uuid=a["user_uuid"],
                                class_id=a["class_id"],
                                class_instance_id=a.get("class_instance_id"),
                                teacher_uuid=a.get("teacher_uuid"),
                                user_role_id=a.get("user_role_id"),
                                attendance_date=date.fromisoformat(
                                    a["attendance_date"]
                                ),
                                created_at=datetime.fromisoformat(a["created_at"]),
                                status=a.get("status", "confirmed"),
                                confirmed_by=a.get("confirmed_by"),
                                confirmed_at=datetime.fromisoformat(a["confirmed_at"])
                                if a.get("confirmed_at")
                                else None,
                            )
                        )

                # Load feedback
                if "class_feedback" in data:
                    for f in data["class_feedback"]:
                        db.add(
                            ClassFeedback(
                                id=f.get("id"),
                                user_uuid=f["user_uuid"],
                                attendance_id=f["attendance_id"],
                                class_instance_id=f["class_instance_id"],
                                rating=f.get("rating"),
                                comment=f.get("comment"),
                                created_at=datetime.fromisoformat(f["created_at"]),
                                updated_at=datetime.fromisoformat(f["updated_at"]),
                            )
                        )

                # Load kiosk auth
                if "kiosk_auth" in data:
                    for k in data["kiosk_auth"]:
                        db.add(
                            KioskAuth(
                                id=k.get("id"),
                                pin_hash=k["pin_hash"],
                                created_at=datetime.fromisoformat(k["created_at"]),
                                updated_at=datetime.fromisoformat(k["updated_at"]),
                            )
                        )

                db.commit()

            finally:
                db.close()

            return {"message": f"Database restored from seed file: {filename}"}

        elif filename.endswith(".db"):
            # Replace database file directly
            engine.dispose()
            shutil.copy2(backup_path, db_path)

            return {"message": f"Database restored from backup: {filename}"}
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error restoring database: {str(e)}"
        )


@router.post("/reset")
def reset_database(
    mode: str = Form(...),  # "empty" or "seed"
    seed_file: Optional[str] = Form(None),
    confirm_phrase: str = Form(...),
):
    """Reset database. Mode can be 'empty' or 'seed' (with seed_file)."""
    try:
        # Verify confirmation phrase
        if confirm_phrase != "RESET DATABASE":
            raise HTTPException(
                status_code=400,
                detail="Invalid confirmation phrase. Type 'RESET DATABASE' to confirm.",
            )

        if mode == "empty":
            # Reset to empty (just roles)
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

            db = SessionLocal()
            try:
                roles = [
                    Role(name="Student", description="Member attending classes"),
                    Role(name="Teacher", description="Instructor teaching classes"),
                    Role(name="Admin", description="Administrator with full access"),
                ]
                for role in roles:
                    db.add(role)
                db.commit()
            finally:
                db.close()

            return {"message": "Database reset to empty state (roles only)"}

        elif mode == "seed":
            if not seed_file:
                raise HTTPException(
                    status_code=400, detail="seed_file required when mode is 'seed'"
                )

            seed_path = SEEDS_DIR / seed_file
            if not seed_path.exists():
                raise HTTPException(status_code=404, detail="Seed file not found")

            # Load and validate seed
            with open(seed_path, "r") as f:
                seed_data = json.load(f)

            if "data" not in seed_data:
                raise HTTPException(status_code=400, detail="Invalid seed file format")

            # Reset database
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

            # Load seed data
            db = SessionLocal()
            try:
                # Seed roles first
                roles = [
                    Role(name="Student", description="Member attending classes"),
                    Role(name="Teacher", description="Instructor teaching classes"),
                    Role(name="Admin", description="Administrator with full access"),
                ]
                for role in roles:
                    db.add(role)
                db.commit()

                data = seed_data["data"]

                # Load all tables in order
                if "gym_locations" in data:
                    for g in data["gym_locations"]:
                        db.add(
                            GymLocation(
                                id=g.get("id"), name=g["name"], address=g.get("address")
                            )
                        )

                if "class_types" in data:
                    for t in data["class_types"]:
                        db.add(ClassType(id=t.get("id"), name=t["name"]))

                if "terms" in data:
                    from datetime import date

                    for t in data["terms"]:
                        db.add(
                            Term(
                                id=t.get("id"),
                                term_name=t["term_name"],
                                start_date=date.fromisoformat(t["start_date"]),
                                end_date=date.fromisoformat(t["end_date"]),
                                created_at=datetime.fromisoformat(t["created_at"]),
                            )
                        )

                if "term_targets" in data:
                    for t in data["term_targets"]:
                        db.add(
                            TermTarget(
                                id=t.get("id"),
                                term_id=t["term_id"],
                                rank=t["rank"],
                                target=t["target"],
                            )
                        )

                if "users" in data:
                    from datetime import date

                    for u in data["users"]:
                        db.add(
                            User(
                                id=u.get("id"),
                                user_uuid=u["user_uuid"],
                                first_name=u["first_name"],
                                last_name=u["last_name"],
                                email=u["email"],
                                password_hash=u.get("password_hash"),
                                rank=u.get("rank"),
                                last_graded_date=date.fromisoformat(
                                    u["last_graded_date"]
                                )
                                if u.get("last_graded_date")
                                else None,
                                comments=u.get("comments"),
                                nicknames=u.get("nicknames"),
                                profile_image_url=u.get("profile_image_url"),
                                is_current=u.get("is_current", True),
                                effective_date=datetime.fromisoformat(
                                    u["effective_date"]
                                ),
                                end_date=datetime.fromisoformat(u["end_date"])
                                if u.get("end_date")
                                else None,
                                created_date=datetime.fromisoformat(u["created_date"]),
                                updated_date=datetime.fromisoformat(u["updated_date"]),
                            )
                        )

                if "user_roles" in data:
                    for ur in data["user_roles"]:
                        db.add(
                            UserRole(
                                id=ur.get("id"),
                                user_uuid=ur["user_uuid"],
                                role_id=ur["role_id"],
                                is_current=ur.get("is_current", True),
                                effective_date=datetime.fromisoformat(
                                    ur["effective_date"]
                                ),
                                end_date=datetime.fromisoformat(ur["end_date"])
                                if ur.get("end_date")
                                else None,
                                created_date=datetime.fromisoformat(ur["created_date"]),
                                updated_date=datetime.fromisoformat(ur["updated_date"]),
                            )
                        )

                if "classes" in data:
                    for c in data["classes"]:
                        db.add(
                            ClassSchedule(
                                id=c.get("id"),
                                class_uuid=c["class_uuid"],
                                class_name=c["class_name"],
                                day=c["day"],
                                time=c["time"],
                                description=c.get("description"),
                                points=c.get("points", 1.0),
                                gym_id=c["gym_id"],
                                class_type_id=c["class_type_id"],
                                is_current=c.get("is_current", True),
                                effective_date=datetime.fromisoformat(
                                    c["effective_date"]
                                ),
                                end_date=datetime.fromisoformat(c["end_date"])
                                if c.get("end_date")
                                else None,
                                created_date=datetime.fromisoformat(c["created_date"]),
                            )
                        )

                if "curricula" in data:
                    for c in data["curricula"]:
                        db.add(
                            Curriculum(
                                id=c.get("id"),
                                class_id=c["class_id"],
                                name=c["name"],
                                description=c.get("description"),
                                created_at=datetime.fromisoformat(c["created_at"]),
                                updated_at=datetime.fromisoformat(c["updated_at"]),
                            )
                        )

                if "lessons" in data:
                    for l in data["lessons"]:
                        db.add(
                            Lesson(
                                id=l.get("id"),
                                curriculum_id=l["curriculum_id"],
                                title=l["title"],
                                description=l.get("description"),
                                lesson_plan_url=l.get("lesson_plan_url"),
                                video_folder_url=l.get("video_folder_url"),
                                created_at=datetime.fromisoformat(l["created_at"]),
                                updated_at=datetime.fromisoformat(l["updated_at"]),
                            )
                        )

                if "class_instances" in data:
                    from datetime import date

                    for ci in data["class_instances"]:
                        db.add(
                            ClassInstance(
                                id=ci.get("id"),
                                class_id=ci["class_id"],
                                class_date=date.fromisoformat(ci["class_date"]),
                                teacher_uuid=ci.get("teacher_uuid"),
                                lesson_id=ci.get("lesson_id"),
                                created_at=datetime.fromisoformat(ci["created_at"]),
                                updated_at=datetime.fromisoformat(ci["updated_at"]),
                            )
                        )

                if "attendance" in data:
                    from datetime import date

                    for a in data["attendance"]:
                        db.add(
                            FactAttendance(
                                id=a.get("id"),
                                user_uuid=a["user_uuid"],
                                class_id=a["class_id"],
                                class_instance_id=a.get("class_instance_id"),
                                teacher_uuid=a.get("teacher_uuid"),
                                user_role_id=a.get("user_role_id"),
                                attendance_date=date.fromisoformat(
                                    a["attendance_date"]
                                ),
                                created_at=datetime.fromisoformat(a["created_at"]),
                                status=a.get("status", "confirmed"),
                                confirmed_by=a.get("confirmed_by"),
                                confirmed_at=datetime.fromisoformat(a["confirmed_at"])
                                if a.get("confirmed_at")
                                else None,
                            )
                        )

                if "class_feedback" in data:
                    for f in data["class_feedback"]:
                        db.add(
                            ClassFeedback(
                                id=f.get("id"),
                                user_uuid=f["user_uuid"],
                                attendance_id=f["attendance_id"],
                                class_instance_id=f["class_instance_id"],
                                rating=f.get("rating"),
                                comment=f.get("comment"),
                                created_at=datetime.fromisoformat(f["created_at"]),
                                updated_at=datetime.fromisoformat(f["updated_at"]),
                            )
                        )

                if "kiosk_auth" in data:
                    for k in data["kiosk_auth"]:
                        db.add(
                            KioskAuth(
                                id=k.get("id"),
                                pin_hash=k["pin_hash"],
                                created_at=datetime.fromisoformat(k["created_at"]),
                                updated_at=datetime.fromisoformat(k["updated_at"]),
                            )
                        )

                db.commit()

            finally:
                db.close()

            return {"message": f"Database reset and loaded from seed: {seed_file}"}
        else:
            raise HTTPException(
                status_code=400, detail="Mode must be 'empty' or 'seed'"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error resetting database: {str(e)}"
        )
