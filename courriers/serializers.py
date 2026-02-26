from rest_framework import serializers
from .models import Courrier
from tags.models import Tag
from users.models import User


class CourrierSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour la lecture des courriers
    """
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    service_nom = serializers.CharField(source='service.username', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Courrier
        fields = [
            'id',
            'reference',
            'type',
            'objet',
            'description',
            'statut',
            'expediteur',
            'destinataire',
            'date_reception',
            'date_envoi',
            'mode_envoi',
            'reponse_a',
            'categorie',
            'categorie_nom',
            'service',
            'service_nom',
            'fichier',
            'created_by',
            'created_by_nom',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reference', 'created_by', 'created_at', 'updated_at']


class CourrierCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création de courriers
    """
    class Meta:
        model = Courrier
        fields = [
            'type',
            'objet',
            'description',
            'expediteur',
            'destinataire',
            'date_reception',
            'date_envoi',
            'mode_envoi',
            'reponse_a',
            'categorie',
            'service',
            'fichier',
        ]
    
    def validate(self, data):
        """
        Validation personnalisée selon le type de courrier
        """
        type_courrier = data.get('type')
        
        if type_courrier == 'entrant':
            if not data.get('expediteur'):
                raise serializers.ValidationError({'expediteur': 'L\'expéditeur est requis pour un courrier entrant'})
            if not data.get('date_reception'):
                raise serializers.ValidationError({'date_reception': 'La date de réception est requise pour un courrier entrant'})
        
        elif type_courrier == 'sortant':
            if not data.get('destinataire'):
                raise serializers.ValidationError({'destinataire': 'Le destinataire est requis pour un courrier sortant'})
            if not data.get('date_envoi'):
                raise serializers.ValidationError({'date_envoi': 'La date d\'envoi est requise pour un courrier sortant'})
        
        return data


class CourrierUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour des courriers
    """
    class Meta:
        model = Courrier
        fields = [
            'objet',
            'description',
            'statut',
            'expediteur',
            'destinataire',
            'date_reception',
            'date_envoi',
            'mode_envoi',
            'reponse_a',
            'categorie',
            'service',
            'fichier',
        ]
