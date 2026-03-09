from aiogram import Router
from .start import router as start_router
from .menu import router as menu_router
from .pr import router as pr_router
from .event import router as event_router
from .travel_module import router as travel_router
from .admin import router as admin_router
from .dinner.affiliate_integrated import router as affiliate_router
from .navigation import router as navigation_router
from .managers_chat import router as managers_chat_router

__all__ = [
    'start_router',
    'menu_router',
    'pr_router',
    'event_router',
    'travel_router',
    'admin_router',
    'navigation_router',
    'affiliate_router',
    'managers_chat_router',
]