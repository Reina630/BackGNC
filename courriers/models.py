from django.db import models
from users.models import User
from tags.models import Tag


class Courrier(models.Model):
    """
    Modèle pour la gestion du registre de courriers (entrants et sortants)
    """
    TYPE_CHOICES = [
        ('entrant', 'Courrier entrant'),
        ('sortant', 'Courrier sortant'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours de traitement'),
        ('traite', 'Traité'),
        ('archive', 'Archivé'),
    ]
    
    MODE_ENVOI_CHOICES = [
        ('courrier', 'Courrier postal'),
        ('email', 'Email'),
        ('fax', 'Fax'),
        ('main', 'Remise en main propre'),
        ('huissier', 'Huissier'),
    ]
    
    # Champs communs
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    objet = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Relations
    categorie = models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True, related_name='courriers')
    service = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='courriers_service')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courriers_crees')
    
    # Champs spécifiques aux courriers entrants
    expediteur = models.CharField(max_length=255, blank=True, help_text="Organisme externe qui envoie")
    date_reception = models.DateField(null=True, blank=True)
    
    # Champs spécifiques aux courriers sortants
    destinataire = models.CharField(max_length=255, blank=True, help_text="Organisme externe destinataire")
    date_envoi = models.DateField(null=True, blank=True)
    mode_envoi = models.CharField(max_length=20, choices=MODE_ENVOI_CHOICES, blank=True)
    reponse_a = models.CharField(max_length=50, blank=True, help_text="Référence du courrier auquel on répond")
    
    # Fichier joint
    fichier = models.FileField(upload_to='courriers/%Y/%m/%d/', blank=True, null=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Courrier'
        verbose_name_plural = 'Courriers'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['type', 'statut']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.objet[:50]}"
    
    def save(self, *args, **kwargs):
        # Générer la référence automatiquement si elle n'existe pas
        if not self.reference:
            self.reference = self.generer_reference()
        super().save(*args, **kwargs)
    
    def generer_reference(self):
        """
        Génère une référence unique pour le courrier
        Format: CE-YYYY-XXX (entrant) ou CS-YYYY-XXX (sortant)
        """
        from django.utils import timezone
        import datetime
        
        # Préfixe selon le type
        prefix = 'CE' if self.type == 'entrant' else 'CS'
        
        # Année courante
        year = timezone.now().year
        
        # Compter les courriers du même type cette année
        count = Courrier.objects.filter(
            type=self.type,
            created_at__year=year
        ).count() + 1
        
        # Format: CE-2026-001
        return f"{prefix}-{year}-{count:03d}"
