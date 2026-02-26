# Déploiement sur Render.com

## Configuration requise

### 1. Variables d'environnement à définir sur Render :

```
DJANGO_SETTINGS_MODULE=ged.settings
SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire
DEBUG=False
ALLOWED_HOSTS=votre-app.onrender.com
DATABASE_URL=postgresql://user:password@host:port/database

# PostgreSQL (automatiquement créé par Render si vous ajoutez une base de données)
# DATABASE_URL sera défini automatiquement
```

### 2. Configuration du service web sur Render :

**Build Command :**
```bash
pip install -r requirements.txt
```

**Start Command :**
```bash
bash start.sh
```

OU si bash ne fonctionne pas :

```bash
python manage.py migrate --noinput && python manage.py collectstatic --noinput && python create_first_user.py && gunicorn ged.wsgi:application
```

### 3. Créer la base de données PostgreSQL :
- Dans Render Dashboard : New → PostgreSQL
- Connecter la base à votre Web Service
- DATABASE_URL sera automatiquement défini

### 4. Vérifier que les migrations sont dans Git :

```bash
git status
# Vérifier que les fichiers suivants sont trackés :
# - users/migrations/0001_initial.py
# - users/migrations/0002_alter_log_id_alter_user_id.py
# - documents/migrations/*.py
# - folders/migrations/*.py
# - tags/migrations/*.py
```

Si les migrations ne sont pas dans Git :
```bash
git add users/migrations/*.py
git add documents/migrations/*.py
git add folders/migrations/*.py
git add tags/migrations/*.py
git commit -m "Add migrations"
git push
```

### 5. Identifiants par défaut après déploiement :

```
Username: admin
Password: 1234
Email: admin@iman.ne
```

⚠️ **IMPORTANT** : Changez ce mot de passe immédiatement après le premier déploiement !

## Dépannage

### Erreur "relation users_user does not exist" :
- Vérifiez que toutes les migrations sont dans votre repo Git
- Vérifiez que DATABASE_URL est correctement configuré
- Les migrations doivent s'exécuter dans l'ordre

### Le déploiement échoue :
- Consultez les logs : Dashboard → Logs
- Vérifiez requirements.txt
- Vérifiez les variables d'environnement

### Le site affiche une erreur 500 :
- Vérifiez que DEBUG=False
- Vérifiez ALLOWED_HOSTS contient votre domaine
- Consultez les logs pour les détails
