# Description: Pydantic data models for client extension API responses

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# API Models for Client Dashboard (Frontend communication in GTQ)
class ClientDashboardSummaryAPI(BaseModel):
    """API model - client dashboard summary in GTQ"""
    user_id: str
    total_sats_accumulated: int
    total_fiat_invested_gtq: float  # Confirmed deposits in GTQ
    pending_fiat_deposits_gtq: float  # Pending deposits in GTQ
    current_sats_fiat_value_gtq: float  # Current fiat value of total sats in GTQ
    average_cost_basis: float  # Average sats per GTQ
    current_fiat_balance_gtq: float  # Available balance for DCA in GTQ
    total_transactions: int
    dca_mode: str  # 'flow' or 'fixed'
    dca_status: str  # 'active' or 'inactive'
    last_transaction_date: Optional[datetime]
    currency: str = "GTQ"


class ClientTransactionAPI(BaseModel):
    """API model - client transaction in GTQ"""
    id: str
    amount_sats: int
    amount_fiat_gtq: float  # Amount in GTQ
    exchange_rate: float
    transaction_type: str  # 'flow', 'fixed', 'manual'
    status: str
    created_at: datetime
    transaction_time: Optional[datetime] = None  # Original ATM transaction time
    lamassu_transaction_id: Optional[str] = None


# Internal Models for Client Dashboard (Database storage in centavos)
class ClientDashboardSummary(BaseModel):
    """Internal model - client dashboard summary stored in centavos"""
    user_id: str
    total_sats_accumulated: int
    total_fiat_invested: int  # Confirmed deposits (in centavos)
    pending_fiat_deposits: int  # Pending deposits awaiting confirmation (in centavos)
    current_sats_fiat_value: float  # Current fiat value of total sats (in centavos)
    average_cost_basis: float  # Average sats per fiat unit
    current_fiat_balance: int  # Available balance for DCA (in centavos)
    total_transactions: int
    dca_mode: str  # 'flow' or 'fixed'
    dca_status: str  # 'active' or 'inactive'
    last_transaction_date: Optional[datetime]
    currency: str = "GTQ"


class ClientTransaction(BaseModel):
    """Internal model - client transaction stored in centavos"""
    id: str
    amount_sats: int
    amount_fiat: int  # Stored in centavos (GTQ * 100) for precision
    exchange_rate: float
    transaction_type: str  # 'flow', 'fixed', 'manual'
    status: str
    created_at: datetime
    transaction_time: Optional[datetime] = None  # Original ATM transaction time
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


class ClientRegistrationData(BaseModel):
    """Data for client self-registration"""
    dca_mode: str = "flow"  # Default to flow mode
    fixed_mode_daily_limit: Optional[int] = None
    username: Optional[str] = None


