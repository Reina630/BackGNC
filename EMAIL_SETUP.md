# Configuration de l'envoi d'emails

## Fonctionnalité d'envoi d'emails

Le système permet d'envoyer des courriers par email directement depuis la plateforme, avec le fichier PDF en pièce jointe.

## Configuration

### 1. Variables d'environnement

Créez un fichier `.env` à la racine du projet backend (GedBack/) en vous basant sur `.env.example` :

```bash
cp .env.example .env
```

### 2. Configuration Gmail (Recommandé)

Si vous utilisez Gmail, vous devez créer un "Mot de passe d'application" (App Password) :

1. Allez sur votre compte Google : https://myaccount.google.com
2. Activez la "Validation en deux étapes" si ce n'est pas déjà fait
3. Allez sur : https://myaccount.google.com/apppasswords
4. Créez un nouveau mot de passe d'application
5. Copiez le mot de passe généré (16 caractères)

Ajoutez ensuite ces variables dans votre fichier `.env` :

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-application
DEFAULT_FROM_EMAIL=votre-email@gmail.com
```

### 3. Autres fournisseurs SMTP

#### Outlook/Hotmail
```env
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@outlook.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe
```

#### Yahoo
```env
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre-email@yahoo.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe
```

### 4. Mode Console (Développement)

Si vous ne configurez pas les variables d'email, le système utilisera automatiquement le backend `console` qui affiche les emails dans la console au lieu de les envoyer.

## Utilisation

### Depuis l'interface

1. Ouvrez un courrier dans les archives
2. Cliquez sur "Partager"
3. Sélectionnez "Email"
4. Entrez l'adresse email du destinataire
5. Ajoutez un message personnalisé (optionnel)
6. Cliquez sur "Partager"

L'email sera envoyé avec :
- Le fichier PDF en pièce jointe
- Les informations du courrier (numéro, objet, dates, etc.)
- Votre message personnalisé

### API Endpoint

```bash
POST /api/partages/send_email/

Body:
{
  "courrier_id": 1,
  "destinataire": "email@example.com",
  "message": "Message personnalisé (optionnel)"
}

Response (Success):
{
  "success": true,
  "message": "Email envoyé avec succès",
  "partage_id": 123
}

Response (Error):
{
  "error": "Message d'erreur"
}
```

## Dépannage

### Erreur "Authentication failed"
- Vérifiez que vous utilisez un mot de passe d'application (pas votre mot de passe Gmail normal)
- Assurez-vous que la validation en deux étapes est activée

### Erreur "SMTPAuthenticationError"
- Vérifiez vos identifiants EMAIL_HOST_USER et EMAIL_HOST_PASSWORD
- Assurez-vous que "Autoriser les applications moins sécurisées" est activé (Gmail)

### Email non reçu
- Vérifiez les spams/courriers indésirables
- Vérifiez que l'adresse email du destinataire est correcte
- Consultez les logs Django pour plus de détails

### Tester l'envoi d'email

Vous pouvez tester l'envoi d'email via le shell Django :

```python
python manage.py shell

from django.core.mail import send_mail

send_mail(
    'Test Email',
    'Ceci est un email de test',
    'votre-email@gmail.com',
    ['destinataire@example.com'],
    fail_silently=False,
)
```

## Historique des partages

Tous les emails envoyés sont enregistrés dans l'historique des partages (`PartageLog`) avec :
- Le courrier partagé
- Le destinataire
- L'utilisateur qui a partagé
- La date et l'heure
- Le type de partage (email)

Consultez l'historique sur : `/api/partages/`
