# DCA Admin Extension - Technical Specification

## Goal

Create an admin extension where the deposits of DCA clients are recorded and managed. This extension monitors the Lamassu ATM's Postgres database and automatically distributes Bitcoin to DCA clients based on successful layperson transactions.

## Core Functionality

### Database Monitoring

The admin extension monitors a Postgres database for new successful transactions. Every time a new (unprocessed) successful transaction is posted to the postgres database, the admin extension distributes the principal amount among the DCA clients.

### Key Responsibilities

1. **Transaction Monitoring**: Continuously monitor the Lamassu Postgres database for new successful transactions
2. **Payment Distribution**: Automatically distribute Bitcoin to Flow Mode DCA clients proportionally when new transactions occur
3. **Client Management**: Record and manage DCA client deposits and balances
4. **Fixed Mode Processing**: Handle scheduled distributions for Fixed Mode DCA clients
5. **Manual Transaction Entry**: Provide interface for manually adding transactions settled externally
6. **Duplicate Prevention**: Ensure no transaction is processed twice

## Technical Requirements

### Database Integration

- Connect to external Lamassu Postgres database
- Monitor for new successful transactions
- Track processed transactions to prevent duplicates
- Handle multiple machine IDs for future multi-location support

### Payment Processing

- **Flow Mode Distribution**: 
  - Triggered by both BTC and Lightning successful cash-out transactions
  - Distribute principal amount (`fiat_amount - actual_commission`) proportionally among Flow Mode clients only
  - No minimum transaction size - all transactions trigger distribution
  
- **Commission Distribution**: 
  - Separate distribution system for commission amounts
  - Configurable percentage allocation to specified wallets
  - DCA clients can optionally be included in commission distribution
  
- **Fixed Mode Processing**: 
  - Process scheduled distributions based on admin-configured timing (daily or multiple times per day)
  - Independent of layperson transactions
  
- Tag all DCA transactions with `aio-dca` for tracking and metrics

### Admin Interface Features

1. **Client Management Dashboard**
   - Add new DCA clients
   - Record initial deposits
   - Set DCA mode (Flow/Fixed)
   - View client balances and transaction history

2. **Transaction Monitoring**
   - View all Lamassu transactions (successful/failed)
   - Mark transactions as processed
   - Manual transaction entry interface
   - Transaction processing logs

3. **Fixed Mode Configuration**
   - Set distribution schedule (once daily or multiple times)
   - Configure maximum daily amounts per client
   - Manual trigger for fixed distributions

4. **Commission Distribution Management**
   - Configure commission distribution percentages
   - Set target wallets for commission allocation
   - Include/exclude DCA clients from commission distribution
   - Monitor commission distribution history

5. **System Administration**
   - Database connection settings
   - Transaction filtering configuration (BTC/LN)
   - System health monitoring
   - Processing status and logs

### Security & Data Integrity

- Secure connection to external Postgres database
- Transaction processing locks to prevent race conditions
- Comprehensive logging of all operations
- Backup and recovery procedures for client data

## Data Models

### DCA Client
- Client ID
- Initial deposit amount
- Current balance
- DCA mode (Flow/Fixed)
- Fixed mode daily limit (if applicable)
- Creation date
- Status (active/inactive)

### Processed Transaction
- Lamassu transaction ID
- Processing timestamp
- Amount distributed
- Number of clients affected
- Processing status

### Distribution Record
- Client ID
- Transaction ID
- Amount received (satoshis)
- Exchange rate at time of distribution
- Timestamp
- Distribution type (flow/fixed/manual/commission)

### Commission Distribution Config
- Wallet ID
- Allocation percentage
- Wallet type (DCA client/external wallet)
- Status (active/inactive)

## Integration Points

### External Systems
- Lamassu Postgres database (read-only access)
- LNBits wallet system for Bitcoin distributions

### Internal Systems
- Client extension (for user dashboards)
- LNBits core wallet functionality
- LNBits payment processing

## Monitoring & Alerting

- Database connection health
- Transaction processing failures
- Duplicate transaction attempts
- Distribution calculation errors
- Wallet balance monitoring

## Future Considerations

- Multi-location machine support
- Fiat DCA capability (mentioned as future feature)
- Advanced reporting and analytics
- API endpoints for external integrations 