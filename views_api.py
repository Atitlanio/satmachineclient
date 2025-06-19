# Description: This file contains the extensions API endpoints.

from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import require_admin_key, require_invoice_key
from starlette.exceptions import HTTPException

from .crud import (
    create_myextension,
    delete_myextension,
    get_myextension,
    get_myextensions,
    update_myextension,
    # DCA CRUD operations
    create_dca_client,
    get_dca_clients,
    get_dca_client,
    update_dca_client,
    delete_dca_client,
    create_deposit,
    get_all_deposits,
    get_deposit,
    update_deposit_status,
    get_client_balance_summary,
    # Lamassu config CRUD operations
    create_lamassu_config,
    get_lamassu_config,
    get_active_lamassu_config,
    get_all_lamassu_configs,
    update_lamassu_config,
    update_config_test_result,
    delete_lamassu_config,
)
from .helpers import lnurler
from .models import (
    CreateMyExtensionData, CreatePayment, MyExtension,
    # DCA models
    CreateDcaClientData, DcaClient, UpdateDcaClientData,
    CreateDepositData, DcaDeposit, UpdateDepositStatusData,
    ClientBalanceSummary,
    CreateLamassuConfigData, LamassuConfig, UpdateLamassuConfigData
)

myextension_api_router = APIRouter()

# Note: we add the lnurl params to returns so the links
# are generated in the MyExtension model in models.py

## Get all the records belonging to the user


@myextension_api_router.get("/api/v1/myex")
async def api_myextensions(
    req: Request,  # Withoutthe lnurl stuff this wouldnt be needed
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[MyExtension]:
    wallet_ids = [wallet.wallet.id]
    user = await get_user(wallet.wallet.user)
    wallet_ids = user.wallet_ids if user else []
    myextensions = await get_myextensions(wallet_ids)

    # Populate lnurlpay and lnurlwithdraw for each instance.
    # Without the lnurl stuff this wouldnt be needed.
    for myex in myextensions:
        myex.lnurlpay = lnurler(myex.id, "myextension.api_lnurl_pay", req)
        myex.lnurlwithdraw = lnurler(myex.id, "myextension.api_lnurl_withdraw", req)

    return myextensions


## Get a single record


@myextension_api_router.get(
    "/api/v1/myex/{myextension_id}",
    dependencies=[Depends(require_invoice_key)],
)
async def api_myextension(myextension_id: str, req: Request) -> MyExtension:
    myex = await get_myextension(myextension_id)
    if not myex:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="MyExtension does not exist."
        )
    # Populate lnurlpay and lnurlwithdraw.
    # Without the lnurl stuff this wouldnt be needed.
    myex.lnurlpay = lnurler(myex.id, "myextension.api_lnurl_pay", req)
    myex.lnurlwithdraw = lnurler(myex.id, "myextension.api_lnurl_withdraw", req)

    return myex


## Create a new record


@myextension_api_router.post("/api/v1/myex", status_code=HTTPStatus.CREATED)
async def api_myextension_create(
    req: Request,  # Withoutthe lnurl stuff this wouldnt be needed
    data: CreateMyExtensionData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> MyExtension:
    myex = await create_myextension(data)

    # Populate lnurlpay and lnurlwithdraw.
    # Withoutthe lnurl stuff this wouldnt be needed.
    myex.lnurlpay = lnurler(myex.id, "myextension.api_lnurl_pay", req)
    myex.lnurlwithdraw = lnurler(myex.id, "myextension.api_lnurl_withdraw", req)

    return myex


## update a record


@myextension_api_router.put("/api/v1/myex/{myextension_id}")
async def api_myextension_update(
    req: Request,  # Withoutthe lnurl stuff this wouldnt be needed
    data: CreateMyExtensionData,
    myextension_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> MyExtension:
    myex = await get_myextension(myextension_id)
    if not myex:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="MyExtension does not exist."
        )

    if wallet.wallet.id != myex.wallet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your MyExtension."
        )

    for key, value in data.dict().items():
        setattr(myex, key, value)

    myex = await update_myextension(data)

    # Populate lnurlpay and lnurlwithdraw.
    # Without the lnurl stuff this wouldnt be needed.
    myex.lnurlpay = lnurler(myex.id, "myextension.api_lnurl_pay", req)
    myex.lnurlwithdraw = lnurler(myex.id, "myextension.api_lnurl_withdraw", req)

    return myex


## Delete a record


