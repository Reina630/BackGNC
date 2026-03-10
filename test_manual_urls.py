#!/usr/bin/env python
"""Script pour tester les URLs manuelles des courriers"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ged.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.urls import resolve, reverse, NoReverseMatch
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

print("\n" + "=" * 80)
print("TEST DES URLS MANUELLES COURRIERS")
print("=" * 80 + "\n")

# URLs à tester
test_urls = [
    '/api/courriers/',
    '/api/courriers/1/',
    '/api/courriers/mes_affectations/',
    '/api/courriers/statistiques/',
    '/api/courriers/affecter_utilisateur/',
    '/api/courriers/affecter_service/',
    '/api/courriers/traiter_affectation/',
    '/api/courriers/commenter_affectation/',
    '/api/courriers/marquer_lu/',
    '/api/courriers/commentaires_affectation/',
    '/api/courriers/1/archiver/',
    '/api/courriers/1/download/',
]

print("1. TEST DE RÉSOLUTION D'URL:")
print("-" * 80)
for url in test_urls:
    try:
        resolved = resolve(url)
        print(f"✓ {url}")
        print(f"  View: {resolved.func}")
        print(f"  Name: {resolved.url_name}")
        print(f"  Args: {resolved.args}")
        print(f"  Kwargs: {resolved.kwargs}")
    except Exception as e:
        print(f"✗ {url}")
        print(f"  Erreur: {e}")
    print()

print("\n2. TEST DE REVERSE URL:")
print("-" * 80)
url_names = [
    'courrier-list',
    'courrier-detail',
    'courrier-mes-affectations', 
    'courrier-statistiques',
    'courrier-affecter-utilisateur',
    'courrier-affecter-service',
    'courrier-traiter-affectation',
    'courrier-commenter-affectation',
    'courrier-marquer-lu',
    'courrier-commentaires-affectation',
    'courrier-archiver',
    'courrier-download',
]

for name in url_names:
    try:
        if 'detail' in name or 'archiver' in name or 'download' in name:
            url = reverse(name, kwargs={'pk': 1})
        else:
            url = reverse(name)
        print(f"✓ {name}: {url}")
    except NoReverseMatch as e:
        print(f"✗ {name}: {e}")

print("\n" + "=" * 80)
print("FIN DU TEST")
print("=" * 80 + "\n")