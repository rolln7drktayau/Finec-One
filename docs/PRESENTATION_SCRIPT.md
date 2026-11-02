# FINEC ONE — Presentation script / Scénario commercial

## 🇫🇷 Démonstration de 10 à 15 minutes

**Positionnement.** « FINEC ONE est une proposition indépendante de plateforme de microfinance évolutive, avec une expérience utilisateur premium et une base de simulation opérationnelle. Les données sont fictives et aucun versement bancaire n'est effectué. »

1. **Pilotage** — Ouvrir la vue d'ensemble : solde consolidé, nombre de clients, dossiers, activité et répartition géographique.
2. **Entrée en relation** — Créer un client avec le profil `agent`. Ouvrir le dossier avec `conformite` pour valider le KYC.
3. **Cycle de vie compte** — Avec `agent`, ouvrir un compte puis effectuer un dépôt. Retourner sur les soldes et le relevé.
4. **Contrôle des opérations** — Faire un virement supérieur à 1 million XAF : en attente ; valider depuis `manager` ; afficher les deux soldes et le journal.
5. **Crédit** — Avec `credit`, saisir un dossier ; avec `manager`, le valider ; avec `agent`, enregistrer un remboursement.
6. **Conformité et contrôle** — Passer par les alertes, la balance, les contrôles d'intégrité, les exports et la chaîne d'audit.
7. **Bilinguisme et mobilité** — Passer l'interface en anglais, puis montrer la mise en page sur mobile.
8. **Conclusion et limites** — Proposer une phase d'étude métier/réglementaire, un cahier des charges et une architecture de production distincte.

### Questions à poser à FINEC avant une V2

- Nombre d'agences opérationnelles, utilisateurs simultanés, produits, volumes et contraintes de disponibilité ?
- Système comptable existant, plan comptable EMF réel, format de reporting et états COBAC exigés ?
- Circuit complet d'ouverture, exigences de pièces justificatives, KYC, sanctions, consentements ?
- Octroi de crédit : délégations, garanties, scoring, échéancier, impayés, intérêts, provisions ?
- Besoins de collecte terrain, mobile money, compensation bancaire, virements, transferts internationaux et partenaires contractuels ?
- Besoins exacts de sécurité, résilience, audit, hébergement et souveraineté des données ?

## 🇬🇧 Short presenter script

“This independent mock core banking platform demonstrates a premium bilingual experience for the operating model of a CEMAC microfinance institution. We simulate customer onboarding, KYC approval, account management, double-entry posting, high-value four-eyes approvals, loan disbursement and repayment, AML-style review queues, branch analytics, exportable reports and audit records. No funds, bank services or personal data are connected. Production would require formal requirements, implementation, independent assurance and regulatory validation.”