@myextension_api_router.delete("/api/v1/myex/{myextension_id}")
async def api_myextension_delete(
    myextension_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    myex = await get_myextension(myextension_id)

    if not myex:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="MyExtension does not exist."
        )

    if myex.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your MyExtension."
        )

    await delete_myextension(myextension_id)
    return


# ANY OTHER ENDPOINTS YOU NEED

## This endpoint creates a payment


@myextension_api_router.post("/api/v1/myex/payment", status_code=HTTPStatus.CREATED)
async def api_myextension_create_invoice(data: CreatePayment) -> dict:
    myextension = await get_myextension(data.myextension_id)

    if not myextension:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="MyExtension does not exist."
        )

    # we create a payment and add some tags,
    # so tasks.py can grab the payment once its paid

    payment = await create_invoice(
        wallet_id=myextension.wallet,
        amount=data.amount,
        memo=(
            f"{data.memo} to {myextension.name}" if data.memo else f"{myextension.name}"
        ),
        extra={
            "tag": "myextension",
            "amount": data.amount,
        },
    )

    return {"payment_hash": payment.payment_hash, "payment_request": payment.bolt11}


###################################################
################ DCA API ENDPOINTS ################
###################################################

# DCA Client Endpoints

@myextension_api_router.get("/api/v1/dca/clients")
async def api_get_dca_clients(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[DcaClient]:
    """Get all DCA clients"""
    return await get_dca_clients()


@myextension_api_router.get("/api/v1/dca/clients/{client_id}")
async def api_get_dca_client(
    client_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> DcaClient:
    """Get a specific DCA client"""
    client = await get_dca_client(client_id)
    if not client:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="DCA client not found."
        )
    return client


# Note: Client creation/update/delete will be handled by the DCA client extension
# Admin extension only reads existing clients and manages their deposits

# TEMPORARY: Test client creation endpoint (remove in production)
@myextension_api_router.post("/api/v1/dca/clients", status_code=HTTPStatus.CREATED)
async def api_create_test_dca_client(
    data: CreateDcaClientData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> DcaClient:
    """Create a test DCA client (temporary for testing)"""
    return await create_dca_client(data)


@myextension_api_router.get("/api/v1/dca/clients/{client_id}/balance")
async def api_get_client_balance(
    client_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> ClientBalanceSummary:
    """Get client balance summary"""
    client = await get_dca_client(client_id)
    if not client:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="DCA client not found."
        )
    
    return await get_client_balance_summary(client_id)


# DCA Deposit Endpoints

@myextension_api_router.get("/api/v1/dca/deposits")
async def api_get_deposits(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> list[DcaDeposit]:
    """Get all deposits"""
    return await get_all_deposits()


@myextension_api_router.get("/api/v1/dca/deposits/{deposit_id}")
async def api_get_deposit(
    deposit_id: str,
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> DcaDeposit:
    """Get a specific deposit"""
    deposit = await get_deposit(deposit_id)
    if not deposit:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Deposit not found."
        )
    return deposit


@myextension_api_router.post("/api/v1/dca/deposits", status_code=HTTPStatus.CREATED)
async def api_create_deposit(
    data: CreateDepositData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> DcaDeposit:
    """Create a new deposit"""
    # Verify client exists
    client = await get_dca_client(data.client_id)
    if not client:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="DCA client not found."
        )
    
    return await create_deposit(data)


@myextension_api_router.put("/api/v1/dca/deposits/{deposit_id}/status")
async def api_update_deposit_status(
    deposit_id: str,
    data: UpdateDepositStatusData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> DcaDeposit:
    """Update deposit status (e.g., confirm deposit)"""
    deposit = await get_deposit(deposit_id)
    if not deposit:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Deposit not found."
        )
    
    updated_deposit = await update_deposit_status(deposit_id, data)
    if not updated_deposit:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to update deposit."
        )
    return updated_deposit


# Transaction Polling Endpoints

@myextension_api_router.post("/api/v1/dca/test-connection")
async def api_test_database_connection(
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    """Test connection to Lamassu database with detailed reporting"""
    try:
        from .transaction_processor import transaction_processor
        
        # Use the detailed test method
        result = await transaction_processor.test_connection_detailed()
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Test connection error: {str(e)}",
            "steps": [f"❌ Unexpected error: {str(e)}"],
            "ssh_tunnel_used": False,
            "ssh_tunnel_success": False,
            "database_connection_success": False
        }


@myextension_api_router.post("/api/v1/dca/manual-poll")
async def api_manual_poll(
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    """Manually trigger a poll of the Lamassu database"""
    try:
        from .transaction_processor import transaction_processor
        from .crud import update_poll_start_time, update_poll_success_time
        
        # Get database configuration
        db_config = await transaction_processor.connect_to_lamassu_db()
        if not db_config:
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Could not get Lamassu database configuration"
            )
        
        config_id = db_config["config_id"]
        
        # Record manual poll start time
        await update_poll_start_time(config_id)
        
        # Fetch and process transactions via SSH
        new_transactions = await transaction_processor.fetch_new_transactions(db_config)
        
        transactions_processed = 0
        for transaction in new_transactions:
            await transaction_processor.process_transaction(transaction)
            transactions_processed += 1
        
        # Record successful manual poll completion
        await update_poll_success_time(config_id)
        
        return {
            "success": True,
            "transactions_processed": transactions_processed,
            "message": f"Processed {transactions_processed} new transactions since last poll"
        }
            
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error during manual poll: {str(e)}"
        )


@myextension_api_router.post("/api/v1/dca/test-transaction")
async def api_test_transaction(
    wallet: WalletTypeInfo = Depends(require_admin_key),
    crypto_atoms: int = 103,
    commission_percentage: float = 0.03,
    discount: float = 0.0,
) -> dict:
    """Test transaction processing with simulated Lamassu transaction data"""
    try:
        from .transaction_processor import transaction_processor
        import uuid
        from datetime import datetime, timezone
        
        # Create a mock transaction that mimics Lamassu database structure
        mock_transaction = {
            "transaction_id": str(uuid.uuid4())[:8],  # Short ID for testing
            "crypto_amount": crypto_atoms,  # Total sats including commission
            "fiat_amount": 100,  # Mock fiat amount (100 centavos = 1 GTQ)
            "commission_percentage": commission_percentage,  # Already as decimal
            "discount": discount,
            "transaction_time": datetime.now(timezone.utc),
            "crypto_code": "BTC",
            "fiat_code": "GTQ",
            "device_id": "test_device",
            "status": "confirmed"
        }
        
        # Process the mock transaction through the complete DCA flow
        await transaction_processor.process_transaction(mock_transaction)
        
        # Calculate commission for response
        if commission_percentage > 0:
            effective_commission = commission_percentage * (100 - discount) / 100
            base_crypto_atoms = int(crypto_atoms / (1 + effective_commission))
            commission_amount_sats = crypto_atoms - base_crypto_atoms
        else:
            base_crypto_atoms = crypto_atoms
            commission_amount_sats = 0
        
        return {
            "success": True,
            "message": "Test transaction processed successfully",
            "transaction_details": {
                "transaction_id": mock_transaction["transaction_id"],
                "total_amount_sats": crypto_atoms,
                "base_amount_sats": base_crypto_atoms,
                "commission_amount_sats": commission_amount_sats,
                "commission_percentage": commission_percentage * 100,  # Show as percentage
                "effective_commission": effective_commission * 100 if commission_percentage > 0 else 0,
                "discount": discount
            }
        }
            
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error processing test transaction: {str(e)}"
        )


