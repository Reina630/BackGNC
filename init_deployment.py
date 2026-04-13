"""
Script d'initialisation pour le déploiement
Crée les services, utilisateurs et catégories de base
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
django.setup()

from users.models import User, Service
from documents.models import Categorie
from django.db import connection

def check_tables():
    """Vérifier que les tables existent"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users_user'
            );
        """)
        return cursor.fetchone()[0]

def create_services():
    """Créer les services de base"""
    services_data = [
        {
            'nom': 'Direction Générale',
            'description': 'Direction de l\'organisation'
        },
        {
            'nom': 'Ressources Humaines',
            'description': 'Gestion du personnel et des ressources humaines'
        },
        {
            'nom': 'Comptabilité',
            'description': 'Gestion financière et comptable'
        },
        {
            'nom': 'Informatique',
            'description': 'Gestion des systèmes d\'information et de l\'infrastructure IT'
        },
        {
            'nom': 'Service Commercial',
            'description': 'Gestion des ventes et relations clients'
        },
        {
            'nom': 'Service Juridique',
            'description': 'Affaires juridiques et conformité'
        },
        {
            'nom': 'Service Logistique',
            'description': 'Gestion de la logistique et des approvisionnements'
        },
    ]
    
    created_services = {}
    print("\n" + "="*60)
    print("CRÉATION DES SERVICES")
    print("="*60)
    
    for service_data in services_data:
        service, created = Service.objects.get_or_create(
            nom=service_data['nom'],
            defaults={'description': service_data['description']}
        )
        created_services[service.nom] = service
        status = "✅ Créé" if created else "ℹ️  Existe déjà"
        print(f"{status}: {service.nom}")
    
    return created_services

def create_users(services):
    """Créer les utilisateurs de base"""
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@iman.ne',
            'password': '1234',
            'first_name': 'Admin',
            'last_name': 'System',
            'role': 'admin',
            'service': None,
            'is_staff': True,
            'is_superuser': True,
        },
        {
            'username': 'dg',
            'email': 'dg@iman.ne',
            'password': '1234',
            'first_name': 'Sangoku',
            'last_name': '',
            'role': 'dg',
            'service': services.get('Direction Générale'),
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'username': 'rh',
            'email': 'rh@iman.ne',
            'password': '1234',
            'first_name': 'Bulma',
            'last_name': 'Brief',
            'role': 'rh',
            'service': services.get('Ressources Humaines'),
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'username': 'compta',
            'email': 'compta@iman.ne',
            'password': '1234',
            'first_name': 'Vegeta',
            'last_name': 'Prince',
            'role': 'collaborator',
            'service': services.get('Comptabilité'),
            'is_staff': False,
            'is_superuser': False,
        },
    ]
    
    print("\n" + "="*60)
    print("CRÉATION DES UTILISATEURS")
    print("="*60)
    
    for user_data in users_data:
        username = user_data.pop('username')
        password = user_data.pop('password')
        
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            print(f"ℹ️  Existe déjà: {username} ({user.email})")
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                **user_data
            )
            print(f"✅ Créé: {username} ({user.email}) - {user.get_role_display()}")

def create_categories():
    """Créer les catégories de courriers de base"""
    categories_data = [
        {
            'name': 'Facture',
            'description': 'Factures fournisseurs et clients'
        },
        {
            'name': 'Devis',
            'description': 'Devis et propositions commerciales'
        },
        {
            'name': 'Contrat',
            'description': 'Contrats et conventions'
        },
        {
            'name': 'Demande',
            'description': 'Demandes diverses (congés, achats, etc.)'
        },
        {
            'name': 'Rapport',
            'description': 'Rapports d\'activité et comptes rendus'
        },
        {
            'name': 'Convocation',
            'description': 'Convocations et invitations'
        },
        {
            'name': 'Note de service',
            'description': 'Notes de service et communications internes'
        },
        {
            'name': 'Courrier administratif',
            'description': 'Courriers administratifs divers'
        },
        {
            'name': 'Réclamation',
            'description': 'Réclamations et plaintes'
        },
        {
            'name': 'Attestation',
            'description': 'Attestations et certificats'
        },
    ]
    
    print("\n" + "="*60)
    print("CRÉATION DES CATÉGORIES")
    print("="*60)
    
    for cat_data in categories_data:
        category, created = Categorie.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        status = "✅ Créé" if created else "ℹ️  Existe déjà"
        print(f"{status}: {category.name}")

def print_summary():
    """Afficher un résumé des identifiants"""
    print("\n" + "="*60)
    print("IDENTIFIANTS DE CONNEXION")
    print("="*60)
    print("\n📧 ADMIN")
    print("   Email:    admin@iman.ne")
    print("   Password: 1234")
    print("   Rôle:     Administrateur système")
    
    print("\n👔 DIRECTION GÉNÉRALE (DG)")
    print("   Email:    dg@iman.ne")
    print("   Password: 1234")
    print("   Nom:      Sangoku Son")
    print("   Service:  Direction Générale")
    
    print("\n👥 RESSOURCES HUMAINES (RH)")
    print("   Email:    rh@iman.ne")
    print("   Password: 1234")
    print("   Nom:      Bulma Brief")
    print("   Service:  Ressources Humaines")
    
    print("\n💰 COMPTABILITÉ")
    print("   Email:    compta@iman.ne")
    print("   Password: 1234")
    print("   Nom:      Vegeta Prince")
    print("   Service:  Comptabilité")
    
    print("\n" + "="*60)
    print(f"✅ Services créés:     {Service.objects.count()}")
    print(f"✅ Utilisateurs créés: {User.objects.count()}")
    print(f"✅ Catégories créées:  {Categorie.objects.count()}")
    print("="*60)

def main():
    try:
        # Vérifier que les tables existent
        if not check_tables():
            print("⚠️  Les tables n'existent pas encore. Exécutez d'abord:")
            print("   python manage.py migrate")
            sys.exit(1)
        
        # 1. Créer les services (en premier car les users en dépendent)
        services = create_services()
        
        # 2. Créer les utilisateurs
        create_users(services)
        
        # 3. Créer les catégories
        create_categories()
        
        # 4. Afficher le résumé
        print_summary()
        
        print("\n🎉 Initialisation terminée avec succès!\n")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'initialisation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
