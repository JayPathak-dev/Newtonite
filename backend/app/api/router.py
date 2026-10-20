"""Main API router - assembles all v1 routes."""
from fastapi import APIRouter
from app.api.v1 import auth, work_items, teams, dashboard

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(work_items.router)
api_router.include_router(teams.router)
api_router.include_router(teams.users_router)
api_router.include_router(dashboard.router)
