#!/usr/bin/env python
"""
Script pour créer un utilisateur de test pour l'application de gestion des courriers

Usage:
    python create_test_user.py
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
django.setup()

from users.models import User

def create_test_user():
    """
    Créer un utilisateur de test
    """
    username = 'test'
    password = 'test123'
    email = 'test@iman.com'
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(username=username).exists():
        print(f"✓ L'utilisateur '{username}' existe déjà")
        user = User.objects.get(username=username)
    else:
        # Créer l'utilisateur
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name='Test',
            last_name='User',
            role='employee'
        )
        print(f"✓ Utilisateur '{username}' créé avec succès")
    
    # Afficher les informations
    print("\n" + "="*50)
    print("INFORMATIONS DE CONNEXION")
    print("="*50)
    print(f"URL:              http://localhost:5173")
    print(f"Nom d'utilisateur: {username}")
    print(f"Mot de passe:     {password}")
    print(f"Email:            {email}")
    print(f"Rôle:             {user.role}")
    print("="*50)
    print("\nVous pouvez maintenant vous connecter avec ces identifiants.")
    print()

if __name__ == '__main__':
    create_test_user()
