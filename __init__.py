import asyncio

from fastapi import APIRouter
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices, hourly_transaction_polling
from .views import satmachineadmin_generic_router
from .views_api import satmachineadmin_api_router

logger.debug(
    "This logged message is from satmachineadmin/__init__.py, you can debug in your "
    "extension using 'import logger from loguru' and 'logger.debug(<thing-to-log>)'."
)


satmachineadmin_ext: APIRouter = APIRouter(prefix="/satmachineadmin", tags=["DCA Admin"])
satmachineadmin_ext.include_router(satmachineadmin_generic_router)
satmachineadmin_ext.include_router(satmachineadmin_api_router)

satmachineadmin_static_files = [
    {
        "path": "/satmachineadmin/static",
        "name": "satmachineadmin_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []


def satmachineadmin_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def satmachineadmin_start():
    # Start invoice listener task
    invoice_task = create_permanent_unique_task("ext_satmachineadmin", wait_for_paid_invoices)
    scheduled_tasks.append(invoice_task)
    
    # Start hourly transaction polling task
    polling_task = create_permanent_unique_task("ext_satmachineadmin_polling", hourly_transaction_polling)
    scheduled_tasks.append(polling_task)


__all__ = [
    "db",
    "satmachineadmin_ext",
    "satmachineadmin_static_files",
    "satmachineadmin_start",
    "satmachineadmin_stop",
]
