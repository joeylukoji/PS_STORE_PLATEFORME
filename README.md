# PS_STORE_PLATEFORME

Plateforme e-commerce PS STORE — backend **Django**, frontend **HTML / CSS / JS** dans les templates Django.
Le périmètre suit le backlog [`docs/BACKLOG-SCRUM.md`](docs/BACKLOG-SCRUM.md) (PS-01 à PS-20).

## Démarrage rapide

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py init_store          # rôles + catégories (ajouter --demo pour des produits fictifs)
python manage.py createsuperuser     # compte administrateur
python manage.py runserver
```

- Boutique : http://127.0.0.1:8000/
- Espace de gestion : http://127.0.0.1:8000/gestion/
- Admin Django (secours) : http://127.0.0.1:8000/django-admin/

Tests : `python manage.py test`

## Administration

### Créer un compte administrateur

Un superutilisateur Django a automatiquement le rôle **Administrateur** dans `/gestion/` et l'accès à `/django-admin/`.

```bash
python manage.py init_store          # crée les groupes « Administrateur » et « Employé » (à faire une fois)
python manage.py createsuperuser     # demande identifiant, e-mail et mot de passe
```

Sans interaction (script, CI) :

```bash
# Linux / macOS
DJANGO_SUPERUSER_PASSWORD='MotDePasseFort!' python manage.py createsuperuser --noinput --username admin --email admin@psstore.local
```

```powershell
# Windows PowerShell
$env:DJANGO_SUPERUSER_PASSWORD = 'MotDePasseFort!'
python manage.py createsuperuser --noinput --username admin --email admin@psstore.local
```

### Changer le mot de passe d'un compte

```bash
python manage.py changepassword admin
```

### Donner le rôle Administrateur à un compte existant (sans superutilisateur)

```bash
python manage.py shell -c "from django.contrib.auth.models import User, Group; u = User.objects.get(username='jean'); u.is_staff = True; u.save(); u.groups.add(Group.objects.get(name='Administrateur'))"
```

Remplacer `Administrateur` par `Employé` pour un compte employé. Une fois connecté, un administrateur peut aussi créer les comptes et attribuer les rôles depuis **Gestion → Utilisateurs**.

## Structure

| Dossier | Contenu |
|---|---|
| `psstore/` | Configuration (settings, URLs) |
| `store/` | Modèles, catalogue, panier (session), commande, suivi |
| `backoffice/` | Connexion, tableau de bord, produits, stock, commandes, rapports, utilisateurs/rôles |
| `templates/` | Pages HTML (`store/`, `backoffice/`) |
| `static/css/style.css`, `static/js/app.js` | Style et interactions (le site fonctionne aussi sans JS) |

## Couverture du backlog

| Story | Où |
|---|---|
| PS-01 à PS-05 | Catégories, catalogue, filtre PS4/PS5/Xbox, fiche produit, recherche |
| PS-06 à PS-10 | Panier, validation (retrait/livraison), référence unique, suivi par référence + e-mail |
| PS-11, PS-18 | Connexion `/gestion/`, rôles **Administrateur** / **Employé** contrôlés côté serveur |
| PS-12, PS-13 | Création/modification/publication des produits, photos (JPG/PNG/WEBP ≤ 3 Mo), caractéristiques libres |
| PS-14, PS-15 | Mouvements de stock tracés (auteur, motif, date), stock négatif bloqué, seuil d'alerte |
| PS-16, PS-17 | Liste/détail des commandes, transitions de statut contrôlées et historisées |
| PS-19, PS-20 | Tableau de bord, ventes par période |

| Rôle | Accès |
|---|---|
| Employé | Tableau de bord, commandes, stock |
| Administrateur | Tout, plus produits, rapports, utilisateurs |

## Hypothèses à valider (section 10 du backlog)

- **Paiement** : pas de paiement en ligne ; règlement à la livraison ou au retrait.
- **Réservation du stock** : le stock est décrémenté à la création de la commande et restitué en cas d'annulation.
- **Statuts** : Reçue → Confirmée → En préparation → Prête/expédiée → Terminée ; annulation possible jusqu'à « En préparation ».
- **Rapports** : chiffre d'affaires = commandes non annulées créées sur la période.
- **Données** : aucun prix réel n'est saisi. `init_store --demo` crée des produits marqués `[DÉMO]` à supprimer avant publication.

## Production

Variables d'environnement : `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, et `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` pour PostgreSQL. Lancer `python manage.py collectstatic` et servir `media/` via le serveur web.
