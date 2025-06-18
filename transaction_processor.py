# Transaction processing and polling service for Lamassu ATM integration

import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger
import socket
import threading
import time

try:
    import asyncssh
    SSH_AVAILABLE = True
except ImportError:
    try:
        # Fallback to subprocess-based SSH tunnel
        import subprocess
        SSH_AVAILABLE = True
    except ImportError:
        SSH_AVAILABLE = False
        logger.warning("SSH tunnel support not available")

from lnbits.core.services import create_invoice, pay_invoice
from lnbits.settings import settings

from .crud import (
    get_flow_mode_clients,
    get_payments_by_lamassu_transaction,
    create_dca_payment,
    get_client_balance_summary,
    get_active_lamassu_config,
    update_config_test_result
)
from .models import CreateDcaPaymentData, LamassuTransaction


class LamassuTransactionProcessor:
    """Handles polling Lamassu database and processing transactions for DCA distribution"""
    
    def __init__(self):
        self.last_check_time = None
        self.processed_transaction_ids = set()
        self.ssh_process = None
        self.ssh_key_path = None
    
    async def get_db_config(self) -> Optional[Dict[str, Any]]:
        """Get database configuration from the database"""
        try:
            config = await get_active_lamassu_config()
            if not config:
                logger.error("No active Lamassu database configuration found")
                return None
            
            return {
                "host": config.host,
                "port": config.port,
                "database": config.database_name,
                "user": config.username,
                "password": config.password,
                "config_id": config.id,
                "use_ssh_tunnel": config.use_ssh_tunnel,
                "ssh_host": config.ssh_host,
                "ssh_port": config.ssh_port,
                "ssh_username": config.ssh_username,
                "ssh_password": config.ssh_password,
                "ssh_private_key": config.ssh_private_key
            }
        except Exception as e:
            logger.error(f"Error getting database configuration: {e}")
            return None
    
    def setup_ssh_tunnel(self, db_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Setup SSH tunnel if required and return modified connection config"""
        if not db_config.get("use_ssh_tunnel"):
            return db_config
            
        if not SSH_AVAILABLE:
            logger.error("SSH tunnel requested but SSH libraries not available")
            return None
            
        try:
            # Close existing tunnel if any
            self.close_ssh_tunnel()
            
            # Use subprocess-based SSH tunnel as fallback
            return self._setup_subprocess_ssh_tunnel(db_config)
            
        except Exception as e:
            logger.error(f"Failed to setup SSH tunnel: {e}")
            self.close_ssh_tunnel()
            return None
    
    def _setup_subprocess_ssh_tunnel(self, db_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Setup SSH tunnel using subprocess (compatible with all environments)"""
        import subprocess
        import socket
        
        # Find an available local port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            local_port = s.getsockname()[1]
        
        # Build SSH command
        ssh_cmd = [
            "ssh",
            "-N",  # Don't execute remote command
            "-L", f"{local_port}:{db_config['host']}:{db_config['port']}",
            f"{db_config['ssh_username']}@{db_config['ssh_host']}",
            "-p", str(db_config['ssh_port']),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR"
        ]
        
        # Add authentication method
        if db_config.get("ssh_password"):
            # Check if sshpass is available for password authentication
            try:
                import subprocess
                subprocess.run(["which", "sshpass"], check=True, capture_output=True)
                ssh_cmd = ["sshpass", "-p", db_config["ssh_password"]] + ssh_cmd
            except subprocess.CalledProcessError:
                logger.error("Password authentication requires 'sshpass' tool which is not installed. Please use SSH key authentication instead.")
                return None
        elif db_config.get("ssh_private_key"):
            # Write private key to temporary file
            import tempfile
            import os
            key_fd, key_path = tempfile.mkstemp(suffix='.pem')
            try:
                with os.fdopen(key_fd, 'w') as f:
                    f.write(db_config["ssh_private_key"])
                os.chmod(key_path, 0o600)
                ssh_cmd.extend(["-i", key_path])
                self.ssh_key_path = key_path  # Store for cleanup
            except Exception as e:
                os.unlink(key_path)
                raise e
        else:
            logger.error("SSH tunnel requires either private key or password")
            return None
        
        # Start SSH tunnel process
        try:
            self.ssh_process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            
            # Wait a moment for tunnel to establish
            import time
            time.sleep(2)
            
            # Check if process is still running
            if self.ssh_process.poll() is not None:
                raise Exception("SSH tunnel process terminated immediately")
            
            logger.info(f"SSH tunnel established: localhost:{local_port} -> {db_config['ssh_host']}:{db_config['ssh_port']} -> {db_config['host']}:{db_config['port']}")
            
            # Return modified config to connect through tunnel
            tunnel_config = db_config.copy()
            tunnel_config["host"] = "127.0.0.1"
            tunnel_config["port"] = local_port
            
            return tunnel_config
            
        except FileNotFoundError:
            logger.error("SSH command not found. SSH tunneling requires ssh (and sshpass for password auth) to be installed on the system.")
            return None
        except Exception as e:
            logger.error(f"Failed to establish SSH tunnel: {e}")
            return None
    
    def close_ssh_tunnel(self):
        """Close SSH tunnel if active"""
        # Close subprocess-based tunnel
        if hasattr(self, 'ssh_process') and self.ssh_process:
            try:
                self.ssh_process.terminate()
                self.ssh_process.wait(timeout=5)
                logger.info("SSH tunnel process closed")
            except Exception as e:
                logger.warning(f"Error closing SSH tunnel process: {e}")
                try:
                    self.ssh_process.kill()
                except:
                    pass
            finally:
                self.ssh_process = None
        
        # Clean up temporary key file if exists
        if hasattr(self, 'ssh_key_path') and self.ssh_key_path:
            try:
                import os
                os.unlink(self.ssh_key_path)
                logger.info("SSH key file cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up SSH key file: {e}")
            finally:
                self.ssh_key_path = None
    
    async def test_connection_detailed(self) -> Dict[str, Any]:
        """Test connection with detailed step-by-step reporting"""
        result = {
            "success": False,
            "message": "",
            "steps": [],
            "ssh_tunnel_used": False,
            "ssh_tunnel_success": False,
            "database_connection_success": False,
            "config_id": None
        }
        
        try:
            # Step 1: Get configuration
            result["steps"].append("Retrieving database configuration...")
            db_config = await self.get_db_config()
            if not db_config:
                result["message"] = "No active Lamassu database configuration found"
                result["steps"].append("❌ No configuration found")
                return result
                
            result["config_id"] = db_config["config_id"]
            result["steps"].append("✅ Configuration retrieved")
            
            # Step 2: SSH Tunnel setup (if required)
            if db_config.get("use_ssh_tunnel"):
                result["ssh_tunnel_used"] = True
                result["steps"].append("Setting up SSH tunnel...")
                
                if not SSH_AVAILABLE:
                    result["message"] = "SSH tunnel required but SSH support not available"
                    result["steps"].append("❌ SSH support missing (requires ssh command line tool)")
                    return result
                
                connection_config = self.setup_ssh_tunnel(db_config)
                if not connection_config:
                    result["message"] = "Failed to establish SSH tunnel"
                    result["steps"].append("❌ SSH tunnel failed - check SSH credentials and server accessibility")
                    return result
                    
                result["ssh_tunnel_success"] = True
                result["steps"].append(f"✅ SSH tunnel established to {db_config['ssh_host']}:{db_config['ssh_port']}")
            else:
                connection_config = db_config
                result["steps"].append("ℹ️  Direct database connection (no SSH tunnel)")
            
            # Step 3: Database connection
            result["steps"].append("Connecting to Postgres database...")
            connection = await asyncpg.connect(
                host=connection_config["host"],
                port=connection_config["port"],
                database=connection_config["database"],
                user=connection_config["user"],
                password=connection_config["password"],
                timeout=30
            )
            
            result["database_connection_success"] = True
            result["steps"].append("✅ Database connection successful")
            
            # Step 4: Test query
            result["steps"].append("Testing database query...")
            test_query = "SELECT 1 as test"
            await connection.fetchval(test_query)
            result["steps"].append("✅ Database query test successful")
            
            # Step 5: Test actual table access
            result["steps"].append("Testing access to cash_out_txs table...")
            table_query = "SELECT COUNT(*) FROM cash_out_txs LIMIT 1"
            count = await connection.fetchval(table_query)
            result["steps"].append(f"✅ Table access successful (found {count} transactions)")
            
            await connection.close()
            result["success"] = True
            result["message"] = "All connection tests passed successfully"
            
        except asyncpg.InvalidCatalogNameError:
            result["message"] = "Database not found - check database name"
            result["steps"].append("❌ Database does not exist")
        except asyncpg.InvalidPasswordError:
            result["message"] = "Authentication failed - check username/password"
            result["steps"].append("❌ Invalid database credentials")
        except asyncpg.CannotConnectNowError:
            result["message"] = "Database server not accepting connections"
            result["steps"].append("❌ Database server unavailable")
        except asyncpg.ConnectionDoesNotExistError:
            result["message"] = "Cannot connect to database server"
            result["steps"].append("❌ Cannot reach database server")
        except Exception as e:
            error_msg = str(e)
            if "cash_out_txs" in error_msg:
                result["message"] = "Connected to database but cash_out_txs table not found"
                result["steps"].append("❌ Lamassu transaction table missing")
            elif "paramiko" in error_msg.lower() or "ssh" in error_msg.lower():
                result["message"] = f"SSH tunnel error: {error_msg}"
                result["steps"].append(f"❌ SSH error: {error_msg}")
            else:
                result["message"] = f"Connection test failed: {error_msg}"
                result["steps"].append(f"❌ Unexpected error: {error_msg}")
        finally:
            # Always cleanup SSH tunnel
            self.close_ssh_tunnel()
            
        # Update test result in database
        if result["config_id"]:
            try:
                await update_config_test_result(result["config_id"], result["success"])
            except Exception as e:
                logger.warning(f"Could not update config test result: {e}")
        
        return result
    
    async def connect_to_lamassu_db(self) -> Optional[asyncpg.Connection]:
        """Establish connection to Lamassu Postgres database"""
        try:
            db_config = await self.get_db_config()
            if not db_config:
                return None
            
            # Setup SSH tunnel if required
            connection_config = self.setup_ssh_tunnel(db_config)
            if not connection_config:
                return None
            
            connection = await asyncpg.connect(
                host=connection_config["host"],
                port=connection_config["port"],
                database=connection_config["database"],
                user=connection_config["user"],
                password=connection_config["password"],
                timeout=30
            )
            logger.info("Successfully connected to Lamassu database")
            
            # Update test result on successful connection
            try:
                await update_config_test_result(db_config["config_id"], True)
            except Exception as e:
                logger.warning(f"Could not update config test result: {e}")
            
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to Lamassu database: {e}")
            
            # Update test result on failed connection
            try:
                db_config = await self.get_db_config()
                if db_config:
                    await update_config_test_result(db_config["config_id"], False)
            except Exception as update_error:
                logger.warning(f"Could not update config test result: {update_error}")
            
            return None
    
    async def fetch_new_transactions(self, connection: asyncpg.Connection) -> List[Dict[str, Any]]:
        """Fetch new successful transactions from Lamassu database"""
        try:
            # Set the time window - check for transactions in the last hour + 5 minutes buffer
            time_threshold = datetime.now() - timedelta(hours=1, minutes=5)
            
            # Query for successful cash-out transactions (people selling BTC for fiat)
            # These are the transactions that trigger DCA distributions
            query = """
            SELECT 
                co.id as transaction_id,
                co.fiat as fiat_amount,
                co.crypto as crypto_amount,
                co.created as transaction_time,
                co.session_id,
                co.machine_id,
                co.status,
                co.commission_percentage,
                co.tx_hash
            FROM cash_out_txs co
            WHERE co.created >= $1 
                AND co.status = 'confirmed'
                AND co.id NOT IN (
                    -- Exclude already processed transactions
                    SELECT DISTINCT lamassu_transaction_id 
                    FROM myextension.dca_payments 
                    WHERE lamassu_transaction_id IS NOT NULL
                )
            ORDER BY co.created DESC
            """
            
            rows = await connection.fetch(query, time_threshold)
            
            transactions = []
            for row in rows:
                # Convert asyncpg.Record to dict
                transaction = {
                    "transaction_id": str(row["transaction_id"]),
                    "fiat_amount": int(row["fiat_amount"]),  # Amount in smallest currency unit
                    "crypto_amount": int(row["crypto_amount"]),  # Amount in satoshis
                    "transaction_time": row["transaction_time"],
                    "session_id": row["session_id"],
                    "machine_id": row["machine_id"],
                    "status": row["status"],
                    "commission_percentage": float(row["commission_percentage"]) if row["commission_percentage"] else 0.0,
                    "tx_hash": row["tx_hash"]
                }
                transactions.append(transaction)
            
            logger.info(f"Found {len(transactions)} new transactions to process")
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching transactions from Lamassu database: {e}")
            return []
    
    async def calculate_distribution_amounts(self, transaction: Dict[str, Any]) -> Dict[str, int]:
        """Calculate how much each Flow Mode client should receive"""
        try:
            # Get all active Flow Mode clients
            flow_clients = await get_flow_mode_clients()
            
            if not flow_clients:
                logger.info("No Flow Mode clients found - skipping distribution")
                return {}
            
            # Calculate principal amount (total - commission)
            fiat_amount = transaction["fiat_amount"]
            commission_percentage = transaction["commission_percentage"]
            commission_amount = int(fiat_amount * commission_percentage / 100)
            principal_amount = fiat_amount - commission_amount
            
            logger.info(f"Transaction: {fiat_amount}, Commission: {commission_amount}, Principal: {principal_amount}")
            
            # Get balance summaries for all clients to calculate proportions
            client_balances = {}
            total_confirmed_deposits = 0
            
            for client in flow_clients:
                balance = await get_client_balance_summary(client.id)
                if balance.remaining_balance > 0:  # Only include clients with remaining balance
                    client_balances[client.id] = balance.remaining_balance
                    total_confirmed_deposits += balance.remaining_balance
            
            if total_confirmed_deposits == 0:
                logger.info("No clients with remaining DCA balance - skipping distribution")
                return {}
            
            # Calculate proportional distribution
            distributions = {}
            exchange_rate = transaction["crypto_amount"] / transaction["fiat_amount"]  # sats per fiat unit
            
            for client_id, client_balance in client_balances.items():
                # Calculate this client's proportion of the principal
                proportion = client_balance / total_confirmed_deposits
                client_fiat_amount = int(principal_amount * proportion)
                client_sats_amount = int(client_fiat_amount * exchange_rate)
                
                distributions[client_id] = {
                    "fiat_amount": client_fiat_amount,
                    "sats_amount": client_sats_amount,
                    "exchange_rate": exchange_rate
                }
                
                logger.info(f"Client {client_id[:8]}... gets {client_fiat_amount} fiat units = {client_sats_amount} sats")
            
            return distributions
            
        except Exception as e:
            logger.error(f"Error calculating distribution amounts: {e}")
            return {}
    
    async def distribute_to_clients(self, transaction: Dict[str, Any], distributions: Dict[str, Dict[str, int]]) -> None:
        """Send Bitcoin payments to DCA clients"""
        try:
            transaction_id = transaction["transaction_id"]
            
            for client_id, distribution in distributions.items():
                try:
                    # Get client info
                    flow_clients = await get_flow_mode_clients()
                    client = next((c for c in flow_clients if c.id == client_id), None)
                    
                    if not client:
                        logger.error(f"Client {client_id} not found")
                        continue
                    
                    # Create DCA payment record
                    payment_data = CreateDcaPaymentData(
                        client_id=client_id,
                        amount_sats=distribution["sats_amount"],
                        amount_fiat=distribution["fiat_amount"],
                        exchange_rate=distribution["exchange_rate"],
                        transaction_type="flow",
                        lamassu_transaction_id=transaction_id
                    )
                    
                    # Record the payment in our database
                    dca_payment = await create_dca_payment(payment_data)
                    
                    # TODO: Actually send Bitcoin to client's wallet
                    # This will be implemented when we integrate with LNBits payment system
                    logger.info(f"DCA payment recorded for client {client_id[:8]}...: {distribution['sats_amount']} sats")
                    
                except Exception as e:
                    logger.error(f"Error processing distribution for client {client_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error distributing to clients: {e}")
    
    async def process_transaction(self, transaction: Dict[str, Any]) -> None:
        """Process a single transaction - calculate and distribute DCA payments"""
        try:
            transaction_id = transaction["transaction_id"]
            
            # Check if transaction already processed
            existing_payments = await get_payments_by_lamassu_transaction(transaction_id)
            if existing_payments:
                logger.info(f"Transaction {transaction_id} already processed - skipping")
                return
            
            logger.info(f"Processing new transaction: {transaction_id}")
            
            # Calculate distribution amounts
            distributions = await self.calculate_distribution_amounts(transaction)
            
            if not distributions:
                logger.info(f"No distributions calculated for transaction {transaction_id}")
                return
            
            # Distribute to clients
            await self.distribute_to_clients(transaction, distributions)
            
            logger.info(f"Successfully processed transaction {transaction_id}")
            
        except Exception as e:
            logger.error(f"Error processing transaction {transaction.get('transaction_id', 'unknown')}: {e}")
    
    async def poll_and_process(self) -> None:
        """Main polling function - checks for new transactions and processes them"""
        try:
            logger.info("Starting Lamassu transaction polling...")
            
            # Connect to Lamassu database
            connection = await self.connect_to_lamassu_db()
            if not connection:
                logger.error("Could not connect to Lamassu database - skipping this poll")
                return
            
            try:
                # Fetch new transactions
                new_transactions = await self.fetch_new_transactions(connection)
                
                # Process each transaction
                for transaction in new_transactions:
                    await self.process_transaction(transaction)
                
                logger.info(f"Completed processing {len(new_transactions)} transactions")
                
            finally:
                await connection.close()
                # Close SSH tunnel if it was used
                self.close_ssh_tunnel()
                
        except Exception as e:
            logger.error(f"Error in polling cycle: {e}")
            # Ensure cleanup on error
            self.close_ssh_tunnel()


# Global processor instance
transaction_processor = LamassuTransactionProcessor()


async def poll_lamassu_transactions() -> None:
    """Entry point for the polling task"""
    await transaction_processor.poll_and_process()