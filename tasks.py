import asyncio
from datetime import datetime

from lnbits.core.models import Payment
from lnbits.core.services import websocket_updater
from lnbits.tasks import register_invoice_listener
from loguru import logger

from .transaction_processor import poll_lamassu_transactions

#######################################
########## RUN YOUR TASKS HERE ########
#######################################

# The usual task is to listen to invoices related to this extension


async def wait_for_paid_invoices():
    """Invoice listener for DCA-related payments"""
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, "ext_satmachineadmin")
    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def hourly_transaction_polling():
    """Background task that polls Lamassu database every hour for new transactions"""
    logger.info("Starting hourly Lamassu transaction polling task")
    
    while True:
        try:
            logger.info(f"Running Lamassu transaction poll at {datetime.now()}")
            await poll_lamassu_transactions()
            logger.info("Completed Lamassu transaction poll, sleeping for 1 hour")
            
            # Sleep for 1 hour (3600 seconds)
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error in hourly polling task: {e}")
            # Sleep for 5 minutes before retrying on error
            await asyncio.sleep(300)


async def on_invoice_paid(payment: Payment) -> None:
    """Handle DCA-related invoice payments"""
    # DCA payments are handled internally by the transaction processor
    # This function can be extended if needed for additional payment processing
    if payment.extra.get("tag") in ["dca_distribution", "dca_commission"]:
        logger.info(f"DCA payment processed: {payment.checking_id} - {payment.amount} sats")
        # Could add websocket notifications here if needed
        pass
