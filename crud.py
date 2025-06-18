# Description: This file contains the CRUD operations for talking to the database.

from typing import List, Optional, Union
from datetime import datetime

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import (
    CreateMyExtensionData, MyExtension,
    CreateDcaClientData, DcaClient, UpdateDcaClientData,
    CreateDepositData, DcaDeposit, UpdateDepositStatusData,
    CreateDcaPaymentData, DcaPayment,
    ClientBalanceSummary,
    CreateLamassuConfigData, LamassuConfig, UpdateLamassuConfigData
)

db = Database("ext_myextension")


async def create_myextension(data: CreateMyExtensionData) -> MyExtension:
    data.id = urlsafe_short_hash()
    await db.insert("myextension.maintable", data)
    return MyExtension(**data.dict())


async def get_myextension(myextension_id: str) -> Optional[MyExtension]:
    return await db.fetchone(
        "SELECT * FROM myextension.maintable WHERE id = :id",
        {"id": myextension_id},
        MyExtension,
    )


async def get_myextensions(wallet_ids: Union[str, List[str]]) -> List[MyExtension]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM myextension.maintable WHERE wallet IN ({q}) ORDER BY id",
        model=MyExtension,
    )


async def update_myextension(data: CreateMyExtensionData) -> MyExtension:
    await db.update("myextension.maintable", data)
    return MyExtension(**data.dict())


async def delete_myextension(myextension_id: str) -> None:
    await db.execute(
        "DELETE FROM myextension.maintable WHERE id = :id", {"id": myextension_id}
    )


# DCA Client CRUD Operations
async def create_dca_client(data: CreateDcaClientData) -> DcaClient:
    client_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO myextension.dca_clients 
        (id, user_id, wallet_id, dca_mode, fixed_mode_daily_limit, status, created_at, updated_at)
        VALUES (:id, :user_id, :wallet_id, :dca_mode, :fixed_mode_daily_limit, :status, :created_at, :updated_at)
        """,
        {
            "id": client_id,
            "user_id": data.user_id,
            "wallet_id": data.wallet_id,
            "dca_mode": data.dca_mode,
            "fixed_mode_daily_limit": data.fixed_mode_daily_limit,
            "status": "active",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    )
    return await get_dca_client(client_id)


async def get_dca_client(client_id: str) -> Optional[DcaClient]:
    return await db.fetchone(
        "SELECT * FROM myextension.dca_clients WHERE id = :id",
        {"id": client_id},
        DcaClient,
    )


async def get_dca_clients() -> List[DcaClient]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_clients ORDER BY created_at DESC",
        model=DcaClient,
    )


async def get_dca_client_by_user(user_id: str) -> Optional[DcaClient]:
    return await db.fetchone(
        "SELECT * FROM myextension.dca_clients WHERE user_id = :user_id",
        {"user_id": user_id},
        DcaClient,
    )


async def update_dca_client(client_id: str, data: UpdateDcaClientData) -> Optional[DcaClient]:
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        return await get_dca_client(client_id)
    
    update_data["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    update_data["id"] = client_id
    
    await db.execute(
        f"UPDATE myextension.dca_clients SET {set_clause} WHERE id = :id",
        update_data
    )
    return await get_dca_client(client_id)


async def delete_dca_client(client_id: str) -> None:
    await db.execute(
        "DELETE FROM myextension.dca_clients WHERE id = :id", 
        {"id": client_id}
    )


# DCA Deposit CRUD Operations
async def create_deposit(data: CreateDepositData) -> DcaDeposit:
    deposit_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO myextension.dca_deposits 
        (id, client_id, amount, currency, status, notes, created_at)
        VALUES (:id, :client_id, :amount, :currency, :status, :notes, :created_at)
        """,
        {
            "id": deposit_id,
            "client_id": data.client_id,
            "amount": data.amount,
            "currency": data.currency,
            "status": "pending",
            "notes": data.notes,
            "created_at": datetime.now()
        }
    )
    return await get_deposit(deposit_id)


async def get_deposit(deposit_id: str) -> Optional[DcaDeposit]:
    return await db.fetchone(
        "SELECT * FROM myextension.dca_deposits WHERE id = :id",
        {"id": deposit_id},
        DcaDeposit,
    )


async def get_deposits_by_client(client_id: str) -> List[DcaDeposit]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_deposits WHERE client_id = :client_id ORDER BY created_at DESC",
        {"client_id": client_id},
        DcaDeposit,
    )


async def get_all_deposits() -> List[DcaDeposit]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_deposits ORDER BY created_at DESC",
        model=DcaDeposit,
    )


async def update_deposit_status(deposit_id: str, data: UpdateDepositStatusData) -> Optional[DcaDeposit]:
    update_data = {
        "status": data.status,
        "notes": data.notes
    }
    
    if data.status == "confirmed":
        update_data["confirmed_at"] = datetime.now()
    
    set_clause = ", ".join([f"{k} = :{k}" for k, v in update_data.items() if v is not None])
    filtered_data = {k: v for k, v in update_data.items() if v is not None}
    filtered_data["id"] = deposit_id
    
    await db.execute(
        f"UPDATE myextension.dca_deposits SET {set_clause} WHERE id = :id",
        filtered_data
    )
    return await get_deposit(deposit_id)


