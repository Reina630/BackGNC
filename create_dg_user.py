"""
Script pour créer un utilisateur DG (Directeur Général) de test
Usage: python create_dg_user.py
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
django.setup()

from users.models import User

def create_dg_user():
    """Créer un utilisateur DG de test"""
    username = 'Dg'
    email = 'dg@iman.ne'
    password = '1234'
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username=username).exists():
        print(f"❌ L'utilisateur '{username}' existe déjà.")
        user = User.objects.get(username=username)
        print(f"   Rôle actuel: {user.role}")
        
        # Mettre à jour le rôle si nécessaire
        if user.role != 'dg':
            user.role = 'dg'
            user.save()
            print(f"✅ Rôle mis à jour en 'dg'")
        return
    
    # Créer l'utilisateur DG
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role='dg',
        is_active=True,
    )
    
    print("✅ Utilisateur DG créé avec succès!")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   Rôle: {user.role}")
    print("\n📝 Utilisez ces identifiants pour tester l'application de registre de courrier.")
    print("   Le DG a accès au registre mais ne peut traiter que les courriers qui lui sont assignés.")

if __name__ == '__main__':
    create_dg_user()
