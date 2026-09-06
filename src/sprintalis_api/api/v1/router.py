from fastapi import APIRouter
from sprintalis_api.authentication.router import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
