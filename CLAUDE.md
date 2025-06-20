# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LNBits extension called "satoshimachine" (currently using template name "SatMachineAdmin"). LNBits extensions are modular add-ons that extend the functionality of the LNBits Lightning Network wallet platform.

## Development Commands

### Code Quality & Formatting
```bash
# Format all code
make format

# Check code quality
make check

# Individual commands
poetry run black .                    # Python formatting
poetry run ruff check . --fix         # Python linting with auto-fix
poetry run ./node_modules/.bin/prettier --write .  # JavaScript formatting
poetry run mypy .                     # Python type checking
poetry run ./node_modules/.bin/pyright # JavaScript type checking
```

### Testing
```bash
# Run tests
make test
# or
PYTHONUNBUFFERED=1 DEBUG=true poetry run pytest
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
make install-pre-commit-hook

# Run pre-commit on all files
make pre-commit
```

## Architecture

### Core Structure
LNBits extensions follow a specific FastAPI + Vue.js architecture:

- **Backend (Python/FastAPI)**:
  - `__init__.py` - Extension initialization and router setup
  - `models.py` - Pydantic data models
  - `crud.py` - Database operations
  - `views.py` - Frontend page routes
  - `views_api.py` - API endpoints
  - `views_lnurl.py` - LNURL protocol handlers
  - `migrations.py` - Database schema changes
  - `tasks.py` - Background tasks
  - `helpers.py` - Utility functions

- **Frontend (Vue.js 3 Options API + Quasar)**:
  - `static/js/index.js` - Main Vue app
  - `static/js/components/` - Vue components
  - `templates/` - HTML templates with Jinja2

### Key Conventions

1. **Template Syntax Rules**:
   - Use `{{ }}` and `{% %}` ONLY in `index.html` files (Jinja2)
   - In Vue components: Use `v-text='value'` instead of `{{ value }}`
   - Use `:attribute='value'` for binding, `v-html='value'` for HTML content

2. **API Patterns**:
   - Always include wallet key (inkey/adminkey) as third parameter in API calls
   - Use `LNbits.api.request()` for all API calls
   - Destructure responses: `const {data} = await LNbits.api.request(...)`

3. **Component Registration**:
   - Templates must be included BEFORE scripts in HTML
   - Components must be registered BEFORE app.mount()

### The Magical G Object
The global `this.g` object provides access to:
- `this.g.user` - Complete user data including wallets array
- `this.g.user.wallets[0].inkey` - Invoice key for API calls
- `this.g.user.wallets[0].adminkey` - Admin key for privileged operations
- `this.g.wallet` - Currently selected wallet

### Built-in Utilities
- Currency conversion: `/api/v1/currencies`, `/api/v1/conversion`
- QR code generation: `/api/v1/qrcode/{data}` or Quasar VueQrcode component
- WebSocket support: `wss://host/api/v1/ws/{id}` with POST to `/api/v1/ws/{id}/{data}`

## Configuration Files

- `config.json` - Extension configuration
- `manifest.json` - Extension manifest for installation
- `pyproject.toml` - Python dependencies and tool configuration
- `package.json` - JavaScript dependencies

## Important Notes

- This extension is currently a template with placeholder "SatMachineAdmin" naming
- The actual functionality appears to be related to "satoshimachine" based on directory structure
- The `tmp/` directory contains a more developed version with DCA (Dollar Cost Averaging) functionality
- Extensions must follow snake_case naming conventions for Python files
- Use Quasar components (QBtn, QInput, QSelect, etc.) for UI consistency
- Always implement proper loading states and error handling with `LNbits.utils.notifyApiError(error)`

## DCA System Development Progress

### ✅ Completed Features

#### **1. SSH-Based Database Polling System**
- Implemented secure SSH connection to remote Lamassu PostgreSQL database
- Uses subprocess-based SSH tunneling (no external Python dependencies required)
- Connects as `postgres` user with SSH key authentication
- Supports both password and private key SSH authentication
- Proper SSH tunnel cleanup and error handling

