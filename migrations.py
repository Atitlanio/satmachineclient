# the migration file is where you build your database tables
# If you create a new release for your extension ,
# remember the migration file is like a blockchain, never edit only add!


async def m001_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE myextension.maintable (
            id TEXT PRIMARY KEY NOT NULL,
            wallet TEXT NOT NULL,
            name TEXT NOT NULL,
            total INTEGER DEFAULT 0,
            lnurlpayamount INTEGER DEFAULT 0,
            lnurlwithdrawamount INTEGER DEFAULT 0
        );
    """
    )


async def m002_add_timestamp(db):
    """
    Add timestamp to templates table.
    """
    await db.execute(
        f"""
        ALTER TABLE myextension.maintable
        ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now};
    """
    )


async def m003_create_dca_clients(db):
    """
    Create DCA clients table.
    """
    await db.execute(
        f"""
        CREATE TABLE myextension.dca_clients (
            id TEXT PRIMARY KEY NOT NULL,
            user_id TEXT NOT NULL,
            wallet_id TEXT NOT NULL,
            dca_mode TEXT NOT NULL DEFAULT 'flow',
            fixed_mode_daily_limit INTEGER,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )


async def m004_create_dca_deposits(db):
    """
    Create DCA deposits table.
    """
    await db.execute(
        f"""
        CREATE TABLE myextension.dca_deposits (
            id TEXT PRIMARY KEY NOT NULL,
            client_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'GTQ',
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            confirmed_at TIMESTAMP
        );
        """
    )


async def m005_create_dca_payments(db):
    """
    Create DCA payments table.
    """
    await db.execute(
        f"""
        CREATE TABLE myextension.dca_payments (
            id TEXT PRIMARY KEY NOT NULL,
            client_id TEXT NOT NULL,
            amount_sats INTEGER NOT NULL,
            amount_fiat INTEGER NOT NULL,
            exchange_rate REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            lamassu_transaction_id TEXT,
            payment_hash TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )


async def m006_create_lamassu_config(db):
    """
    Create Lamassu database configuration table.
    """
    await db.execute(
        f"""
        CREATE TABLE myextension.lamassu_config (
            id TEXT PRIMARY KEY NOT NULL,
            host TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 5432,
            database_name TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            test_connection_last TIMESTAMP,
            test_connection_success BOOLEAN,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )


async def m007_add_ssh_tunnel_support(db):
    """
    Add SSH tunnel support to Lamassu configuration table.
    """
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN use_ssh_tunnel BOOLEAN NOT NULL DEFAULT false;
        """
    )
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN ssh_host TEXT;
        """
    )
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN ssh_port INTEGER NOT NULL DEFAULT 22;
        """
    )
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN ssh_username TEXT;
        """
    )
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN ssh_password TEXT;
        """
    )
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN ssh_private_key TEXT;
        """
    )


async def m008_add_last_poll_tracking(db):
    """
    Add last poll time tracking to Lamassu configuration table.
    """
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN last_poll_time TIMESTAMP;
        """
    )
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN last_successful_poll TIMESTAMP;
        """
    )


async def m009_add_username_to_dca_clients(db):
    """
    Add username field to DCA clients table for better user experience.
    """
    await db.execute(
        """
        ALTER TABLE myextension.dca_clients 
        ADD COLUMN username TEXT;
        """
    )


async def m010_add_source_wallet_to_lamassu_config(db):
    """
    Add source wallet ID to Lamassu configuration table for DCA distributions.
    """
    await db.execute(
        """
        ALTER TABLE myextension.lamassu_config 
        ADD COLUMN source_wallet_id TEXT;
        """
    )
