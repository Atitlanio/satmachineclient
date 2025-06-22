# Description: Pydantic data models for client extension API responses

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# Client Dashboard Data Models
class ClientDashboardSummary(BaseModel):
    """Summary metrics for client dashboard overview"""
    user_id: str
    total_sats_accumulated: int
    total_fiat_invested: int  # Confirmed deposits
    pending_fiat_deposits: int  # Pending deposits awaiting confirmation
    average_cost_basis: float  # Average sats per fiat unit
    current_fiat_balance: int  # Available balance for DCA
    total_transactions: int
    dca_mode: str  # 'flow' or 'fixed'
    dca_status: str  # 'active' or 'inactive'
    last_transaction_date: Optional[datetime]
    currency: str = "GTQ"


class ClientTransaction(BaseModel):
    """Read-only view of client's DCA transactions"""
    id: str
    amount_sats: int
    amount_fiat: int
    exchange_rate: float
    transaction_type: str  # 'flow', 'fixed', 'manual'
    status: str
    created_at: datetime
    lamassu_transaction_id: Optional[str] = None


class ClientAnalytics(BaseModel):
    """Performance analytics for client dashboard"""
    user_id: str
    cost_basis_history: List[dict]  # Historical cost basis data points
    accumulation_timeline: List[dict]  # Sats accumulated over time
    transaction_frequency: dict  # Transaction frequency metrics
    performance_vs_market: Optional[dict] = None  # Market comparison data


class ClientPreferences(BaseModel):
    """Client dashboard preferences and settings"""
    user_id: str
    preferred_currency: str = "GTQ"
    dashboard_theme: str = "light"
    chart_time_range: str = "30d"  # Default chart time range
    notification_preferences: dict = {}


class UpdateClientSettings(BaseModel):
    """Settings that client can modify"""
    dca_mode: Optional[str] = None  # 'flow' or 'fixed'
    fixed_mode_daily_limit: Optional[int] = None
    status: Optional[str] = None  # 'active' or 'inactive'


