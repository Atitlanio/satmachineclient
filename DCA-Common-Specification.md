# DCA System - Common Specification

## System Overview

This document describes the common elements of a Dollar Cost Averaging (DCA) system that integrates with Lamassu Bitcoin ATMs. The system consists of two LNBits extensions:

1. **Admin Extension**: Monitors Postgres database and manages DCA distributions
2. **Client Extension**: Provides user dashboard for DCA control and monitoring

## Context

A user provides a certain amount of cash to a Dollar Cost Average (DCA) service. This cash goes into a Lamassu Bitcoin ATM (it's a 2-way machine that allows both buying and selling).

For now, you can only DCA by purchasing Bitcoin, however it would be interesting to make sure that it is generalized in such a way that someone could also DCA into fiat. In the current moment we are not concerned with the latter option, we are only concerned with someone being able to DCA into Bitcoin.

The Lamassu ATM (often referred to as "the machine") runs a server which stores all transactions in a postgres database. It is important to note that not all transactions succeed, so for this service, we want to make sure that we are only accounting for successful transactions. We may want the ability to manually add a transaction in the case that a interaction is settled externally.

Note that the frame of reference with regards to a transaction will always be from the perspective of the layperson and Bitcoin. E.g., if a layperson sells. They are selling their Bitcoin to the machine and receiving fiat in return. If they buy, they are buying Bitcoin from the machine and inserting fiat in exchange.

This system will eventually involve multiple machines in different locations, however there is currently only one. All machines log to the same Postgres database and simply have a field for machine id.

## Definitions

**Dollar Cost Averaging**: When someone commits to buying an asset over time instead of in one lump sum

**layperson**: an unknown person who uses the Lamassu machine to either buy or sell bitcoin. They are not directly related to the DCA system. They are what fuel the system by their interactions with the system.

**client**: someone who is providing cash to the Lamassu ATM and receiving back Bitcoin through one of the methods defined below

**commission**: the amount that the machine charges to the layperson.

**cash-out**: when someone sells their bitcoin to the machine in return for cash.

**cash-in**: when someone buys Bitcoin from the machine with fiat.

## DCA Methods

Clients choose one of two DCA methods that they can change in their dashboard:

### Flow Mode

This works by the client choosing to receive their Bitcoin as a function of layperson transactions.

#### Example

1) A client provides 20,000 GTQ to DCA. Once the 20,000 GTQ is received it is placed into the ATM. It is now in the ATM.

2) Following its placement into the ATM, a layperson goes to cash out at the machine and decides to sell, i.e., exchange their BTC for 2,000 GTQ. They create a "sell" order and choose 2,000 GTQ. The machine calculates the exchange rate, taking into account commission, and provides the layperson a QR code to which they will send their BTC.

3) If the transaction is successful, the layperson receives their cash and it is logged in the postgres database on a separate server. The lnbits extension then detects that a new successful transaction has occurred and it distributes the transaction amongst all of the Flow Mode DCA'ers proportionally.

3a) if the transaction is unsuccessful, nothing happens

3b) leave room for a manual input in the case that a failed transaction is settled externally

### Fixed Mode

The DCA client can choose to receive up to X amount per day. They can vary the amount, but there is a limit. The extension admin will choose when the fixed DCA is distributed. Either it happens once a day at a fixed time, or it happens Y times per day.

## System Properties/Features

DCA transactions will be tagged with `aio-dca` so that the extension knows to filter for those when calculating metrics.

Clients can see things such as their:

- Average DCA rate in fiat/BTC
- Total amount of satoshis stacked
- any other useful stats

## Critical Requirements

### Duplicate Payment Prevention

We must have a check in place to know when a successful transaction has already been processed so that no duplicate payments occur.

### Transaction Processing Rules

- Only successful transactions should be processed
- Failed transactions should be ignored unless manually added
- All transactions must be properly logged and trackable
- Commission amounts should be handled separately from principal amounts

## Database Integration

The system integrates with the Lamassu ATM's Postgres database to monitor for new successful transactions. The database contains:

- Transaction records with success/failure status
- Machine ID for multi-location support
- Transaction amounts (principal + commission)
- Timestamps and other transaction metadata 