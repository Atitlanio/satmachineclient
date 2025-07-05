# Description: Client extension CRUD operations - reads from admin extension database

from typing import List, Optional
from datetime import datetime, timedelta

from lnbits.db import Database
from lnbits.utils.exchange_rates import satoshis_amount_as_fiat
from lnbits.core.crud.wallets import get_wallet

from .models import (
    ClientDashboardSummary,
    ClientTransaction,
    ClientAnalytics,
    UpdateClientSettings,
    ClientRegistrationData,
)

# Connect to admin extension's database
db = Database("ext_satoshimachine")


###################################################
############## CLIENT DASHBOARD CRUD ##############
###################################################

async def get_client_dashboard_summary(user_id: str) -> Optional[ClientDashboardSummary]:
    """Get dashboard summary for a specific user"""
    
    # Get client info
    client = await db.fetchone(
        "SELECT * FROM satoshimachine.dca_clients WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    if not client:
        return None
    
    # Get wallet to determine currency
    wallet = await get_wallet(client["wallet_id"])
    # TODO: Get currency from wallet; bit more difficult to do in a different 
    # currency than deposit cause of cross exchange rates
    # currency = wallet.currency or "GTQ"  # Default to GTQ if no currency set
    currency = "GTQ"  # Default to GTQ if no currency set
    
    # Get total sats accumulated from DCA transactions
    sats_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount_sats), 0) as total_sats 
        FROM satoshimachine.dca_payments 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    # Get total confirmed deposits (this is the "total invested")
    deposits_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount), 0) as confirmed_deposits
        FROM satoshimachine.dca_deposits 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client["id"]}
    )
    
    # Get total pending deposits (for additional info)
    pending_deposits_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount), 0) as pending_deposits
        FROM satoshimachine.dca_deposits 
        WHERE client_id = :client_id AND status = 'pending'
        """,
        {"client_id": client["id"]}
    )
    
    # Get total fiat spent on DCA transactions (to calculate remaining balance)
    dca_spent_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount_fiat), 0) as dca_spent
        FROM satoshimachine.dca_payments 
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
        FROM satoshimachine.dca_payments 
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
    avg_cost_basis = total_sats / dca_spent if dca_spent > 0 else 0  # Cost basis = sats / GTQ
    
    # Calculate current fiat value of total sats
    current_sats_fiat_value = 0.0
    if total_sats > 0:
        try:
            current_sats_fiat_value = await satoshis_amount_as_fiat(total_sats, currency)
        except Exception as e:
            print(f"Warning: Could not fetch exchange rate for {currency}: {e}")
            current_sats_fiat_value = 0.0
    
    return ClientDashboardSummary(
        user_id=user_id,
        total_sats_accumulated=total_sats,
        total_fiat_invested=total_invested,  # Sum of confirmed deposits
        pending_fiat_deposits=pending_deposits,  # Sum of pending deposits
        current_sats_fiat_value=current_sats_fiat_value,  # Current fiat value of sats
        average_cost_basis=avg_cost_basis,
        current_fiat_balance=remaining_balance,  # Confirmed deposits - DCA spent
        total_transactions=tx_stats["tx_count"] if tx_stats else 0,
        dca_mode=client["dca_mode"],
        dca_status=client["status"],
        last_transaction_date=tx_stats["last_tx_date"] if tx_stats else None,
        currency=currency  # Wallet's currency
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
        "SELECT id FROM satoshimachine.dca_clients WHERE user_id = :user_id",
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
               status, created_at, transaction_time, lamassu_transaction_id
        FROM satoshimachine.dca_payments 
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
            transaction_time=tx["transaction_time"],
            lamassu_transaction_id=tx["lamassu_transaction_id"]
        )
        for tx in transactions
    ]


async def get_client_analytics(user_id: str, time_range: str = "30d") -> Optional[ClientAnalytics]:
    """Get client performance analytics"""
    
    try:
        from datetime import datetime
        
        # Get client ID
        client = await db.fetchone(
            "SELECT id FROM satoshimachine.dca_clients WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        
        if not client:
            print(f"No client found for user_id: {user_id}")
            return None
        
        print(f"Found client {client['id']} for user {user_id}, loading analytics for time_range: {time_range}")
    
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
                COALESCE(transaction_time, created_at) as transaction_date,
                amount_sats,
                amount_fiat,
                exchange_rate,
                SUM(amount_sats) OVER (ORDER BY COALESCE(transaction_time, created_at)) as cumulative_sats,
                SUM(amount_fiat) OVER (ORDER BY COALESCE(transaction_time, created_at)) as cumulative_fiat
            FROM satoshimachine.dca_payments 
            WHERE client_id = :client_id 
              AND status = 'confirmed'
              AND COALESCE(transaction_time, created_at) IS NOT NULL
              AND COALESCE(transaction_time, created_at) >= :start_date
            ORDER BY COALESCE(transaction_time, created_at)
            """,
            {"client_id": client["id"], "start_date": start_date}
        )
        
        # Build cost basis history
        cost_basis_history = []
        for record in cost_basis_data:
            avg_cost_basis = record["cumulative_sats"] / record["cumulative_fiat"] if record["cumulative_fiat"] > 0 else 0  # Cost basis = sats / GTQ
            # Use transaction_date (which is COALESCE(transaction_time, created_at))
            date_to_use = record["transaction_date"]
            if date_to_use is None:
                print(f"Warning: Null date in cost basis data, skipping record")
                continue
            elif hasattr(date_to_use, 'isoformat'):
                # This is a datetime object
                date_str = date_to_use.isoformat()
            elif hasattr(date_to_use, 'strftime'):
                # This is a date object 
                date_str = date_to_use.strftime('%Y-%m-%d')
            elif isinstance(date_to_use, (int, float)):
                # This might be a Unix timestamp - check if it's in a reasonable range
                timestamp = float(date_to_use)
                # Check if this looks like a timestamp (between 1970 and 2100)
                if 0 < timestamp < 4102444800:  # Jan 1, 2100
                    # Could be seconds or milliseconds
                    if timestamp > 1000000000000:  # Likely milliseconds
                        timestamp = timestamp / 1000
                    date_str = datetime.fromtimestamp(timestamp).isoformat()
                else:
                    # Not a timestamp, treat as string
                    date_str = str(date_to_use)
                    print(f"Warning: Numeric date value out of timestamp range: {date_to_use}")
            elif isinstance(date_to_use, str) and date_to_use.isdigit():
                # This is a numeric string - might be a timestamp
                timestamp = float(date_to_use)
                # Check if this looks like a timestamp
                if 0 < timestamp < 4102444800:  # Jan 1, 2100
                    # Could be seconds or milliseconds
                    if timestamp > 1000000000000:  # Likely milliseconds
                        timestamp = timestamp / 1000
                    date_str = datetime.fromtimestamp(timestamp).isoformat()
                else:
                    # Not a timestamp, treat as string
                    date_str = str(date_to_use)
                    print(f"Warning: Numeric date string out of timestamp range: {date_to_use}")
            else:
                # Convert string representation to proper format
                date_str = str(date_to_use)
                print(f"Warning: Unexpected date format: {date_to_use} (type: {type(date_to_use)})")
            
            cost_basis_history.append({
                "date": date_str,
                "average_cost_basis": avg_cost_basis,
                "cumulative_sats": record["cumulative_sats"],
                "cumulative_fiat": record["cumulative_fiat"]
            })
        
        # Get accumulation timeline (daily/weekly aggregation)
        accumulation_data = await db.fetchall(
            """
            SELECT 
                DATE(COALESCE(transaction_time, created_at)) as date,
                SUM(amount_sats) as daily_sats,
                SUM(amount_fiat) as daily_fiat,
                COUNT(*) as daily_transactions
            FROM satoshimachine.dca_payments 
            WHERE client_id = :client_id 
              AND status = 'confirmed'
              AND COALESCE(transaction_time, created_at) IS NOT NULL
              AND COALESCE(transaction_time, created_at) >= :start_date
            GROUP BY DATE(COALESCE(transaction_time, created_at))
            ORDER BY date
            """,
            {"client_id": client["id"], "start_date": start_date}
        )
        
        accumulation_timeline = []
        for record in accumulation_data:
            # Handle date conversion safely
            date_value = record["date"]
            if date_value is None:
                print(f"Warning: Null date in accumulation data, skipping record")
                continue
            elif hasattr(date_value, 'isoformat'):
                # This is a datetime object
                date_str = date_value.isoformat()
            elif hasattr(date_value, 'strftime'):
                # This is a date object (from DATE() function)
                date_str = date_value.strftime('%Y-%m-%d')
            elif isinstance(date_value, (int, float)):
                # This might be a Unix timestamp - check if it's in a reasonable range
                timestamp = float(date_value)
                # Check if this looks like a timestamp (between 1970 and 2100)
                if 0 < timestamp < 4102444800:  # Jan 1, 2100
                    # Could be seconds or milliseconds
                    if timestamp > 1000000000000:  # Likely milliseconds
                        timestamp = timestamp / 1000
                    date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                else:
                    # Not a timestamp, treat as string
                    date_str = str(date_value)
                    print(f"Warning: Numeric accumulation date out of timestamp range: {date_value}")
            elif isinstance(date_value, str) and date_value.isdigit():
                # This is a numeric string - might be a timestamp
                timestamp = float(date_value)
                # Check if this looks like a timestamp
                if 0 < timestamp < 4102444800:  # Jan 1, 2100
                    # Could be seconds or milliseconds
                    if timestamp > 1000000000000:  # Likely milliseconds
                        timestamp = timestamp / 1000
                    date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                else:
                    # Not a timestamp, treat as string
                    date_str = str(date_value)
                    print(f"Warning: Numeric accumulation date string out of timestamp range: {date_value}")
            else:
                # Convert string representation to proper format
                date_str = str(date_value)
                print(f"Warning: Unexpected accumulation date format: {date_value} (type: {type(date_value)})")
            
            accumulation_timeline.append({
                "date": date_str,
                "sats": record["daily_sats"],
                "fiat": record["daily_fiat"],
                "transactions": record["daily_transactions"]
            })
        
        # Get transaction frequency metrics
        frequency_stats = await db.fetchone(
            """
            SELECT 
                COUNT(*) as total_transactions,
                AVG(amount_sats) as avg_sats_per_tx,
                AVG(amount_fiat) as avg_fiat_per_tx,
                MIN(COALESCE(transaction_time, created_at)) as first_tx,
                MAX(COALESCE(transaction_time, created_at)) as last_tx
            FROM satoshimachine.dca_payments 
            WHERE client_id = :client_id AND status = 'confirmed'
            """,
            {"client_id": client["id"]}
        )
        
        # Build transaction frequency with safe date handling
        transaction_frequency = {
            "total_transactions": frequency_stats["total_transactions"] if frequency_stats else 0,
            "avg_sats_per_transaction": frequency_stats["avg_sats_per_tx"] if frequency_stats else 0,
            "avg_fiat_per_transaction": frequency_stats["avg_fiat_per_tx"] if frequency_stats else 0,
            "first_transaction": None,
            "last_transaction": None
        }
        
        # Handle first_tx date safely
        if frequency_stats and frequency_stats["first_tx"]:
            first_tx = frequency_stats["first_tx"]
            if hasattr(first_tx, 'isoformat'):
                transaction_frequency["first_transaction"] = first_tx.isoformat()
            else:
                transaction_frequency["first_transaction"] = str(first_tx)
        
        # Handle last_tx date safely
        if frequency_stats and frequency_stats["last_tx"]:
            last_tx = frequency_stats["last_tx"]
            if hasattr(last_tx, 'isoformat'):
                transaction_frequency["last_transaction"] = last_tx.isoformat()
            else:
                transaction_frequency["last_transaction"] = str(last_tx)
    
        return ClientAnalytics(
            user_id=user_id,
            cost_basis_history=cost_basis_history,
            accumulation_timeline=accumulation_timeline,
            transaction_frequency=transaction_frequency
        )
        
    except Exception as e:
        print(f"Error in get_client_analytics for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def get_client_by_user_id(user_id: str):
    """Get client record by user_id"""
    return await db.fetchone(
        "SELECT * FROM satoshimachine.dca_clients WHERE user_id = :user_id",
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
            f"UPDATE satoshimachine.dca_clients SET {set_clause} WHERE id = :id",
            update_data
        )
        return True
    except Exception:
        return False


###################################################
############## CLIENT REGISTRATION ###############
###################################################

async def register_dca_client(user_id: str, wallet_id: str, registration_data: ClientRegistrationData) -> Optional[dict]:
    """Register a new DCA client - special permission for self-registration"""
    from lnbits.helpers import urlsafe_short_hash
    from lnbits.core.crud import get_user
    
    try:
        # Verify user exists and get username
        user = await get_user(user_id)
        username = registration_data.username or (user.username if user else f"user_{user_id[:8]}")
        
        # Check if client already exists
        existing_client = await db.fetchone(
            "SELECT id FROM satoshimachine.dca_clients WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        
        if existing_client:
            return {"error": "Client already registered", "client_id": existing_client[0]}
        
        # Create new client
        client_id = urlsafe_short_hash()
        await db.execute(
            """
            INSERT INTO satoshimachine.dca_clients 
            (id, user_id, wallet_id, username, dca_mode, fixed_mode_daily_limit, status, created_at, updated_at)
            VALUES (:id, :user_id, :wallet_id, :username, :dca_mode, :fixed_mode_daily_limit, :status, :created_at, :updated_at)
            """,
            {
                "id": client_id,
                "user_id": user_id,
                "wallet_id": wallet_id,
                "username": username,
                "dca_mode": registration_data.dca_mode,
                "fixed_mode_daily_limit": registration_data.fixed_mode_daily_limit,
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        )
        
        return {
            "success": True,
            "client_id": client_id,
            "message": f"DCA client registered successfully with {registration_data.dca_mode} mode"
        }
        
    except Exception as e:
        print(f"Error registering DCA client: {e}")
        return {"error": f"Registration failed: {str(e)}"}


async def get_client_by_user_id(user_id: str) -> Optional[dict]:
    """Get client by user_id - returns dict instead of model for easier access"""
    try:
        client = await db.fetchone(
            "SELECT * FROM satoshimachine.dca_clients WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        return dict(client) if client else None
    except Exception:
        return None


# Removed get_active_lamassu_config - client should not access sensitive admin config
# Client limits are now fetched via secure public API endpoint