# Lamassu Configuration Endpoints

@myextension_api_router.get("/api/v1/dca/config")
async def api_get_lamassu_config(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
) -> Optional[LamassuConfig]:
    """Get active Lamassu database configuration"""
    return await get_active_lamassu_config()


@myextension_api_router.post("/api/v1/dca/config", status_code=HTTPStatus.CREATED)
async def api_create_lamassu_config(
    data: CreateLamassuConfigData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> LamassuConfig:
    """Create/update Lamassu database configuration"""
    return await create_lamassu_config(data)


@myextension_api_router.put("/api/v1/dca/config/{config_id}")
async def api_update_lamassu_config(
    config_id: str,
    data: UpdateLamassuConfigData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> LamassuConfig:
    """Update Lamassu database configuration"""
    config = await get_lamassu_config(config_id)
    if not config:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Configuration not found."
        )
    
    updated_config = await update_lamassu_config(config_id, data)
    if not updated_config:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to update configuration."
        )
    return updated_config


@myextension_api_router.delete("/api/v1/dca/config/{config_id}")
async def api_delete_lamassu_config(
    config_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    """Delete Lamassu database configuration"""
    config = await get_lamassu_config(config_id)
    if not config:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Configuration not found."
        )
    
    await delete_lamassu_config(config_id)
    return {"message": "Configuration deleted successfully"}
