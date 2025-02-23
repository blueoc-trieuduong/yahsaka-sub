from fastapi import APIRouter

from app.api.routes import login, packages, subscriptions, users, utils

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(subscriptions.router)
api_router.include_router(packages.router)
