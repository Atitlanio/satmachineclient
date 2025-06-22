from fastapi import APIRouter
from loguru import logger

from .crud import db
from .views import satmachineclient_generic_router
from .views_api import satmachineclient_api_router

logger.debug(
    "This logged message is from satmachineclient/__init__.py, you can debug in your "
    "extension using 'import logger from loguru' and 'logger.debug(<thing-to-log>)'."
)


satmachineclient_ext: APIRouter = APIRouter(
    prefix="/satmachineclient", tags=["DCA Client"]
)
satmachineclient_ext.include_router(satmachineclient_generic_router)
satmachineclient_ext.include_router(satmachineclient_api_router)

satmachineclient_static_files = [
    {
        "path": "/satmachineclient/static",
        "name": "satmachineclient_static",
    }
]

def satmachineclient_stop():
    # No background tasks to stop
    pass


def satmachineclient_start():
    # No background tasks to start - client extension is read-only
    pass


__all__ = [
    "db",
    "satmachineclient_ext",
    "satmachineclient_static_files",
    "satmachineclient_start",
    "satmachineclient_stop",
]
