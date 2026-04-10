from django.db import models
from django.utils import timezone
from users.models import User, Service


# ============================================================================
# CIRCUIT D'AFFECTATION
# ============================================================================

class Circuit(models.Model):
    """
    Un circuit regroupe une ou plusieurs affectations liées au même courrier.
    Il peut être simultané (tous traitent en parallèle) ou séquentiel (étape par étape).
    """

    TYPE_CHOICES = [
        ('simultane', 'Simultané'),
        ('sequentiel', 'Séquentiel'),
    ]

    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
    ]

    # Courrier lié à ce circuit (import tardif pour éviter la circularité)
    courrier = models.ForeignKey(
        'documents.Courrier',
        on_delete=models.CASCADE,
        related_name='circuits_v2',
        help_text="Courrier concerné par ce circuit",
    )

    type_circuit = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='simultane',
        help_text="Simultané : tous traitent en même temps. Séquentiel : étape par étape.",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_cours',
    )

    titre = models.CharField(
        max_length=255,
        blank=True,
        help_text="Titre ou description courte du circuit (optionnel)",
    )

    instructions_generales = models.TextField(
        blank=True,
        help_text="Instructions générales valables pour l'ensemble du circuit",
    )

    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='circuits_v2_crees',
        help_text="Utilisateur ayant créé ce circuit (RH, Admin…)",
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Données supplémentaires (flexible)",
    )

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Circuit d'affectation"
        verbose_name_plural = "Circuits d'affectation"
        indexes = [
            models.Index(fields=['-date_creation']),
            models.Index(fields=['courrier', 'statut']),
        ]

    def __str__(self):
        return f"Circuit {self.get_type_circuit_display()} – {self.courrier.numero_registre} ({self.get_statut_display()})"

    # ------------------------------------------------------------------
    # Logique métier
    # ------------------------------------------------------------------

    def get_etape_actuelle(self):
        """Retourne le n° de la première étape non terminée (mode séquentiel)."""
        if self.type_circuit != 'sequentiel':
            return None

        affectations = self.affectations.order_by('etape_numero')
        etapes: dict[int, list] = {}
        for aff in affectations:
            etapes.setdefault(aff.etape_numero, []).append(aff)

        statuts_termines = {'valide', 'rejete', 'signe', 'renvoye'}
        for num in sorted(etapes.keys()):
            if not all(a.statut in statuts_termines for a in etapes[num]):
                return num
        return None  # Toutes les étapes sont terminées

    def est_termine(self):
        """Vérifie si toutes les affectations du circuit sont dans un état terminal."""
        affectations = self.affectations.all()
        if not affectations.exists():
            return False
        statuts_termines = {'valide', 'rejete', 'signe', 'renvoye'}
        return all(a.statut in statuts_termines for a in affectations)

    def rafraichir_statut(self):
        """Met à jour le statut du circuit et du courrier en fonction des affectations."""
        if self.est_termine():
            self.statut = 'termine'
            self.save(update_fields=['statut', 'date_modification'])
            # Mettre à jour le courrier si toutes ses affectations sont traitées
            tous_circuits_termines = all(
                c.est_termine() for c in self.courrier.circuits.all()
            )
            if tous_circuits_termines:
                self.courrier.statut = 'traite'
                self.courrier.save(update_fields=['statut'])


# ============================================================================
# AFFECTATION
# ============================================================================

