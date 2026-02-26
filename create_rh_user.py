"""
Script pour créer un utilisateur RH de test
Usage: python create_rh_user.py
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
django.setup()

from users.models import User

def create_rh_user():
    """Créer un utilisateur RH de test"""
    username = 'Rh'
    email = 'rh@iman.ne'
    password = '1234'
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username=username).exists():
        print(f"❌ L'utilisateur '{username}' existe déjà.")
        user = User.objects.get(username=username)
        print(f"   Rôle actuel: {user.role}")
        
        # Mettre à jour le rôle si nécessaire
        if user.role != 'rh':
            user.role = 'rh'
            user.save()
            print(f"✅ Rôle mis à jour en 'rh'")
        return
    
    # Créer l'utilisateur RH
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role='rh',
        is_active=True,
    )
    
    print("✅ Utilisateur RH créé avec succès!")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   Rôle: {user.role}")
    print("\n📝 Utilisez ces identifiants pour tester l'application de registre de courrier.")

if __name__ == '__main__':
    create_rh_user()
