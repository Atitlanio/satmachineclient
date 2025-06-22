# Description: Client extension CRUD operations - reads from admin extension database

from typing import List, Optional
from datetime import datetime, timedelta

from lnbits.db import Database

from .models import (
    ClientDashboardSummary,
    ClientTransaction,
    ClientAnalytics,
    UpdateClientSettings,
)

# Connect to admin extension's database
db = Database("ext_satmachineadmin")


###################################################
############## CLIENT DASHBOARD CRUD ##############
###################################################

async def get_client_dashboard_summary(user_id: str) -> Optional[ClientDashboardSummary]:
    """Get dashboard summary for a specific user"""
    
    # Get client info
    client = await db.fetchone(
        "SELECT * FROM satmachineadmin.dca_clients WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    if not client:
        return None
    
    # Get total sats accumulated from DCA transactions
    sats_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount_sats), 0) as total_sats 
        FROM satmachineadmin.dca_payments 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    # Get total confirmed deposits (this is the "total invested")
    deposits_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount), 0) as confirmed_deposits
        FROM satmachineadmin.dca_deposits 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    # Get total pending deposits (for additional info)
    pending_deposits_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount), 0) as pending_deposits
        FROM satmachineadmin.dca_deposits 
        WHERE client_id = :client_id AND status = 'pending'
        """,
        {"client_id": client["id"]}
    )
    
    # Get total fiat spent on DCA transactions (to calculate remaining balance)
    dca_spent_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount_fiat), 0) as dca_spent
        FROM satmachineadmin.dca_payments 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    # Get transaction count and last transaction date
    tx_stats = await db.fetchone(
        """
        SELECT 
            COUNT(*) as tx_count,
            MAX(created_at) as last_tx_date
        FROM satmachineadmin.dca_payments 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    # Extract values from query results
    total_sats = sats_result["total_sats"] if sats_result else 0
    confirmed_deposits = deposits_result["confirmed_deposits"] if deposits_result else 0
    pending_deposits = pending_deposits_result["pending_deposits"] if pending_deposits_result else 0
    dca_spent = dca_spent_result["dca_spent"] if dca_spent_result else 0
    
    # Calculate metrics
    total_invested = confirmed_deposits  # Total invested = all confirmed deposits
    remaining_balance = confirmed_deposits - dca_spent  # Remaining = deposits - DCA spending
    avg_cost_basis = total_sats / dca_spent if dca_spent > 0 else 0  # Cost basis = sats / fiat spent
    
    return ClientDashboardSummary(
        user_id=user_id,
        total_sats_accumulated=total_sats,
        total_fiat_invested=total_invested,  # Sum of confirmed deposits
        pending_fiat_deposits=pending_deposits,  # Sum of pending deposits
        average_cost_basis=avg_cost_basis,
        current_fiat_balance=remaining_balance,  # Confirmed deposits - DCA spent
        total_transactions=tx_stats["tx_count"] if tx_stats else 0,
        dca_mode=client["dca_mode"],
        dca_status=client["status"],
        last_transaction_date=tx_stats["last_tx_date"] if tx_stats else None
    )


