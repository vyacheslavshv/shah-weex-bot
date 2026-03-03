from aiogram import Router

from .group import router as group_router
from .commands import router as commands_router
from .admin import router as admin_router
from .relay import router as relay_router


def setup_routers():
    router = Router()
    router.include_router(group_router)
    router.include_router(commands_router)
    router.include_router(admin_router)
    router.include_router(relay_router)  # catch-all, must be last
    return router
