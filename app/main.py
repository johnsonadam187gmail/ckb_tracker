"""
CKB Tracker - FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import models, database
from .config import settings
from .routers import (
    users,
    classes,
    class_instances,
    attendance,
    terms,
    gyms,
    class_types,
    term_targets,
    roles,
    curricula,
    lessons,
    auth,
    feedback,
    user_target_adjustments,
)

# Initialize the FastAPI app
app = FastAPI(title=settings.api_title, version=settings.api_version)

# Create the database tables on startup
models.Base.metadata.create_all(bind=database.engine)

# Include routers
app.include_router(users.router)
app.include_router(classes.router)
app.include_router(class_instances.router)
app.include_router(attendance.router)
app.include_router(terms.router)
app.include_router(gyms.router)
app.include_router(class_types.router)
app.include_router(term_targets.router)
app.include_router(roles.router)
app.include_router(curricula.router)
app.include_router(lessons.router)
app.include_router(auth.router)
app.include_router(feedback.router)
app.include_router(user_target_adjustments.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "Attendance API is live!"}
