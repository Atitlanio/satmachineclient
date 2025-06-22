# Description: This file contains the extensions API endpoints.

from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import create_invoice
from lnbits.decorators import require_admin_key
from starlette.exceptions import HTTPException

from .crud import (
    # DCA CRUD operations
    create_dca_client,
    get_dca_client,
    get_all_deposits,
    get_deposit,
    get_client_balance_summary,
)
from .models import (
    # DCA models
    CreateDcaClientData,
    DcaClient,
    DcaDeposit,
    ClientBalanceSummary,
)

satmachineclient_api_router = APIRouter()


###################################################
################ DCA API ENDPOINTS ################
###################################################

# DCA Client Endpoints
# Note: Client creation/update


@satmachineclient_api_router.post("/api/v1/dca/clients", status_code=HTTPStatus.CREATED)
async def api_create_test_dca_client(
    data: CreateDcaClientData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> DcaClient:
    return await create_dca_client(data)


@satmachineclient_api_router.get("/api/v1/dca/clients/{client_id}/balance")
async def api_get_client_balance(
    client_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> ClientBalanceSummary:
    """Get client balance summary"""
    client = await get_dca_client(client_id)
    if not client:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="DCA client not found."
        )

    return await get_client_balance_summary(client_id)


# DCA Deposit Endpoints


# NOTE: to Claude - modify this so it only gets the deposits for the user! important security
@satmachineclient_api_router.get("/api/v1/dca/deposits")
async def api_get_deposits(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> list[DcaDeposit]:
    """Get all deposits"""
    return await get_all_deposits()


# NOTE: does the client have any need to get sepcific deposits?
@satmachineclient_api_router.get("/api/v1/dca/deposits/{deposit_id}")
async def api_get_deposit(
    deposit_id: str,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> DcaDeposit:
    """Get a specific deposit"""
    deposit = await get_deposit(deposit_id)
    if not deposit:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Deposit not found."
        )
    return deposit
