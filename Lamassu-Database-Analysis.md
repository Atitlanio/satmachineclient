# Lamassu Database Analysis - Based on Sample Data

## Database Schema Analysis

Based on the provided CSV sample data, here's the identified structure:

### Transaction Table Structure (Estimated Column Names)

| Position | Field Name (Estimated) | Sample Values | Description |
|----------|------------------------|---------------|-------------|
| 1 | `id` | `81b3f12e-7c75-41a9-a212-8a82dcbfda07` | Transaction ID (UUID) |
| 2 | `device_id` | `b3f790bd3207aec95157de7c7a06d4130586e4d5b2c5b10a5b1dc9ff50498366` | ATM Device identifier |
| 3 | `crypto_address` | `bc1qc7gqgck9tx6cgv3d7y89xmqzvn6435u035l09m` | BTC address or Lightning invoice |
| 4 | `crypto_atoms` | `512400`, `31100`, `312100` | Amount in smallest crypto unit (satoshis) |
| 5 | `crypto_code` | `BTC`, `LN` | Cryptocurrency type |
| 6 | `fiat_amount` | `4000.00000`, `100.00000` | Fiat amount requested |
| 7 | `fiat_code` | `GTQ` | Fiat currency code (Guatemalan Quetzal) |
| 8 | `status` | `confirmed`, `notSeen` | **Transaction status (CRITICAL)** |
| 9 | `send` | `t`, `f` | Boolean - Send transaction flag |
| 10 | `receive` | `f` | Boolean - Receive transaction flag |
| 11 | `flag_11` | `f` | Boolean - Unknown purpose |
| 12 | `error_code` | `Operator cancel` | Error/cancellation reason |
| 13 | `created` | `2025-06-09 19:12:42.040933+00` | **Transaction creation timestamp** |
| 14 | `send_confirmed` | `2025-06-09 19:26:08.801857+00` | Send confirmation timestamp |
| 15 | `flag_15` | | Various flags |
| 16-18 | `flags_16_18` | `f`, `f`, `f` | Additional boolean flags |
| 19 | `confirmations` | `40`, `20`, `8` | Number of confirmations |
| 20 | `discount_1` | `0` | First discount field |
| 21 | `discount_2` | `100`, `0` | **Discount percentage (CRITICAL)** |
| 22 | `dispense_confirmed` | `100` | Dispense confirmation amount |
| 23 | `cancel_reason` | `operatorCancel` | Cancellation reason code |
| 24 | `machine_id` | `47ac1184-8102-11e7-9079-8f13a7117867` | **Machine UUID (consistent across all)** |
| 25 | `batch_id` | `25`, `26`, `16` | Batch identifier |
| 26 | `batch_time` | `2025-06-09 19:14:49.618988+00` | Batch processing time |
| 27 | `flag_27` | `f` | Boolean flag |
| 28-29 | `fields_28_29` | | Additional fields |
| 30 | `commission_percentage` | `0.05500`, `0.04500` | **Commission rate** |
| 31 | `exchange_rate` | `826091.28000`, `339104.71000` | **Exchange rate at transaction time** |
| 32 | `dispensed` | `512400`, `31100` | **Actually dispensed amount** |
| 33+ | `additional_fields` | Various | Additional transaction metadata |

## Key Findings for DCA System

### ✅ Critical Fields Identified

1. **Transaction Status**: Column 8 (`status`)
   - `confirmed` = Successful transaction ✓
   - `notSeen` = Failed/incomplete transaction ✗

2. **Transaction Amounts**:
   - **Fiat Amount**: Column 6 (`fiat_amount`) - What layperson requested
   - **Crypto Amount**: Column 4 (`crypto_atoms`) - Satoshis/smallest unit
   - **Dispensed Amount**: Column 32 (`dispensed`) - Actually given amount

3. **Commission Data**:
   - **Commission Rate**: Column 30 (`commission_percentage`) - e.g., 0.05500 (5.5%)
   - **Discount Percentage**: Column 21 (`discount_percentage`) - e.g., 100 = no commission, 10 = 10% off
   - **Exchange Rate**: Column 31 (`exchange_rate`) - Rate at transaction time

4. **Timing**:
   - **Created**: Column 13 (`created`) - Transaction initiation
   - **Confirmed**: Column 14 (`send_confirmed`) - When completed

