# DCA System Implementation Plan

## Current State
- **Base Extension**: SatoshiMachine (template extension)
- **Structure**: Complete LNBits extension with all necessary files
- **Status**: Ready to be overwritten with DCA functionality

## Updated System Design Based on Clarifications

### 1. Data Integration Solution - CSV Fetch Approach

**Implementation**: Admin extension will fetch CSV data using the provided bash script pattern:
- Execute SSH commands to export transaction data from Lamassu server
- Download CSV files: `cash_out_txs.csv`, `cash_in_txs.csv`, `cash_out_actions.csv`
- Process CSV data to identify new successful transactions
- Alternative: Direct Postgres connection (read-only) for real-time processing

**Benefits**:
- Secure (read-only access)
- Reliable data export from Lamassu
- Network security through SSH

### 2. Proportional Distribution Logic (CLARIFIED)

**Flow Mode Distribution**:
```python
# Example: Client A: 9,000 GTQ, Client B: 1,000 GTQ (Total: 10,000 GTQ)
# New transaction: 2,000 GTQ principal after commission

client_a_share = (9000 / 10000) * 2000 = 1800 GTQ worth of BTC
client_b_share = (1000 / 10000) * 2000 = 200 GTQ worth of BTC

# Convert to satoshis using transaction exchange rate
client_a_sats = 1800 * (crypto_atoms / fiat_amount)
client_b_sats = 200 * (crypto_atoms / fiat_amount)
```

### 3. System Architecture - Shared Database Approach

**Admin Extension** (Primary):
- Hosts all data models and business logic
- Processes transaction data (CSV/Postgres)
- Manages DCA distributions
- Provides internal API endpoints
- **Must be active** for system to function

**Client Extension** (Interface):
- User-facing dashboard
- Calls admin extension's internal APIs
- No direct database access
- Lightweight interface layer

### 4. Fixed Mode Configuration

**System-Wide Settings**:
- Admin configures Fixed Mode timing globally
- Maximum daily limit: **2000 GTQ per client**
- Insufficient funds handling: LNBits wallet "top-up" or Nostr notification

### 5. Authentication & User Mapping

**Client Identification**:
- User selects DCA wallet in client extension (standard LNBits pattern)
- Wallet cannot be changed after initiation (maintains transaction integrity)
- Admin manually adds clients using `user_id` + deposit amount
- No separate registration process required

### 6. Real-Time Updates Strategy

**Recommended Approach**: **Polling-based** for this use case
- Client dashboard polls admin APIs every 30-60 seconds
- Lower complexity than WebSocket for this scenario
- Sufficient responsiveness for DCA monitoring
- LNBits handles actual payment notifications

## Implementation Architecture

### Phase 1: Admin Extension (Core System)
1. **Database Models**:
   - DCA clients and deposits
   - Transaction processing tracking
   - Commission distribution configuration
   - Distribution history

2. **Transaction Processing**:
   - CSV data fetching and parsing
   - Duplicate detection using transaction IDs
   - Flow Mode distribution calculations
   - Commission distribution system

3. **Admin Interface**:
   - Client management dashboard
   - Transaction monitoring
   - Commission distribution configuration
   - System health monitoring

### Phase 2: Client Extension (User Interface)
1. **Dashboard Components**:
   - DCA overview and metrics
   - Transaction history
   - Settings management
   - Performance analytics

2. **API Integration**:
   - Read-only access to admin extension APIs
   - Real-time balance and status updates
   - Settings synchronization

## Technical Specifications

### Data Flow
```
Lamassu ATM → CSV Export → Admin Extension → Process & Distribute → Client Extensions Display
```

### Security Model
- Admin extension: Full database access, transaction processing
- Client extension: Read-only API access, user-specific data only
- CSV/SSH: Secure remote data fetching with credentials management

### Commission Distribution System
- Configurable percentage allocation to specified wallets
- Can include DCA clients in commission distribution
- Separate from Flow Mode distribution
- Admin-controlled allocation rules

### Error Handling
- Insufficient Fixed Mode funds: LNBits wallet top-up + Nostr notification
- Failed transactions: Comprehensive logging and admin alerts
- Network issues: Retry mechanisms and offline mode handling

## File Structure Transformation

### From Current Template:
```
dca_admin/
├── templates/dca_admin/
│   ├── index.html
│   ├── dca_admin.html
│   └── _dca_admin.html
├── static/
├── models.py
├── crud.py
├── views.py
├── views_api.py
└── config.json
```

### To DCA System:
```
dca_admin/                    # Admin Extension
├── templates/dca_admin/
│   ├── index.html
│   ├── client_management.html
│   ├── transaction_monitor.html
│   └── commission_config.html
├── static/
├── models.py                 # DCA clients, transactions, distributions
├── crud.py                   # Database operations
├── views.py                  # Admin interface
├── views_api.py             # Internal APIs for client extension
├── transaction_processor.py # CSV processing & distribution logic
└── config.json

dca_client/                   # Client Extension  
├── templates/dca_client/
│   ├── index.html
│   ├── dashboard.html
│   └── analytics.html
├── static/
├── models.py                 # Minimal client-side models
├── views.py                  # Client interface
├── views_api.py             # Client API endpoints
└── config.json
```

## Next Steps

1. **Create updated specifications** for both extensions
2. **Transform current template** into DCA admin extension
3. **Create new client extension** from scratch
4. **Implement CSV processing** and distribution logic
5. **Build admin interface** for system management
6. **Create client dashboard** with analytics
7. **Test integration** and distribution calculations

## Key Decisions Confirmed

✅ **Data Source**: CSV fetch with SSH (+ optional direct Postgres)
✅ **Architecture**: Shared database via admin extension APIs
✅ **Distribution**: Proportional by deposit amounts
✅ **Fixed Mode**: System-wide 2000 GTQ daily limit
✅ **Authentication**: LNBits user_id + selected wallet
✅ **Updates**: Polling-based (30-60 seconds)
✅ **Commission**: Separate configurable distribution system

The system is now fully specified and ready for implementation! 🚀 