#### **2. Transaction Processing Pipeline**
- Fetches new cash-out transactions from Lamassu `cash_out_txs` table
- Correctly handles commission calculation with discount support
- Formula: `base_crypto_atoms = crypto_atoms / (1 + effective_commission)`
- Effective commission: `commission_percentage * (100 - discount) / 100`
- Timezone-aware processing using UTC timestamps

#### **3. Smart Poll Tracking**
- Tracks `last_poll_time` and `last_successful_poll` in database
- Prevents missed transactions during server downtime
- First run checks last 24 hours, subsequent runs check since last successful poll
- Proper error handling that doesn't update success time on failures

#### **4. DCA Client Management**
- Full CRUD operations for DCA clients
- Added username support for better UX (shows "johndoe" instead of "a1b2c3d4...")
- Client balance tracking and proportional distribution calculation
- Support for both Flow Mode and Fixed Mode DCA strategies

#### **5. Admin Interface**
- Connection testing with detailed step-by-step reporting
- Manual poll triggers for immediate transaction processing
- Real-time poll status display with timestamps
- Username-based client selection in forms and tables
- Export functionality for clients and deposits data

#### **6. Database Schema**
- Complete migration system (m001-m009)
- DCA clients table with username field
- DCA deposits and payments tracking
- Lamassu configuration with SSH settings
- Poll tracking timestamps

### 🚧 Current State

#### **What Works:**
- ✅ SSH connection to Lamassu database
- ✅ Transaction detection and fetching
- ✅ Commission calculation (with discounts)
- ✅ Proportional distribution calculation
- ✅ Payment record creation in database
- ✅ Admin interface for monitoring and management

#### **Database Fields Used:**
- `crypto_atoms` - Total satoshis with commission baked in
- `fiat` - Actual fiat dispensed (commission-free amount)
- `commission_percentage` - Stored as decimal (e.g., 0.045 for 4.5%)
- `discount` - Discount percentage applied to commission

### 📋 Next Steps / TODO

#### **1. Actual Bitcoin Payment Implementation**
- Currently only records payments in database (line 572-573 in `transaction_processor.py`)
- Need to implement actual Bitcoin transfers to client wallets
- Integrate with LNBits payment system
- Handle client wallet addresses/invoices

#### **2. Payment Status Tracking**
- Track payment states: pending → confirmed → failed
- Implement retry logic for failed payments
- Payment confirmation and error handling

#### **3. Client Wallet Integration**
- Store client wallet addresses or Lightning invoices
- Implement payment delivery mechanisms
- Handle different payment methods (on-chain, Lightning, etc.)

### 🔧 Technical Implementation Details

#### **SSH Connection Setup:**
```bash
# On Lamassu server:
sudo mkdir -p /var/lib/postgresql/.ssh
sudo echo "your-public-key" >> /var/lib/postgresql/.ssh/authorized_keys
sudo chown -R postgres:postgres /var/lib/postgresql/.ssh
sudo chmod 700 /var/lib/postgresql/.ssh
sudo chmod 600 /var/lib/postgresql/.ssh/authorized_keys
```

#### **Configuration:**
- Database: `lamassu` on postgres user
- SSH: Direct connection as postgres user (no tunneling complexity)
- Polling: Hourly automatic + manual trigger available
- Security: SSH key authentication, read-only database access

### 🐛 Known Considerations

- Commission calculation uses `crypto_atoms / (1 + effective_commission)` not `crypto_atoms * commission`
- Database stores commission as decimal (0.045) not percentage (4.5)
- Username field is optional for backward compatibility
- Timezone handling standardized to UTC throughout system
- SSH requires system `ssh` command (standard on Linux servers)

### 📁 Key Files

- `transaction_processor.py` - Main polling and processing logic
- `models.py` - Data models with commission calculation
- `crud.py` - Database operations including poll tracking
- `migrations.py` - Schema evolution (m001-m009)
- `static/js/index.js` - Admin interface JavaScript
- `templates/satmachineadmin/index.html` - Admin UI templates