class Affectation(models.Model):
    """
    Une affectation représente l'instruction donnée à un utilisateur (ou service)
    de traiter un courrier d'une manière précise.
    Elle appartient obligatoirement à un Circuit.
    """

    STATUT_CHOICES = [
        ('distribue', 'Distribué'),
        ('vu', 'Vu'),
        ('en_traitement', 'En traitement'),
        ('valide', 'Validé'),
        ('signe', 'Signé'),
        ('rejete', 'Rejeté'),
        ('renvoye', 'Renvoyé'),
    ]

    NIVEAU_URGENCE_CHOICES = [
        ('faible', 'Faible'),
        ('normal', 'Normal'),
        ('eleve', 'Élevé'),
        ('critique', 'Critique'),
    ]

    ACTION_REQUISE_CHOICES = [
        ('informatif', 'À titre informatif'),
        ('a_signer', 'À signer'),
        ('accusation_reception', 'À accuser de réception'),
        ('a_repondre', 'À répondre'),
        ('a_valider', 'À valider'),
        ('a_annoter', 'À annoter'),
    ]

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    circuit = models.ForeignKey(
        Circuit,
        on_delete=models.CASCADE,
        related_name='affectations',
        help_text="Circuit auquel appartient cette affectation",
    )

    # Dénormalisation du courrier pour faciliter les requêtes directes
    courrier = models.ForeignKey(
        'documents.Courrier',
        on_delete=models.CASCADE,
        related_name='affectations_v2',
        help_text="Courrier concerné (copie de circuit.courrier pour accès direct)",
    )

    destinataire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='affectations_v2_recues',
        help_text="Utilisateur à qui le courrier est affecté",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='affectations_v2',
        help_text="Service concerné (optionnel, déduit du destinataire si absent)",
    )

    affecte_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='affectations_v2_creees',
        help_text="Utilisateur qui a créé cette affectation",
    )

    # ------------------------------------------------------------------
    # Configuration de l'affectation
    # ------------------------------------------------------------------

    action_requise = models.CharField(
        max_length=30,
        choices=ACTION_REQUISE_CHOICES,
        default='informatif',
        help_text="Ce que le destinataire doit faire avec ce courrier",
    )

    note_instruction = models.TextField(
        blank=True,
        help_text="Instructions spécifiques de l'affecteur pour cette affectation",
    )

    niveau_urgence = models.CharField(
        max_length=20,
        choices=NIVEAU_URGENCE_CHOICES,
        default='normal',
    )

    date_echeance = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure limite pour traiter cette affectation",
    )

    # Étape (utile uniquement en mode séquentiel)
    etape_numero = models.PositiveIntegerField(
        default=1,
        help_text="N° d'étape dans le circuit séquentiel (toutes à 1 en simultané)",
    )

    # ------------------------------------------------------------------
    # Suivi du traitement
    # ------------------------------------------------------------------

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='distribue',
    )

    commentaire_traitement = models.TextField(
        blank=True,
        help_text="Commentaire du destinataire lors du traitement",
    )

    motif_rejet = models.TextField(
        blank=True,
        help_text="Motif en cas de rejet",
    )

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------

    date_affectation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(
        null=True, blank=True,
        help_text="Première ouverture par le destinataire",
    )
    date_traitement = models.DateTimeField(
        null=True, blank=True,
        help_text="Date de validation / rejet / signature",
    )

    # ------------------------------------------------------------------
    # Métadonnées supplémentaires
    # ------------------------------------------------------------------

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Données supplémentaires flexibles (pièces jointes, tags, etc.)",
    )

    class Meta:
        ordering = ['etape_numero', '-date_affectation']
        verbose_name = "Affectation"
        verbose_name_plural = "Affectations"
        indexes = [
            models.Index(fields=['destinataire', 'statut']),
            models.Index(fields=['circuit', 'etape_numero']),
            models.Index(fields=['-date_affectation']),
        ]

    def __str__(self):
        return (
            f"{self.courrier.numero_registre} → {self.destinataire.username} "
            f"[étape {self.etape_numero}] ({self.get_statut_display()})"
        )

    # ------------------------------------------------------------------
    # Vérifications
    # ------------------------------------------------------------------

    def peut_etre_traitee(self) -> bool:
        """En mode séquentiel, vérifie que c'est bien l'étape actuelle."""
        if self.circuit.type_circuit == 'simultane':
            return True
        etape_actuelle = self.circuit.get_etape_actuelle()
        return etape_actuelle is None or self.etape_numero == etape_actuelle

    # ------------------------------------------------------------------
    # Actions métier
    # ------------------------------------------------------------------

    def _set_date_traitement(self):
        if not self.date_traitement:
            self.date_traitement = timezone.now()

    def marquer_comme_lu(self):
        if self.statut in ('distribue',):
            if not self.date_lecture:
                self.date_lecture = timezone.now()
            self.statut = 'vu'
            self.save(update_fields=['statut', 'date_lecture'])

    def demarrer_traitement(self):
        """Passe de 'vu' à 'en_traitement'."""
        if self.statut in ('vu', 'distribue'):
            if not self.date_lecture:
                self.date_lecture = timezone.now()
            self.statut = 'en_traitement'
            self.save(update_fields=['statut', 'date_lecture'])

    def valider(self, commentaire: str = ''):
        self._set_date_traitement()
        self.statut = 'valide'
        self.commentaire_traitement = commentaire
        self.save()
        self.circuit.rafraichir_statut()

    def signer(self, commentaire: str = ''):
        self._set_date_traitement()
        self.statut = 'signe'
        self.commentaire_traitement = commentaire
        self.save()
        self.circuit.rafraichir_statut()

    def rejeter(self, motif: str = ''):
        self._set_date_traitement()
        self.statut = 'rejete'
        self.motif_rejet = motif
        self.save()
        self.circuit.rafraichir_statut()

    def renvoyer(self, commentaire: str = ''):
        self._set_date_traitement()
        self.statut = 'renvoye'
        self.commentaire_traitement = commentaire
        # Remettre le service de l'affectation à null
        self.service = None
        self.save()
        # Remettre le courrier en attente chez la RH et effacer le service concerné
        self.courrier.statut = 'recu'
        self.courrier.service_concerne = ''
        self.courrier.save(update_fields=['statut', 'service_concerne'])
        self.circuit.rafraichir_statut()
