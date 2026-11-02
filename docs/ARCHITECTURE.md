# Architecture and design rationale / Architecture et choix techniques

**Intent:** executable proof of concept for a Cameroonian microfinance (EMF) client presentation. No live banking.

## 1. Bounded modules

```text
                 Browser SPA (FR / EN)
                        │ HTTPS? No, loopback HTTP demo only
                        ▼
           FastAPI REST application
        ┌──────────┬───────────┬───────────┐
        │ Identity │ Customers │ Dashboard │
        │ / RBAC   │ / KYC     │ / Reports │
        └──────────┴─────┬─────┴─────┬─────┘
                         │           │
          ┌──────────────▼───────────▼───────────────┐
          │ Domain services / accounting policies   │
          │ Accounts • operations • loans • audit   │
          └───────────────────┬──────────────────────┘
                              │ BEGIN IMMEDIATE / COMMIT
                              ▼
                        SQLite database
          users, customers, accounts, operations,
          loans, journals, journal_lines, alerts, audit
```

**Design choices:** separate database/schema, authorization, business logic, API transport, translations and UI concerns. No remote UI dependencies. Source is intentionally readable and annotated in English. Typed Pydantic request models block invalid enum values, amounts and dates before state mutation.

## 2. Accounting principles

- All customer funds are synthetic; quantities are positive **integer XAF**.
- An account balance is a cache reconciled against journal lines, not an editable number.
- Posting requires at least two lines and equality of total debit and total credit.
- A single SQLite `BEGIN IMMEDIATE` transaction writes both journal lines and account balances. On failure, all changes roll back.
- A customer deposit increases cash on hand (debit 1000) and deposit liability (credit 2100/customer).
- A withdrawal debits deposit liability (2100/customer) and credits cash (1000).
- Internal transfers debit source liability and credit destination liability.
- Simulated mobile transfers debit source liability and credit an **internal fictional clearing ledger**; **no provider is actually contacted**.
- Loan disbursements debit loan receivable 1300 and credit customer deposit liability 2100.
- Loan repayments debit deposit liability, credit receivable and credit the demonstration interest-income ledger 4100 where applicable.
- Rejecting a pending workflow changes workflow status but does not post a journal.

**IMPORTANT:** The ledger codes, loan interest treatment, treasury representation and regulatory mapping are simplistic teaching models, not a comprehensive or legally approved accounting implementation. A real core must implement a reviewed EMF chart of accounts, EOD and daybooks, branch vaults, settlement and reconciliation, tax accounting, prudent provisioning and reconciliation to regulatory returns.

## 3. Authorization & segregation

Permissions are enforced by the **server**. UI visibility is only a convenience. Roles include admin, teller, credit, manager, compliance and auditor. Pending outgoing operations start at 1,000,000 XAF; loans always require review. The creator cannot approve their own request. Concurrency is serialized by SQLite transactions; pending transactions are revalidated at approval time. Holds/reservations are **not** implemented.

## 4. Client navigation

- Login page, role switch, FR/EN toggle
- Overview with KPIs, chart and portfolio distribution
- Customers & KYC
- Accounts, freeze/unfreeze, statements
- Transactions, pending approvals
- Loans, origination, approvals, repayments
- Compliance, alert review/escalation
- Branch network and synthetic deposits
- Reporting, journal checks, CSV export
- Audit and products/channel catalog

## 5. Deployment evolution / Recommandations production

1. Requirements discovery workshops with FINEC operations, risk, finance, IT and counsel.
2. Formal regulatory gap analysis with Cameroonian counsel and COBAC/BEAC specialists.
3. Rebuild on PostgreSQL with serializable ledger engine, immutable event storage, outbox, and reconciliation. Add strong accounting periods and approved chart of accounts.
4. Enforce maker-checker across onboarding, parameter changes, treasury and privileged administration, with KYC document evidence and multi-factor authentication.
5. Integrate approved KYC sanctions/PEP screening, fraud monitoring, reporting, secure document storage and real regulator templates.
6. Contract with actual payment providers only after relevant approval and operational due diligence. Implement webhooks, settlement, dispute handling and idempotent event processing.
7. Secure network isolation, access management, hardware key protection, backups, encryption, audit retention, observability, code review and penetration testing.
8. Run parallel accounting and regulatory reconciliations, conduct UAT, load/security testing and obtain supervisory or professional validations as applicable.

For real production, avoid using this prototype as the foundation of a regulated ledger without substantial reengineering, independent review and field testing.
