# Description: Client-focused API endpoints for DCA dashboard

from http import HTTPStatus
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import require_admin_key
from starlette.exceptions import HTTPException

from .crud import (
    get_client_dashboard_summary,
    get_client_transactions,
    get_client_analytics,
    update_client_dca_settings,
    get_client_by_user_id,
    register_dca_client,
)
from .models import (
    ClientDashboardSummary,
    ClientTransaction,
    ClientAnalytics,
    UpdateClientSettings,
    ClientRegistrationData,
)

satmachineclient_api_router = APIRouter()


###################################################
############## CLIENT REGISTRATION ###############
###################################################

@satmachineclient_api_router.post("/api/v1/register", status_code=HTTPStatus.CREATED)
async def api_register_client(
    registration_data: ClientRegistrationData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> dict:
    """Register a new DCA client
    
    Clients can self-register using their wallet admin key.
    Creates a new client entry in the satoshimachine database.
    """
    result = await register_dca_client(
        wallet.wallet.user, 
        wallet.wallet.id, 
        registration_data
    )
    
    if "error" in result:
        if "already registered" in result["error"]:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=result["error"]
            )
        else:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=result["error"]
            )
    
    return result


@satmachineclient_api_router.get("/api/v1/registration-status")
async def api_check_registration_status(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> dict:
    """Check if user is already registered as a DCA client"""
    client = await get_client_by_user_id(wallet.wallet.user)
    
    return {
        "is_registered": client is not None,
        "client_id": client["id"] if client else None,
        "dca_mode": client["dca_mode"] if client else None,
        "status": client["status"] if client else None,
    }


###################################################
############## CLIENT DASHBOARD API ###############
###################################################

@satmachineclient_api_router.get("/api/v1/dashboard/summary")
async def api_get_dashboard_summary(
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> ClientDashboardSummary:
    """Get client dashboard summary metrics"""
    summary = await get_client_dashboard_summary(wallet.wallet.user)
    if not summary:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, 
            detail="Client data not found"
        )
    return summary


@satmachineclient_api_router.get("/api/v1/dashboard/transactions")
async def api_get_client_transactions(
    wallet: WalletTypeInfo = Depends(require_admin_key),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    transaction_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
) -> List[ClientTransaction]:
    """Get client's DCA transaction history with filtering"""
    return await get_client_transactions(
        wallet.wallet.user, 
        limit=limit, 
        offset=offset,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )


@satmachineclient_api_router.get("/api/v1/dashboard/analytics")
async def api_get_client_analytics(
    wallet: WalletTypeInfo = Depends(require_admin_key),
    time_range: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
) -> ClientAnalytics:
    """Get client performance analytics and cost basis data"""
    try:
        analytics = await get_client_analytics(wallet.wallet.user, time_range)
        if not analytics:
            # Return empty analytics data instead of error
            return ClientAnalytics(
                user_id=wallet.wallet.user,
                cost_basis_history=[],
                accumulation_timeline=[],
                transaction_frequency={}
            )
        return analytics
    except Exception as e:
        print(f"Analytics error: {e}")
        # Return empty analytics data as fallback
        return ClientAnalytics(
            user_id=wallet.wallet.user,
            cost_basis_history=[],
            accumulation_timeline=[],
            transaction_frequency={}
        )


@satmachineclient_api_router.put("/api/v1/dashboard/settings")
async def api_update_client_settings(
    settings: UpdateClientSettings,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> dict:
    """Update client DCA settings (mode, limits, status)
    
    Security: Users can only modify their own DCA settings.
    Validated by user_id lookup from wallet.wallet.user.
    """
    client = await get_client_by_user_id(wallet.wallet.user)
    if not client:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Client profile not found"
        )
    
    success = await update_client_dca_settings(client.id, settings)
    if not success:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Failed to update settings"
        )
    
    return {"message": "Settings updated successfully"}


@satmachineclient_api_router.get("/api/v1/dashboard/export/transactions")
async def api_export_transactions(
    wallet: WalletTypeInfo = Depends(require_admin_key),
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """Export client transaction history"""
    transactions = await get_client_transactions(
        wallet.wallet.user,
        limit=10000,  # Large limit for export
        start_date=start_date,
        end_date=end_date
    )
    
    if format == "csv":
        # Return CSV response
        from io import StringIO
        import csv
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Amount (Sats)', 'Amount (Fiat)', 'Exchange Rate', 'Type', 'Status'])
        
        for tx in transactions:
            writer.writerow([
                tx.created_at.isoformat(),
                tx.amount_sats,
                tx.amount_fiat / 100,  # Convert centavos to GTQ for CSV export
                tx.exchange_rate,
                tx.transaction_type,
                tx.status
            ])
        
        from fastapi.responses import StreamingResponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=dca_transactions.csv"}
        )
    else:
        return {"transactions": transactions}


# Removed local client-limits endpoint
# Client should call admin extension's public endpoint directly
