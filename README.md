# FINEC ONE — Core Banking Experience (interactive simulated prototype)

**FR / EN** · **Python FastAPI + SQLite + HTML/CSS/JavaScript (no UI dependencies)** · **100% synthetic data**

> **IMPORTANT / IMPORTANT** — This is an interactive **software demonstration**, **not** a production banking system, a licensed financial product, or a certificate of compliance with COBAC, CEMAC, BEAC, ANIF or Cameroonian law. Never use it for real customer data, real money, or public internet access. FINEC S.A. did not approve or commission this independent prototype. It is not affiliated with FINEC. All customer records and balances are fabricated.

## Démo web partageable

La version GitHub Pages fonctionne entièrement dans le navigateur, avec une base
fictive isolée par onglet. Connexion : **admin / Demo2026!**. Recharger réinitialise
la simulation. Le premier chargement peut prendre une minute.

Les avertissements concernant l'exposition publique du serveur Python ci-dessous
s'appliquent à la version serveur locale ; la version Pages n'expose aucun serveur
ni aucune base partagée. Voir [le guide GitHub Pages](docs/GITHUB_PAGES.md).

## 🇫🇷 Démarrage en 3 étapes

1. Décompresser `FINEC_ONE_Core_Banking_Demo.zip` et installer **Python 3.11 ou supérieur** (accès Internet nécessaire uniquement pour l'installation des dépendances Python).
2. Sous **Windows**, double-cliquer sur `START_WINDOWS.bat`. Sous **macOS/Linux**, lancer `bash START_MAC_LINUX.sh` depuis le dossier décompressé.
3. Ouvrir **http://127.0.0.1:8000** dans Chrome, Edge, Firefox ou Safari.

Ou, manuellement :

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

L'application démarre sur l'adresse locale `127.0.0.1` seulement. Le dossier inclut une base préchargée `finec_demo.sqlite3` générée avec des données fictives. Si la base n'existe pas, elle est créée automatiquement au premier lancement. Les modifications sont conservées entre les sessions.

### Comptes de démonstration

| Identifiant | Mot de passe | Rôle | Fonction principale |
|---|---|---|---|
| `admin` | `Demo2026!` | Administrateur | Accès complet, sauf validation de ses propres opérations |
| `agent` | `Demo2026!` | Agent de caisse | Clients, comptes, dépôts, retraits, virements, remboursements |
| `credit` | `Demo2026!` | Gestionnaire crédit | Ouverture des demandes de crédit |
| `manager` | `Demo2026!` | Responsable | Validation indépendante des opérations et des crédits |
| `conformite` | `Demo2026!` | Conformité | Vérification KYC, alertes, gel de comptes |
| `auditeur` | `Demo2026!` | Auditeur | Lecture seule des données et des journaux |

Le bouton **FR / EN** traduit l'interface. Les commentaires et la structure des modules sont rédigés en anglais. Les erreurs d'API sont principalement en anglais avec traduction des principaux cas usuels à l'écran.

### Parcours de démonstration guidé

1. Connexion avec **agent** → Clients → Ajouter un client (KYC = en attente).
2. Déconnexion, connexion avec **conformite** → Clients → KYC → Vérifié.
3. Reconnexion avec **agent** → Comptes → Ouvrir un compte au nouveau client.
4. Transactions → Déposer 250 000 XAF → Vérifier le nouveau solde et le relevé.
5. Initier un virement d'au moins 1 000 000 XAF depuis un compte suffisamment approvisionné. L'opération devient **en attente**.
6. Se connecter avec **manager** → Validations → Approuver : les deux comptes changent et le journal est équilibré.
7. Connexion **credit** → Créer un crédit ; connexion **manager** → Approuver ; connexion **agent** → Rembourser.
8. Consulter Conformité, Reporting (balance) et Audit ; télécharger les CSV. Tenter une validation de sa propre demande : elle sera refusée.

### Remise à zéro des données fictives

Fermer le serveur, puis lancer :

```bash
python -m app.reset
```

Taper `RESET` pour confirmer. **Toutes les modifications locales de démonstration seront effacées**.

### Tests automatiques

```bash
python -m pytest -q
```

L'API interactive et sa documentation technique sont accessibles à `http://127.0.0.1:8000/docs` après démarrage.

## 🇬🇧 Quick start

1. Unzip the archive and install **Python 3.11+**.
2. On **Windows**, run `START_WINDOWS.bat`. On **macOS/Linux**, run `bash START_MAC_LINUX.sh`.
3. Visit **http://127.0.0.1:8000** and sign in with `admin` / `Demo2026!` (or another demo role above).

Alternatively run `python -m venv .venv`, activate the environment, run `python -m pip install -r requirements.txt`, and execute `python run.py`.

The app automatically initializes a populated SQLite demo database, persists your changes, and supports immediate FR/EN switching. All banking flows are fictional and local only; no real payment rails or customer databases are integrated.

## Modules fonctionnels / Working modules

| Module | Simulation opérationnelle / Operational simulation |
|---|---|
| Identity & RBAC | Local login, salted password hashes, expiring sessions, six permission profiles |
| Branches | Seven publicized FINEC branch labels, synthetic aggregates, multi-branch customer segmentation |
| Customers & KYC | Create a customer, mark verified/rejected, classify risks |
| Deposit accounts | Create savings/current/daily/blocked accounts, view balances, freeze/unfreeze and export account statements |
| Operations | Cash deposits/withdrawals, daily collections, internal transfers and fictional external mobile money clearing |
| Four-eyes approvals | High-value outgoing transactions are pending until approved by a separate user; the same user cannot approve their own request |
| Lending | Applications, simulated annual interest, installment approximation, independent decision, booked disbursement and simplified repayment |
| General ledger | Atomic, integer-XAF double-entry journals, debit/credit equalities, reconciled customer balances |
| Compliance | Risk-tagging and rule-triggered alerts, review/escalation actions, basic KYC gate |
| Management | KPIs, activity chart, portfolio and branch distribution |
| Audit & reporting | Chained hashes, audit records, GL summary, integrity checks, CSV exports |
| Catalog & channels | Product descriptions with *illustrative* rates, clearly inactive external integration names |

**Not implemented:** real BEAC/COBAC filings, verified regulatory chart-of-accounts mapping, cash vault/agent till reconciliation, tax/fee engines, periodic interest accrual, deposit interest crediting, loan amortization scheduling, delinquency/PAR and provisioning, collateral and guarantors, bank statement matching, reconciliation with third-party settlement, real mobile money, real foreign exchange, AML screening against sanctions/PEP lists, FIU disclosures, strong customer authentication, multi-tenancy, production encryption, HSM/key rotation, data governance, archival, infrastructure monitoring, system integrations or external penetration testing. These require separate commissioned development and validation.

## Architecture (code organization)

```text
FINEC_ONE/
├── app/
│   ├── database.py       # SQLite schema, connection lifecycle, atomic transactions
│   ├── security.py       # PBKDF2 credentials, bearer session, RBAC permissions
│   ├── services.py       # Double-entry GL, transfers, loans, compliance, audit chain
│   ├── seed.py           # Synthetic client, account, transaction and user fixtures
│   ├── main.py           # FastAPI routes, validation models, dashboard, CSV APIs
│   └── reset.py          # Explicit demo-only data reset command
├── web/
│   ├── index.html        # Application shell
│   ├── styles.css        # Responsive UI design system
│   └── app.js            # FR/EN translation catalog, screens and API actions
├── docs/
│   ├── REGULATORY_MAPPING.md
│   ├── ARCHITECTURE.md
│   └── PRESENTATION_SCRIPT.md
├── tests/test_workflows.py # End-to-end API tests for money and approvals
├── finec_demo.sqlite3    # Seeded LOCAL demo DB
├── run.py
├── START_WINDOWS.bat
├── START_MAC_LINUX.sh
├── requirements.txt
└── README.md
```

Amounts use **integer XAF**. Core journals are posted in a single database transaction. Customer deposit GL is `2100`, cash `1000`, loan receivable `1300`, external clearing `2200`, illustrative equity `3000`, interest income `4100`. **These are deliberately simplified internal demo account codes, not the certified EMF plan comptable.**

### Environment / Configuration

- `FINEC_DB_PATH`: optional absolute or relative path for the demo SQLite file.
- `http://127.0.0.1:8000/docs`: OpenAPI API explorer (locally running).
- No production external service, API keys, emails, or customer information are required.
- Test suite always uses temporary isolated databases and cannot alter the packaged demo database.

### Security limitations and intended audience

Users should demonstrate this prototype in a controlled, private laptop environment. All demo passwords are published; sessions are held in browser session storage; SQLite is unencrypted; there is no TLS termination, MFA, rate limiting, network firewall, dedicated key management, password policy, column-level access control, SIEM, disaster recovery, approved data retention policy, or security certification. **Do not deploy it publicly or use confidential information.** The audit chain detects some simple modifications but is neither write-once nor cryptographically anchored, and should not be treated as tamper-proof evidence.

The feature scope is a **proof of concept**, not a complete banking core. The references to the insurer-level experience concern product UX, controls and modularity; FINEC is a **microfinance institution**, and insurance underwriting or insurance claims management are not part of this CBS.

For regulatory scoping, see `docs/REGULATORY_MAPPING.md`; it explicitly separates demonstrative hooks from legal compliance.
