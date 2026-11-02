# Démo partageable sur GitHub Pages

La version publique exécute le moteur Python existant avec Pyodide 0.29.3 dans
un Web Worker. Les validations FastAPI, les permissions, la comptabilité et les
exports sont conservés. Aucun serveur bancaire ni base partagée ne sont exposés.

- Chaque onglet initialise ses propres données fictives en mémoire.
- Recharger la page remet les données à zéro. Changer de rôle par déconnexion
  conserve les opérations dans le même onglet.
- Connexion : `admin` / `Demo2026!`, ou les autres rôles du README.
- Le premier chargement nécessite Internet pour télécharger Python et ses
  bibliothèques depuis jsDelivr. Il peut prendre une minute.
- Ne saisir que des données fictives. Les identifiants sont ceux d'une simulation.
- L'authentification illustre les rôles ; le visiteur contrôle son propre moteur.

## Publication

Dans Settings → Pages, sélectionner **GitHub Actions** comme source.
Chaque push sur `main` lance les tests, construit `dist/` et publie la démo.
Le paquet contient uniquement les sources Python et les ressources web : la base
SQLite locale, les environnements et les caches sont exclus.

## Vérification locale

```sh
python scripts/build_pages.py
python -m http.server 8765 --directory dist
```

Ouvrir http://localhost:8765. Le lancement local habituel avec `python run.py`
reste disponible et conserve sa base SQLite sur disque.
