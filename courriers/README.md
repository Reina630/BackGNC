# Configuration de l'app Courriers

## Installation et Configuration

### 1. Migrations de base de données

```bash
cd GedBack
python manage.py makemigrations courriers
python manage.py migrate
```

### 2. Créer un utilisateur admin (si ce n'est pas déjà fait)

```bash
python manage.py createsuperuser
```

### 3. Lancer le serveur de développement

```bash
python manage.py runserver
```

Le serveur sera accessible sur http://localhost:8000

## API Endpoints

L'app courriers expose les endpoints suivants:

### Liste des courriers
- `GET /api/courriers/` - Liste tous les courriers
  - Paramètres de filtre: `type`, `statut`, `categorie`, `service`
  - Paramètre de recherche: `search` (recherche dans reference, objet, description, expediteur, destinataire)
  - Paramètre de tri: `ordering` (ex: `-created_at`)

### Créer un courrier
- `POST /api/courriers/` - Créer un nouveau courrier
  - Body (FormData):
    - `type`: 'entrant' | 'sortant'
    - `objet`: string
    - `description`: string (optionnel)
    - `expediteur`: string (requis pour entrant)
    - `destinataire`: string (requis pour sortant)
    - `date_reception`: date (requis pour entrant)
    - `date_envoi`: date (requis pour sortant)
    - `mode_envoi`: string (optionnel pour sortant)
    - `reponse_a`: string (optionnel)
    - `categorie`: number (ID du tag)
    - `service`: number (ID du service/user)
    - `fichier`: File (optionnel)

### Détails d'un courrier
- `GET /api/courriers/{id}/` - Récupérer les détails d'un courrier

### Modifier un courrier
- `PUT /api/courriers/{id}/` - Mettre à jour un courrier (tous les champs)
- `PATCH /api/courriers/{id}/` - Mettre à jour un courrier (champs partiels)

### Supprimer un courrier
- `DELETE /api/courriers/{id}/` - Supprimer un courrier

### Actions spéciales

#### Archiver un courrier
- `POST /api/courriers/{id}/archiver/` - Change le statut en 'archive'

#### Télécharger le fichier joint
- `GET /api/courriers/{id}/download/` - Télécharge le fichier attaché

#### Statistiques
- `GET /api/courriers/statistiques/` - Retourne les statistiques
  ```json
  {
    "total": 100,
    "entrants": 60,
    "sortants": 40,
    "en_attente": 20,
    "en_cours": 30,
    "traites": 40,
    "archives": 10
  }
  ```

## Modèle de données

Le modèle `Courrier` contient:

### Champs communs
- `reference`: Référence unique auto-générée (CE-YYYY-XXX ou CS-YYYY-XXX)
- `type`: 'entrant' ou 'sortant'
- `objet`: Objet du courrier
- `description`: Description détaillée
- `statut`: 'en_attente', 'en_cours', 'traite', 'archive'
- `categorie`: ForeignKey vers Tag
- `service`: ForeignKey vers User
- `created_by`: ForeignKey vers User (créateur)
- `fichier`: Fichier joint

### Champs spécifiques aux courriers entrants
- `expediteur`: Organisme externe qui envoie
- `date_reception`: Date de réception

### Champs spécifiques aux courriers sortants
- `destinataire`: Organisme externe destinataire
- `date_envoi`: Date d'envoi prévue/réelle
- `mode_envoi`: 'courrier', 'email', 'fax', 'main', 'huissier'
- `reponse_a`: Référence du courrier auquel on répond

### Métadonnées
- `created_at`: Date de création
- `updated_at`: Date de dernière modification

## Frontend

Le service `documentService` a été mis à jour pour utiliser l'endpoint `/api/courriers/` au lieu de `/api/documents/`.

Toutes les pages du frontend (CourriersList, NouveauCourrierEntrant, NouveauCourrierSortant, DetailCourrier, Dashboard, ArchivesPage) sont déjà configurées pour utiliser ce service.
