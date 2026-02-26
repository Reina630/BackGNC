
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
django.setup()

from users.models import User
from django.db import connection

try:
    # Vérifier que la table users_user existe
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users_user'
            );
        """)
        table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        print("⚠️  Table users_user n'existe pas encore. Migrations non appliquées.")
        sys.exit(0)
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username='admin').exists():
        print("✅ L'utilisateur admin existe déjà")
        user = User.objects.get(username='admin')
    else:
        # Créer l'utilisateur admin
        user = User.objects.create_user(
            username='admin',
            email='admin@iman.ne',
            password='1234',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        print(f"✅ Utilisateur créé: {user.username}")
    
    print("\n" + "="*60)
    print("IDENTIFIANTS DE CONNEXION")
    print("="*60)
    print(f"  Username:     admin")
    print(f"  Password:     1234")
    print(f"  Email:        admin@iman.ne")
    print("="*60)

except Exception as e:
    print(f"⚠️  Erreur lors de la création de l'utilisateur: {e}")
    print("   (Ce n'est pas grave si les migrations ne sont pas encore appliquées)")
    sys.exit(0)


