# Script de démarrage du backend GED avec système de courriers intégré

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Démarrage du système GED complet" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activer l'environnement virtuel
Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Migrations
Write-Host ""
Write-Host "Création des migrations..." -ForegroundColor Yellow
python manage.py makemigrations

Write-Host ""
Write-Host "Application des migrations..." -ForegroundColor Yellow
python manage.py migrate

# Vérifier si on doit créer un superuser
Write-Host ""
$createSuperuser = Read-Host "Voulez-vous créer un superuser? (o/N)"
if ($createSuperuser -eq "o" -or $createSuperuser -eq "O") {
    python manage.py createsuperuser
}

# Lancer le serveur
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Démarrage du serveur Django" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Le serveur sera accessible sur: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Admin: http://localhost:8000/admin" -ForegroundColor Cyan
Write-Host "API Documents: http://localhost:8000/api/" -ForegroundColor Cyan
Write-Host "API Courriers: http://localhost:8000/api/courriers/" -ForegroundColor Cyan
Write-Host "API Affectations: http://localhost:8000/api/affectations/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter le serveur" -ForegroundColor Gray
Write-Host ""

python manage.py runserver