5. **Machine Identification**:
   - **Machine ID**: Column 24 (`machine_id`) - Same across all: `47ac1184-8102-11e7-9079-8f13a7117867`

### Transaction Types Observed

1. **Successful Cash-Out (Sell)**: `status = 'confirmed'`, `send = 't'`
   - Layperson sells BTC, receives fiat
   - These transactions should trigger DCA distributions

2. **Failed Transactions**: `status = 'notSeen'`
   - Should be ignored by DCA system

3. **Cancelled Transactions**: Contains `"Operator cancel"`
   - Should be ignored even if status shows confirmed

4. **Lightning vs On-Chain**: 
   - `crypto_code = 'LN'` for Lightning
   - `crypto_code = 'BTC'` for on-chain

5. **Discount Analysis from Sample Data**:
   - Most transactions show `100` in discount field = **NO COMMISSION**
   - One transaction shows `90` = **90% discount** (only 10% of commission applies)
   - Standard transactions appear to have 100% discount (commission-free)
   - Special promotional transactions may have partial discounts

## SQL Query for DCA System

Based on this analysis, here's the query to get new successful transactions:

```sql
-- Get new successful cash-out transactions for DCA distribution
SELECT 
    id,
    fiat_amount,
    crypto_atoms,
    commission_percentage,
    discount_percentage,  -- Column 21: Critical for commission calculation
    exchange_rate,
    dispensed,
    created,
    send_confirmed,
    machine_id
FROM transactions 
WHERE status = 'confirmed' 
    AND send = 't' 
    AND error_code IS NULL 
    AND cancel_reason IS NULL
    AND created > :last_processed_timestamp
ORDER BY created ASC;
```

## Answers to Your Original Questions

### 3. Flow Mode Distribution Logic (FINAL)
- **Trigger Transactions**: Both `BTC` and `LN` (Lightning) successful cash-outs
- **Target Recipients**: **Flow Mode DCA clients ONLY** (Fixed Mode clients not affected)
- **Distribution Amount**: `fiat_amount - actual_commission` (principal only)
- **No Minimum**: All successful transactions trigger distribution, regardless of size
- **Commission Calculation**:
  ```
  base_commission = fiat_amount * commission_percentage
  actual_commission = base_commission * (1 - discount_percentage/100)
  flow_mode_distribution = fiat_amount - actual_commission
  ```
- **Bitcoin Value Reference**: Use `crypto_atoms` for rate calculations
- **Special Cases**:
  - If `discount_percentage = 100`: No commission, Flow Mode gets full `fiat_amount`
  - Commission amount (if any) goes to separate distribution system

### 4. Commission Distribution System (UPDATED)
- **Base Commission Rate**: `commission_percentage` (e.g., 0.05500 = 5.5%)
- **Discount Applied**: `discount_percentage` (e.g., 100 = no commission, 10 = 10% off)
- **Commission Calculation**:
  ```
  base_commission = fiat_amount * commission_percentage
  discount_amount = base_commission * (discount_percentage / 100)
  actual_commission = base_commission - discount_amount
  ```
- **Distribution Logic**:
  - **Principal Amount**: `fiat_amount - actual_commission` → **Flow Mode DCA clients only**
  - **Commission Amount**: `actual_commission` → **Separate distribution system** (configurable percentages to specified wallets)
  - **DCA clients can potentially be included** in commission distribution
- **Example**: 1000 GTQ transaction, 5.5% commission, 10% discount:
  - Base commission: 1000 * 0.055 = 55 GTQ
  - Actual commission: 55 - 5.5 = 49.5 GTQ
  - **To Flow Mode DCA**: 1000 - 49.5 = 950.5 GTQ
  - **To Commission Distribution**: 49.5 GTQ (distributed per admin configuration)

### Duplicate Prevention Strategy
- Use the `id` field (transaction UUID) to track processed transactions
- Store processed transaction IDs in your LNBits extension database
- Query: `WHERE id NOT IN (processed_transaction_ids)`

## Recommendations

1. **Focus on Cash-Out Transactions**: Filter for `send = 't'` (layperson selling BTC)
2. **Status Check**: Only process `status = 'confirmed'` 
3. **Error Handling**: Exclude transactions with `error_code` or `cancel_reason`
4. **Use Dispensed Amount**: Consider using `dispensed` field for actual transaction value
5. **Commission Decision**: Decide whether DCA clients get commission benefit or not

This sample data provides everything needed to build the DCA system! 🎯 