# Currency conversion utilities for Client Extension API boundary
from decimal import Decimal
from typing import Union


def gtq_to_centavos(gtq_amount: Union[float, int, str]) -> int:
    """Convert GTQ to centavos for database storage"""
    return int(Decimal(str(gtq_amount)) * 100)


def centavos_to_gtq(centavos: int) -> float:
    """Convert centavos to GTQ for API responses"""
    return float(centavos) / 100


def format_gtq_currency(centavos: int) -> str:
    """Format centavos as GTQ currency string"""
    gtq_amount = centavos_to_gtq(centavos)
    return f"Q{gtq_amount:.2f}"


# Conversion helpers for client API responses
def dashboard_summary_db_to_api(summary_db) -> dict:
    """Convert database dashboard summary to API response"""
    return {
        "user_id": summary_db.user_id,
        "total_sats_accumulated": summary_db.total_sats_accumulated,
        "total_fiat_invested_gtq": centavos_to_gtq(summary_db.total_fiat_invested),
        "pending_fiat_deposits_gtq": centavos_to_gtq(summary_db.pending_fiat_deposits),
        "current_sats_fiat_value_gtq": centavos_to_gtq(int(summary_db.current_sats_fiat_value)),
        "average_cost_basis": summary_db.average_cost_basis,
        "current_fiat_balance_gtq": centavos_to_gtq(summary_db.current_fiat_balance),
        "total_transactions": summary_db.total_transactions,
        "dca_mode": summary_db.dca_mode,
        "dca_status": summary_db.dca_status,
        "last_transaction_date": summary_db.last_transaction_date,
        "currency": summary_db.currency
    }


def transaction_db_to_api(transaction_db) -> dict:
    """Convert database transaction to API response"""
    return {
        "id": transaction_db.id,
        "amount_sats": transaction_db.amount_sats,
        "amount_fiat_gtq": centavos_to_gtq(transaction_db.amount_fiat),
        "exchange_rate": transaction_db.exchange_rate,
        "transaction_type": transaction_db.transaction_type,
        "status": transaction_db.status,
        "created_at": transaction_db.created_at,
        "transaction_time": transaction_db.transaction_time,
        "lamassu_transaction_id": transaction_db.lamassu_transaction_id
    }