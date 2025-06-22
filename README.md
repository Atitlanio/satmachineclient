# DCA Client Extension for LNBits

A Dollar Cost Averaging (DCA) administration extension for LNBits that integrates with Lamassu ATM machines to automatically distribute Bitcoin to registered clients based on their deposit balances.

## Overview

This extension enables automated Bitcoin distribution from Lamassu ATM transactions to DCA clients. When customers use a Lamassu ATM to purchase Bitcoin, the system automatically distributes the purchased amount (minus commission) proportionally to clients who have active DCA balances.

## Features

### 🏦 DCA Client Management
- View all registered DCA clients from the client extension
- Monitor client balances and deposit history
- Support for both "flow" and "fixed" DCA modes
- Real-time balance tracking with remaining amounts

### 💰 Deposit Management
- Quick deposit creation for existing clients
- Individual deposit confirmation workflow
- Status tracking (pending/confirmed)
- Notes and documentation for each deposit

### 🔄 Lamassu ATM Integration
- Real-time polling of Lamassu database transactions
- Secure SSH tunnel support for database access
- Automatic commission calculation and handling
- Proportional distribution to active DCA clients

### 📊 Transaction Audit Trail
- Complete record of all processed Lamassu transactions
- Clickable transaction details showing exact distribution breakdown
- Commission tracking with discount support
- Export capabilities for all data

### ⚙️ Configuration Management
- Secure database connection configuration
- Source wallet selection for Bitcoin distributions
- Commission wallet configuration for earnings
- SSH tunnel setup for secure remote access

## Installation

1. Copy this extension to your LNBits extensions directory
2. Enable the extension in LNBits admin panel
3. Install the companion DCA client extension for end-users

## Configuration

### Database Setup

1. **Configure Lamassu Database Connection**
   - Navigate to the DCA Client extension
   - Click "Configure Database" in the sidebar
   - Enter your Lamassu PostgreSQL connection details:
     - Host and port
     - Database name (usually "lamassu")
     - Username and password
   - Select source wallet for Bitcoin distributions
   - Optionally select commission wallet for earnings

2. **SSH Tunnel (Recommended)**
   - Enable SSH tunnel for secure database access
   - Provide SSH server details and authentication
   - Supports both password and private key authentication

3. **Test Connection**
   - Use the "Test Connection" button to verify setup
   - Check SSH tunnel and database connectivity

### Wallet Configuration

- **Source Wallet**: Must contain sufficient Bitcoin for distributions
- **Commission Wallet**: Optional separate wallet for commission earnings
- Wallets are automatically credited with Lamassu transaction amounts

## Usage

### For Administrators

1. **Client Registration**
   - Clients register using the DCA client extension
   - Admins can view all registered clients in the admin panel

2. **Deposit Management**
   - Add deposits for clients when they provide fiat currency
   - Confirm deposits once money is physically placed in ATM
   - Track deposit status and client balances

3. **Transaction Processing**
   - System automatically polls Lamassu database hourly
   - Manual polling available for immediate processing
   - Test transaction feature for system validation

4. **Monitoring**
   - View all processed transactions with full audit trail
   - Click transactions to see distribution details
   - Export data for accounting and compliance

### For End Users (DCA Client Extension)

1. **Registration**
   - Install DCA client extension
   - Choose DCA mode (flow or fixed)
   - Make initial deposit with administrator

2. **DCA Modes**
   - **Flow Mode**: Receives proportional share of all transactions
   - **Fixed Mode**: Receives up to daily limit from transactions

## Technical Details

### Architecture

- **Backend**: FastAPI with PostgreSQL database
- **Frontend**: Vue.js 3 with Quasar UI components
- **Database**: Extends LNBits database with dedicated tables
- **Integration**: Direct PostgreSQL connection to Lamassu database

### Database Schema

The extension creates several tables:
- `dca_clients`: Registered DCA users
- `dca_deposits`: Client deposit tracking
- `dca_payments`: Individual Bitcoin distributions
- `lamassu_config`: Database connection settings
- `lamassu_transactions`: Processed ATM transaction audit trail

### Security

- SSH tunnel support for secure database access
- Encrypted storage of database credentials
- Read-only access to Lamassu database
- Internal LNBits payment system for Bitcoin distributions

### Commission Handling

- Configurable commission percentage from Lamassu
- Discount support for promotional rates
- Automatic commission calculation: `base_amount = total / (1 + commission_rate)`
- Separate wallet option for commission earnings

## API Endpoints

### DCA Clients
- `GET /api/v1/dca/clients` - List all clients
- `GET /api/v1/dca/clients/{id}/balance` - Get client balance
- `POST /api/v1/dca/clients` - Create test client (dev only)

### Deposits
- `GET /api/v1/dca/deposits` - List all deposits
- `POST /api/v1/dca/deposits` - Create new deposit
- `PUT /api/v1/dca/deposits/{id}/status` - Update deposit status

### Transactions
- `GET /api/v1/dca/transactions` - List processed transactions
- `GET /api/v1/dca/transactions/{id}/distributions` - Get distribution details

### Configuration
- `GET /api/v1/dca/config` - Get database configuration
- `POST /api/v1/dca/config` - Create/update configuration
- `POST /api/v1/dca/test-connection` - Test database connection

### Operations
- `POST /api/v1/dca/manual-poll` - Trigger manual polling
- `POST /api/v1/dca/test-transaction` - Process test transaction

## Development

### Setup Development Environment

1. Clone LNBits and this extension
2. Install dependencies: `poetry install`
3. Set up test Lamassu database or use test mode
4. Configure SSH tunnel for development access

### Code Structure

```
├── README.md                 # This file
├── __init__.py              # Extension initialization
├── models.py                # Pydantic data models
├── crud.py                  # Database operations
├── views.py                 # Frontend page routes
├── views_api.py             # API endpoints
├── migrations.py            # Database migrations
├── transaction_processor.py # Lamassu integration
├── helpers.py               # Utility functions
├── config.json              # Extension configuration
├── manifest.json            # Extension manifest
├── templates/
│   └── satmachineclient/
│       └── index.html       # Main UI template
└── static/
    └── js/
        └── index.js         # Frontend JavaScript
```

### Testing

- Use "Test Connection" to verify Lamassu database access
- Use "Test Transaction" to simulate ATM transaction processing
- Monitor logs for debugging transaction processing
- Test SSH tunnel connectivity independently

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify SSH credentials and host accessibility
   - Check SSH key permissions (600 for private keys)
   - Ensure SSH server allows database user connections

2. **Database Connection Failed**
   - Verify PostgreSQL connection details
   - Check database user permissions (SELECT access required)
   - Confirm database name and schema

3. **No Transactions Found**
   - Check Lamassu database for recent transactions
   - Verify transaction polling timestamps
   - Review database query filters

4. **Distribution Errors**
   - Ensure source wallet has sufficient balance
   - Check client deposit confirmations
   - Verify wallet configuration

### Debugging

- Enable debug logging: `DEBUG=true`
- Check LNBits logs for transaction processing
- Use manual polling to test individual transactions
- Verify database queries with SSH tunnel

## Security Considerations

- Use SSH tunnels for production database access
- Regularly rotate database credentials
- Monitor transaction processing logs
- Implement proper backup procedures
- Use read-only database access where possible

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review LNBits extension documentation
3. Check connection test results for specific errors
4. Monitor system logs for detailed error messages

## License

This extension follows the same license as LNBits.

---

**Note**: This extension requires the companion DCA client extension for end-users to register and participate in the DCA program.