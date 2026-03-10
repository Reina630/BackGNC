from django.db import models
from django.contrib.auth.models import AbstractUser


class Service(models.Model):
    """Service de l'organisation"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('rh', 'RH'),
        ('collaborator', 'Collaborateur'),
        ('client', 'Client'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='collaborator')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='utilisateurs')
    
    # Signature électronique
    signature_electronique = models.ImageField(
        upload_to='signatures/%Y/%m/',
        null=True,
        blank=True,
        help_text="Image de la signature électronique de l'utilisateur (PNG recommandé avec fond transparent)"
    )
    
    # Mot de passe de signature (hashé séparément du mot de passe principal)
    signature_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Mot de passe hashé pour valider la signature électronique"
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def set_signature_password(self, raw_password):
        """Définir le mot de passe de signature (hashé)"""
        from django.contrib.auth.hashers import make_password
        self.signature_password = make_password(raw_password)
    
    def check_signature_password(self, raw_password):
        """Vérifier le mot de passe de signature"""
        from django.contrib.auth.hashers import check_password
        if not self.signature_password:
            return False
        return check_password(raw_password, self.signature_password)


class Log(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"


class Notification(models.Model):
    """Notifications pour les utilisateurs"""
    TYPE_CHOICES = [
        ('courrier_affecte', 'Courrier affecté'),
        ('document_partage', 'Document partagé'),
        ('commentaire', 'Nouveau commentaire'),
        ('tache', 'Nouvelle tâche'),
        ('system', 'Notification système'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='system')
    titre = models.CharField(max_length=255)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    
    # Données supplémentaires pour créer des liens
    courrier_id = models.IntegerField(null=True, blank=True)
    document_id = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    lue_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.utilisateur.username} - {self.titre} ({'Lue' if self.lue else 'Non lue'})"

