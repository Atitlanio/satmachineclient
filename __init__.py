import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices, hourly_transaction_polling
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

scheduled_tasks: list[asyncio.Task] = []


def satmachineclient_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def satmachineclient_start():
    # Start invoice listener task
    invoice_task = create_permanent_unique_task(
        "ext_satmachineclient", wait_for_paid_invoices
    )
    scheduled_tasks.append(invoice_task)

    # Start hourly transaction polling task
    polling_task = create_permanent_unique_task(
        "ext_satmachineclient_polling", hourly_transaction_polling
    )
    scheduled_tasks.append(polling_task)


__all__ = [
    "db",
    "satmachineclient_ext",
    "satmachineclient_static_files",
    "satmachineclient_start",
    "satmachineclient_stop",
]