# DCA Payment CRUD Operations
async def create_dca_payment(data: CreateDcaPaymentData) -> DcaPayment:
    payment_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO myextension.dca_payments 
        (id, client_id, amount_sats, amount_fiat, exchange_rate, transaction_type, 
         lamassu_transaction_id, payment_hash, status, created_at)
        VALUES (:id, :client_id, :amount_sats, :amount_fiat, :exchange_rate, :transaction_type,
                :lamassu_transaction_id, :payment_hash, :status, :created_at)
        """,
        {
            "id": payment_id,
            "client_id": data.client_id,
            "amount_sats": data.amount_sats,
            "amount_fiat": data.amount_fiat,
            "exchange_rate": data.exchange_rate,
            "transaction_type": data.transaction_type,
            "lamassu_transaction_id": data.lamassu_transaction_id,
            "payment_hash": data.payment_hash,
            "status": "pending",
            "created_at": datetime.now()
        }
    )
    return await get_dca_payment(payment_id)


async def get_dca_payment(payment_id: str) -> Optional[DcaPayment]:
    return await db.fetchone(
        "SELECT * FROM myextension.dca_payments WHERE id = :id",
        {"id": payment_id},
        DcaPayment,
    )


async def get_payments_by_client(client_id: str) -> List[DcaPayment]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_payments WHERE client_id = :client_id ORDER BY created_at DESC",
        {"client_id": client_id},
        DcaPayment,
    )


async def get_all_payments() -> List[DcaPayment]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_payments ORDER BY created_at DESC",
        model=DcaPayment,
    )


async def get_payments_by_lamassu_transaction(lamassu_transaction_id: str) -> List[DcaPayment]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_payments WHERE lamassu_transaction_id = :transaction_id",
        {"transaction_id": lamassu_transaction_id},
        DcaPayment,
    )


# Balance and Summary Operations
async def get_client_balance_summary(client_id: str) -> ClientBalanceSummary:
    # Get total confirmed deposits
    total_deposits_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount), 0) as total, currency 
        FROM myextension.dca_deposits 
        WHERE client_id = :client_id AND status = 'confirmed'
        GROUP BY currency
        """,
        {"client_id": client_id}
    )
    
    # Get total payments made
    total_payments_result = await db.fetchone(
        """
        SELECT COALESCE(SUM(amount_fiat), 0) as total 
        FROM myextension.dca_payments 
        WHERE client_id = :client_id AND status = 'confirmed'
        """,
        {"client_id": client_id}
    )
    
    total_deposits = total_deposits_result["total"] if total_deposits_result else 0
    total_payments = total_payments_result["total"] if total_payments_result else 0
    currency = total_deposits_result["currency"] if total_deposits_result else "GTQ"
    
    return ClientBalanceSummary(
        client_id=client_id,
        total_deposits=total_deposits,
        total_payments=total_payments,
        remaining_balance=total_deposits - total_payments,
        currency=currency
    )


async def get_flow_mode_clients() -> List[DcaClient]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_clients WHERE dca_mode = 'flow' AND status = 'active'",
        model=DcaClient,
    )


async def get_fixed_mode_clients() -> List[DcaClient]:
    return await db.fetchall(
        "SELECT * FROM myextension.dca_clients WHERE dca_mode = 'fixed' AND status = 'active'",
        model=DcaClient,
    )


# Lamassu Configuration CRUD Operations
async def create_lamassu_config(data: CreateLamassuConfigData) -> LamassuConfig:
    config_id = urlsafe_short_hash()
    
    # Deactivate any existing configs first (only one active config allowed)
    await db.execute(
        "UPDATE myextension.lamassu_config SET is_active = false, updated_at = :updated_at",
        {"updated_at": datetime.now()}
    )
    
    await db.execute(
        """
        INSERT INTO myextension.lamassu_config 
        (id, host, port, database_name, username, password, is_active, created_at, updated_at)
        VALUES (:id, :host, :port, :database_name, :username, :password, :is_active, :created_at, :updated_at)
        """,
        {
            "id": config_id,
            "host": data.host,
            "port": data.port,
            "database_name": data.database_name,
            "username": data.username,
            "password": data.password,
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    )
    return await get_lamassu_config(config_id)


async def get_lamassu_config(config_id: str) -> Optional[LamassuConfig]:
    return await db.fetchone(
        "SELECT * FROM myextension.lamassu_config WHERE id = :id",
        {"id": config_id},
        LamassuConfig,
    )


async def get_active_lamassu_config() -> Optional[LamassuConfig]:
    return await db.fetchone(
        "SELECT * FROM myextension.lamassu_config WHERE is_active = true ORDER BY created_at DESC LIMIT 1",
        model=LamassuConfig,
    )


async def get_all_lamassu_configs() -> List[LamassuConfig]:
    return await db.fetchall(
        "SELECT * FROM myextension.lamassu_config ORDER BY created_at DESC",
        model=LamassuConfig,
    )


async def update_lamassu_config(config_id: str, data: UpdateLamassuConfigData) -> Optional[LamassuConfig]:
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        return await get_lamassu_config(config_id)
    
    update_data["updated_at"] = datetime.now()
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    update_data["id"] = config_id
    
    await db.execute(
        f"UPDATE myextension.lamassu_config SET {set_clause} WHERE id = :id",
        update_data
    )
    return await get_lamassu_config(config_id)


async def update_config_test_result(config_id: str, success: bool) -> None:
    await db.execute(
        """
        UPDATE myextension.lamassu_config 
        SET test_connection_last = :test_time, test_connection_success = :success, updated_at = :updated_at
        WHERE id = :id
        """,
        {
            "id": config_id,
            "test_time": datetime.now(),
            "success": success,
            "updated_at": datetime.now()
        }
    )


async def delete_lamassu_config(config_id: str) -> None:
    await db.execute(
        "DELETE FROM myextension.lamassu_config WHERE id = :id", 
        {"id": config_id}
    )
