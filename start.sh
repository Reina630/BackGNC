#!/bin/bash
# Script de démarrage pour Render.com

echo "=========================================="
echo "🚀 Démarrage de l'application GED"
echo "=========================================="

# 1. Appliquer les migrations
echo "📦 Application des migrations..."
python manage.py migrate --noinput

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors des migrations"
    exit 1
fi

# 2. Collecter les fichiers statiques
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# 3. Créer le premier utilisateur (seulement si nécessaire)
echo "👤 Configuration utilisateur admin..."
python create_first_user.py

# 4. Démarrer Gunicorn
echo "🎯 Démarrage du serveur..."
gunicorn ged.wsgi:application
