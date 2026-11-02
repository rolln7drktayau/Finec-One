# FINEC ONE — CEMAC / Cameroon regulatory scoping memo

**Status:** regulatory discovery notes, current research as of **2 November 2026**. **Not legal advice, an audit opinion, a compliance certificate, or an official FINEC regulatory determination.** Confirm applicability, updated texts, supervisory circulars and exact thresholds with qualified Cameroon/CEMAC banking counsel and the institution's compliance officer.

## FINEC product and licensing context

FINEC's official website describes it as a **second-category microfinance institution** (établissement de microfinance de deuxième catégorie), headquartered in Douala Akwa, with deposit/savings, lending, daily collection and transfer-related products. FINEC's website publicly lists branch locations in Akwa, Bonabéri, Yaoundé-Mendong, Bafia, Bépanda, Village/Ndogpassi and Dschang. These **place names** inform the synthetic demonstration fixtures; no live FINEC customer/transaction data is used.

- https://finec.cm/company-overview/
- https://finec.cm/about-layout-3/
- https://finec.cm/service-layout-4/

## Key framework and implementation mapping

| Domain | Primary source or framework | Demo evidence (not regulatory satisfaction) | Production gap |
|---|---|---|---|
| Licensing and internal control | **Règlement n°01/17/CEMAC/UMAC/COBAC** (conditions d'exercice et de contrôle de l'activité de microfinance). Section on internal control, notably article 10. | Six role profiles, a maker-checker approval, audit events | Verify all EMF-specific rules; document delegations, internal control, risk limit structure and governance |
| EMF accounting | **COBAC EMF-2010/01** (plan comptable) and **COBAC EMF-2010/02** (organisation des comptabilités) | Balanced ledger, customer balance reconciliation | Implement and have audited the complete current EMF chart of accounts, balance sheet, earnings, cashbooks, reconciliation and cut-offs |
| Supervisory reporting | **COBAC I-EMF-2010/03** (états déclaratifs / comptes annuels) | CSV exports and dashboard | Build verified official templates, timing, data lineage, sign-off and secure supervisory submission |
| AML/CFT/CPF | **Règlement n°02/24/CEMAC/UMAC/CM**, adopted 20 Dec 2024, concerning prevention/repression of money laundering, terrorism financing and proliferation | Fictional KYC status, high-risk flag, sample threshold alert/review queue | Complete risk-based due diligence, beneficial ownership, sanctions/PEP/TF screening, suspicious activity analysis, legally correct reporting/retention, alert confidentiality and escalation procedures. The older **2016** framework should not be the sole requirements baseline |
| Financial intelligence | **ANIF Cameroun** (financial intelligence unit) | Mock monitoring queue, no external communication | Confirm reportability, deadlines, channels, confidentiality and filing format with ANIF and specialist counsel |
| Payments | **Règlement n°04/18/CEMAC/UMAC/COBAC** (payment services) and **Règlement n°03/16/CEMAC/UMAC/CM** (payment means/incidents) | Simulated internal transfers and a fictional mobile-money clearing ledger | Authorization/partnership scoping, end-to-end payments, settlement controls, reconciliation, chargebacks, incident handling |
| FX controls | **Règlement n°02/18/CEMAC/UMAC/CM** (foreign exchange) | Intentionally NO external currency settlement functionality | Restrict cross-border and FX functionality until authorized scope, documentary rules and compliance design confirmed |
| IT, security, business continuity | COBAC 2024 risk-information-system reforms, discussed in the official **2024 COBAC annual report**; report describes EMF entry into force **1 July 2026** | Local RBAC and traceability as early concepts | Governance, security policy, IT outsourcing controls, backups, incident response, continuous testing, BCP/DRP, data quality and change control |
| Banking terms and credit products | **Règlement n°04/19/CEMAC/UMAC/CM** (effective global rate, usury and publication of conditions) — confirm scope/applicability to the relevant EMF products | Illustrative annual percentages only | Exact legal APR/TEG, fee schedules, amortization, total cost of credit, disclosures, usury tests, credit provisions |
| Banking confidentiality / data | **Cameroon Law n°2022/006 of 27 April 2022** on banking secrecy; applicable personal-data rules require separate expert review | No real data in prototype | Consent, confidentiality, encryption, access restrictions, retention/deletion, legal data-transfer rules and incident response |

**IMPORTANT:** It would be incorrect to treat an illustrative transaction alert threshold of 2,000,000 XAF as a legally mandated AML threshold. Likewise, the 1,000,000 XAF dual-approval threshold is an **example internal policy choice**, not a COBAC obligation. Both are hard-coded simulator rules; production rules need formal approval and effective versioned configuration.

## Sources for legal verification

1. BEAC, microfinance regulations: https://www.beac.int/supervision-bancaire/microfinance/reglements-de-microfinance/
2. BEAC, EMF reporting instructions: https://www.beac.int/supervision-bancaire/microfinance/instructions-de-microfinance/
3. COBAC regulation index (BEAC): https://www.beac.int/supervision-bancaire/reglements-de-cobac/
4. Microfinance presentation (BEAC): https://www.beac.int/supervision-bancaire/microfinance/presentation-de-microfinance/
5. ANIF (official): https://anif.cm/a-propos/
6. GABAC, 2024 AML/CFT/CPF text: https://gabac.org/wp-content/uploads/2025/05/Reglement-N%C2%B002CEMAC-UMAC-CM-LBC_FT-2024.pdf
7. COBAC annual report 2024 (IT-risk information, BEAC): https://www.beac.int/wp-content/uploads/2016/10/Rapport-annuel-de-la-COBAC-2024-PDF-14.8-Mo_compressed-1.pdf
8. BEAC on CEMAC payments: https://www.beac.int/systemes-paiement/presentation-generale/
9. GECAM links to banking secrecy and EMF governance instruments: https://legecam.cm/reglementations/
10. Legal text article 10 (secondary searchable rendering; cross-check against official): https://lex.cameroun.cc/fr/cemac/cemac-r-glement-n-01-17-relatif-aux-conditions-d-exercice-et-de-controle-de-lactivite-de-m/art-10

## Validation list for a formal RFP

- Confirm official FINEC EMF category, permitted services and signed-off scope per license/approval.
- Secure the currently applicable COBAC, BEAC, GABAC and Cameroonian law corpus.
- Conduct data-flow/process workshops with operations, IT, audit, compliance, finance and legal leadership.
- Translate each legal requirement into version-controlled acceptance tests and obtain written approval from qualified reviewers.
- Agree contractual responsibility for mobile money, transfers, credit scoring, FX and any bancassurance/insurance intermediary activities.
- Audit the final financial ledger independently and reconcile all statements to the supervisory returns.

## 🇬🇧 Summary

The demonstrator illustrates some *concepts* expected in a regulated CEMAC microfinance operating environment: KYC verification, role-based access, maker/checker, risk alerts, transaction journals, internal accounting and traceability. It does **not** implement the detailed law. Do not market this proof of concept as COBAC-compliant or production-ready. Build a legally reviewed compliance matrix from the official and current texts before launching any live financial service.