async def get_client_transactions(
    user_id: str, 
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[ClientTransaction]:
    """Get client's transaction history with filtering"""
    
    # Get client ID first
    client = await db.fetchone(
        "SELECT id FROM satmachineadmin.dca_clients WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    if not client:
        return []
    
    # Build query with filters
    where_conditions = ["client_id = :client_id"]
    params = {"client_id": client["id"], "limit": limit, "offset": offset}
    
    if transaction_type:
        where_conditions.append("transaction_type = :transaction_type")
        params["transaction_type"] = transaction_type
    
    if start_date:
        where_conditions.append("created_at >= :start_date")
        params["start_date"] = start_date
    
    if end_date:
        where_conditions.append("created_at <= :end_date")
        params["end_date"] = end_date
    
    where_clause = " AND ".join(where_conditions)
    
    transactions = await db.fetchall(
        f"""
        SELECT id, amount_sats, amount_fiat, exchange_rate, transaction_type, 
               status, created_at, lamassu_transaction_id
        FROM satmachineadmin.dca_payments 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """,
        params
    )
    
    return [
        ClientTransaction(
            id=tx["id"],
            amount_sats=tx["amount_sats"],
            amount_fiat=tx["amount_fiat"],
            exchange_rate=tx["exchange_rate"],
            transaction_type=tx["transaction_type"],
            status=tx["status"],
            created_at=tx["created_at"],
            lamassu_transaction_id=tx["lamassu_transaction_id"]
        )
        for tx in transactions
    ]


async def get_client_analytics(user_id: str, time_range: str = "30d") -> Optional[ClientAnalytics]:
    """Get client performance analytics"""
    
    # Get client ID
    client = await db.fetchone(
        "SELECT id FROM satmachineadmin.dca_clients WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    if not client:
        return None
    
    # Calculate date range
    if time_range == "7d":
        start_date = datetime.now() - timedelta(days=7)
    elif time_range == "30d":
        start_date = datetime.now() - timedelta(days=30)
    elif time_range == "90d":
        start_date = datetime.now() - timedelta(days=90)
    elif time_range == "1y":
        start_date = datetime.now() - timedelta(days=365)
    else:  # "all"
        start_date = datetime(2020, 1, 1)  # Arbitrary early date
    
    # Get cost basis history (running average)
    cost_basis_data = await db.fetchall(
        """
        SELECT 
            created_at,
            amount_sats,
            amount_fiat,
            exchange_rate,
            SUM(amount_sats) OVER (ORDER BY created_at) as cumulative_sats,
            SUM(amount_fiat) OVER (ORDER BY created_at) as cumulative_fiat
        FROM satmachineadmin.dca_payments 
        WHERE client_id = :client_id 
          AND status = 'confirmed'
          AND created_at >= :start_date
        ORDER BY created_at
        """,
        {"client_id": client["id"], "start_date": start_date}
    )
    
    # Build cost basis history
    cost_basis_history = []
    for record in cost_basis_data:
        avg_cost_basis = record["cumulative_sats"] / record["cumulative_fiat"] if record["cumulative_fiat"] > 0 else 0
        cost_basis_history.append({
            "date": record["created_at"].isoformat(),
            "average_cost_basis": avg_cost_basis,
            "cumulative_sats": record["cumulative_sats"],
            "cumulative_fiat": record["cumulative_fiat"]
        })
    
    # Get accumulation timeline (daily/weekly aggregation)
    accumulation_data = await db.fetchall(
        """
        SELECT 
            DATE(created_at) as date,
            SUM(amount_sats) as daily_sats,
            SUM(amount_fiat) as daily_fiat,
            COUNT(*) as daily_transactions
        FROM satmachineadmin.dca_payments 
        WHERE client_id = :client_id 
          AND status = 'confirmed'
          AND created_at >= :start_date
        GROUP BY DATE(created_at)
        ORDER BY date
        """,
        {"client_id": client["id"], "start_date": start_date}
    )
    
    accumulation_timeline = [
        {
            "date": record["date"],
            "sats": record["daily_sats"],
            "fiat": record["daily_fiat"],
            "transactions": record["daily_transactions"]
        }
        for record in accumulation_data
    ]
    
    # Get transaction frequency metrics
    frequency_stats = await db.fetchone(
        """
        SELECT 
            COUNT(*) as total_transactions,
            AVG(amount_sats) as avg_sats_per_tx,
            AVG(amount_fiat) as avg_fiat_per_tx,
            MIN(created_at) as first_tx,
            MAX(created_at) as last_tx
        FROM satmachineadmin.dca_payments 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    transaction_frequency = {
        "total_transactions": frequency_stats["total_transactions"] if frequency_stats else 0,
        "avg_sats_per_transaction": frequency_stats["avg_sats_per_tx"] if frequency_stats else 0,
        "avg_fiat_per_transaction": frequency_stats["avg_fiat_per_tx"] if frequency_stats else 0,
        "first_transaction": frequency_stats["first_tx"].isoformat() if frequency_stats and frequency_stats["first_tx"] else None,
        "last_transaction": frequency_stats["last_tx"].isoformat() if frequency_stats and frequency_stats["last_tx"] else None
    }
    
    return ClientAnalytics(
        user_id=user_id,
        cost_basis_history=cost_basis_history,
        accumulation_timeline=accumulation_timeline,
        transaction_frequency=transaction_frequency
    )


async def get_client_by_user_id(user_id: str):
    """Get client record by user_id"""
    return await db.fetchone(
        "SELECT * FROM satmachineadmin.dca_clients WHERE user_id = :user_id",
        {"user_id": user_id}
    )


async def update_client_dca_settings(client_id: str, settings: UpdateClientSettings) -> bool:
    """Update client DCA settings (mode, limits, status)"""
    try:
        update_data = {k: v for k, v in settings.dict().items() if v is not None}
        if not update_data:
            return True  # Nothing to update
        
        update_data["updated_at"] = datetime.now()
        set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
        update_data["id"] = client_id
        
        await db.execute(
            f"UPDATE satmachineadmin.dca_clients SET {set_clause} WHERE id = :id",
            update_data
        )
        return True
    except Exception:
        return False